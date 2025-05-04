# login_handler.py
import os
import time
import requests
import logging
from pysm4 import encrypt_ecb
import base64
from dotenv import load_dotenv
from datetime import datetime, timedelta
from transitions import Machine
from .login_session_repository import LoginSessionRepository

class LoginStateMachine:
    # 加入 fetching_dept_cookie 状态
    states = [
        'init', 'config_loaded', 'db_connected',
        'portal_query', 'portal_ready',  # 基础会话状态
        'ccd_query', 'ccd_ready',       # 科室会话状态
        'login_encrypting', 'login_requesting',
        'renew_ccd_session',  # CCD会话重建状态
        'renew_portal',       # Portal会话重建状态
        'error'
    ]

    def __init__(self, username, password, sm4_key, login_url,
                 db_uri, user_info_url, dept_cookie_url, new_token_url):
        self.username = username
        self.password = password
        self.sm4_key = sm4_key
        self.login_url = login_url
        self.db_uri = db_uri
        self.user_info_url = user_info_url
        self.dept_cookie_url = dept_cookie_url
        self.new_token_url = new_token_url
        self.logger = logging.getLogger(__name__)
        self.context = {}
        self.repo = LoginSessionRepository(db_uri)
        self._setup_state_machine()

    def _setup_state_machine(self):
        self.machine = Machine(
            model=self, states=LoginStateMachine.states,
            initial='init', ignore_invalid_triggers=False
        )
        # 基础portal会话流程
        self.machine.add_transition('load_config', 'init', 'config_loaded')
        self.machine.add_transition('connect_db', 'config_loaded', 'db_connected')
        self.machine.add_transition('get_portal', 'db_connected', 'portal_query')
        
        # 统一portal状态转换
        self.machine.add_transition('portal_success', 
                                  ['portal_query','login_requesting','renew_portal'], 
                                  'portal_ready')
        self.machine.add_transition('portal_fail', 'portal_query', 'renew_portal')
        self.machine.add_transition('portal_renew_failed', 'renew_portal', 'error')
        
        # 登录流程
        self.machine.add_transition('start_login', '*', 'login_encrypting')
        self.machine.add_transition(
            'send_request', 'login_encrypting', 'login_requesting',
            after='_perform_login'
        )

        # 科室ccd会话流程
        self.machine.add_transition('get_ccd', 'portal_ready', 'ccd_query')
        #目前还需要！
        self.machine.add_transition('ccd_valid', 'ccd_query', 'ccd_ready')
        #目前还需要！

        # 重置/作废/错误
        self.machine.add_transition('reset', '*', 'init')
        self.machine.add_transition('invalidate', ['portal_ready','ccd_ready'], 'init')
        self.machine.add_transition('error', '*', 'error')
        self.machine.add_transition('renew_portal','*','renew_portal')
        
        # CCD会话重建流程
        self.machine.add_transition('renew_ccd', '*', 'renew_ccd_session')
        self.machine.add_transition('ccd_invalid', 'ccd_query', 'renew_ccd_session')
        self.machine.add_transition('renew_complete', 'renew_ccd_session', 'ccd_ready')
        self.machine.add_transition('renew_failed', 'renew_ccd_session', 'error')

        # 回调绑定
        self.machine.on_enter_config_loaded('_on_config_loaded')
        #移除它，避免get portal没有传参user id
        #self.machine.on_enter_db_connected('_on_db_connected')
        
        # Portal流程回调
        self.machine.on_enter_portal_query('_on_portal_query')
        self.machine.on_enter_login_encrypting('_on_encrypting')
        
        # CCD流程回调
        self.machine.on_enter_ccd_query('_on_ccd_query')
        
        # 公共回调
        self.machine.on_enter_error('_on_error')
        self.machine.on_enter_init('_on_reset')
        self.machine.on_enter_renew_ccd_session('_on_renew_ccd_session')
        self.machine.on_enter_renew_portal('_on_renew_portal')
        
        # login_requesting由after执行_perform_login，无需on_enter

    # ———— 原有回调 ————
    def _on_config_loaded(self):
        try:
            self.context.update({
                'username':self.username,'password':self.password,
                'sm4_key':self.sm4_key,'login_url':self.login_url
            })
        except Exception as e:
            self.logger.error(f"加载配置失败: {e}")
            self.error(error=e)

    def _on_db_connected(self):
        """数据库连接成功后触发portal查询"""
        try:
            if 'user_id' not in self.context:
                raise ValueError("缺少user_id")
            # 触发portal会话查询
            self.get_portal()
        except Exception as e:
            self.logger.error(f"DB连接后处理失败: {e}")
            self.error(error=e)

    def _on_portal_query(self):
        """查询portal会话状态"""
        try:
            sess = self.repo.get_active_session(
                self.context['user_id'],
                dept_id='portal'  # 固定portal标记
            )
            if sess and self._validate_portal(sess):
                self.context.update({
                    'portal_session': {
                        'user_id': sess.user_id,
                        'cookies': sess.cookies,
                        'access_token': sess.access_token,
                        'user_code': sess.user_code
                    },
                    'portal_cookies': sess.cookies
                })
                self.portal_success()
            else:
                self.portal_fail()
        except Exception as e:
            self.logger.error(f"查询portal会话失败: {e}")
            self.error(error=e)

    def _on_ccd_query(self):
        """查询ccd会话状态"""
        try:
            dept_id = self.context['dept_id']
            sess = self.repo.get_active_session(
                self.context['user_id'],
                dept_id=dept_id
            )
            if sess and self._validate_ccd(sess):
                self.context['ccd_session'] = {
                    'user_id': sess.user_id,
                    'cookies': sess.cookies,
                    'access_token': sess.access_token,
                    'user_code': sess.user_code
                }
                self.ccd_valid()
            else:
                self.ccd_invalid()
        except Exception as e:
            self.logger.error(f"查询ccd会话失败: {e}")
            self.error(error=e)

    def _validate_portal(self, session) -> bool:
        """验证portal会话有效性"""
        try:
            r = requests.get(self.user_info_url,
                           cookies=session.cookies, 
                           timeout=10)
            return (r.status_code == 200 and 
                   r.json().get('data',{}).get('loginName') == self.username)
        except:
            return False

    def _validate_ccd(self, session) -> bool:
        """验证ccd会话有效性"""
        try:
            url = f"{self.dept_cookie_url}?deptId={self.context['dept_id']}"
            r = requests.get(url, cookies=session.cookies, timeout=10)
            return r.status_code == 200
        except:
            return False
        
    def _on_reset(self):
        self.logger.info("状态机 reset")
        self.context.clear()

    def _on_error(self, *_, **__):
        self.logger.error("进入 error 状态")
        # 若想自动复位则解除注释
        # self.reset()

    def encrypt_password(self, pwd):
        if not self.sm4_key or len(self.sm4_key)!=32:
            raise ValueError("SM4 key 必须 32 字符")
        key_bytes=bytes.fromhex(self.sm4_key)
        key_str=key_bytes.decode('latin1')
        return base64.b64decode(encrypt_ecb(pwd,key_str)).hex()

    def _on_encrypting(self):
        try:
            self.context['encrypted_pwd'] = self.encrypt_password(self.password)
            # 触发发送登录请求
            self.send_request()
        except Exception as e:
            self.logger.error(f"加密失败: {e}")
            self.error(error=e)

    # ———— 核心登录逻辑 ————
    def _perform_login(self):
        """在 login_requesting 后执行，成功 portal_complete(), 失败 error()."""
        try:
            data = {
                "scheme":"login3","userName":self.username,
                "passWord":self.context['encrypted_pwd'],
                "city":"未知","ip":"10.248.200.14",
                "equipmentType":"PG199","needverifycode":"0"
            }
            r = requests.post(self.login_url, data=data,
                              headers={"Content-Type":"application/x-www-form-urlencoded"},
                              allow_redirects=False, timeout=10)
            r.raise_for_status()
            j = r.json()
            if j.get('code')!=200:
                raise ValueError(j.get('message'))
            expires=(datetime.now()+timedelta(days=30)).isoformat()
            sess_data={
                'user_id':self.username,
                'cookies':dict(r.cookies),
                'access_token':j['data']['access_token'],
                'user_code':j['data']['user_code'],
                'expires_at':expires,
                'dept_id':'portal'  # 标记为portal会话
            }
            self.repo.save_session(sess_data)
            # 统一更新上下文
            self.context.update({
                'result': sess_data,
                'portal_session': sess_data,
                'cookies': dict(r.cookies),
                'portal_cookies': dict(r.cookies)
            })
            # 统一触发portal_success
            self.portal_success()
        except Exception as e:
            self.logger.error(f"登录失败: {e}")
            self.error(error=e)
        
    def _on_renew_portal(self):
        """处理portal会话重建"""
        try:
            # 触发完整登录流程
            self.start_login()
            #self.send_request() 
            # 只是增强可读性
            # 登录成功后会自动转到portal_ready
        except Exception as e:
            self.logger.error(f"重建portal会话失败: {e}")
            self.portal_renew_failed(error=e)

    def _on_renew_ccd_session(self):
        """处理CCD会话重建"""
        try:
            # 1. 刷新access_token
            new_token = self.refresh_access_token()
            
            # 2. 获取新的ccd cookie
            url = f"{self.dept_cookie_url}?token={new_token}&deptId={self.context['dept_id']}"
            r = requests.get(url, cookies=self.context.get('portal_cookies', {}), timeout=10)
            if r.status_code != 200:
                raise ValueError(f"获取ccd cookie失败: HTTP {r.status_code}")
            
            # 3. 更新数据库和上下文
            merged_cookies = {**self.context.get('portal_cookies', {}), **dict(r.cookies)}

            # 只保存 **一次**，而且字段都是对的
            self.repo.save_session({
                'user_id':      self.context['user_id'],
                'dept_id':      self.context['dept_id'],
                'access_token': new_token,
                'cookies':      merged_cookies,
                'expires_at':  (datetime.now()+timedelta(days=1)).isoformat()
            })

            # 4. 再写回 context
            self.context['ccd_session'] = {
                'user_id':      self.context['user_id'],
                'dept_id':      self.context['dept_id'],
                'access_token': new_token,
                'cookies':      merged_cookies
            }            
            self.renew_complete()
            
        except Exception as e:
            self.logger.error(f"重建CCD会话失败: {e}")
            self.renew_failed(error=e)

    def refresh_access_token(self):
        """刷新access_token"""
        try:
            r = requests.get(self.new_token_url, cookies=self.context.get('portal_cookies', {}))
            if r.status_code == 200:
                data = r.json()
                if data.get('code') == 200:
                    return data['data']['access_token']
                raise ValueError(f"获取新token失败: {data.get('message')}")
            raise ValueError(f"刷新token请求失败: HTTP {r.status_code}")
        except Exception as e:
            self.logger.error(f"刷新token失败: {e}")
            raise

class LoginHandler:
    """处理登录会话的核心类，提供portal和ccd两种会话获取方式"""
    
    def __init__(self):
        """初始化登录处理器，从环境变量加载配置"""
        load_dotenv()
        # 外部配置一次性读取
        self.database_uri = os.getenv('DATABASE_URI')
        self.user_info_url = os.getenv('USER_INFO_URL')
        self.dept_cookie_url = os.getenv('DEPT_COOKIE_URL')
        self.new_token_url = os.getenv('NEW_TOKEN_URL')
        self.username = os.getenv('USERNAME')
        self.password = os.getenv('PASSWORD')
        self.sm4_key = os.getenv('SM4_KEY')
        self.login_url = os.getenv('LOGIN_URL')
        self.logger = logging.getLogger(__name__)
        # 把这些常量都传进去
        self.sm = LoginStateMachine(
            username = self.username,
            password = self.password,
            sm4_key = self.sm4_key,
            login_url = self.login_url,
            db_uri = self.database_uri,
            user_info_url = self.user_info_url,
            dept_cookie_url = self.dept_cookie_url,
            new_token_url = self.new_token_url
        )

    def get_portal_session(self, user_id: str, *, do_reset=True) -> dict:
        """
        获取基础portal会话
        Args:
            user_id: 必须提供的用户ID
        Returns:
            包含cookies等信息的字典
        Raises:
            ValueError: 当user_id为空时
            RuntimeError: 当登录失败时
        """
        #重置状态机, do_reset=True时重置,避免mark_ccd_invalid()的时候插入空行
        if do_reset:
            self.sm.reset()

        if not user_id:
            raise ValueError("user_id是必填参数")
            
        # 确保按正确顺序初始化状态机
        self.sm.load_config()
        self.sm.connect_db()
        self.sm.context.update({
            'user_id': user_id,
            'dept_id': 'portal'  # 特殊标记portal会话
        })
        self.sm.get_portal()
        
        # 等待状态机完成(最多30秒)
        max_wait = 30  # 秒
        start = time.time()
        
        while self.sm.state not in ('portal_ready', 'error'):
            if time.time() - start > max_wait:
                raise RuntimeError("获取portal会话超时")
            time.sleep(0.1)  # 避免busy-wait
            
        if self.sm.state != 'portal_ready':
            raise RuntimeError("获取portal会话失败")
        return self.sm.context['portal_session']

    def mark_portal_invalid(self, user_id: str) -> dict:
        """
        失效并重建portal会话
        Args:
            user_id: 必须提供的用户ID
        Returns:
            重建后的portal会话
        Raises:
            ValueError: 当user_id为空时
            RuntimeError: 当重建失败时
        """
        #重置状态机
        self.sm.reset()

        if not user_id:
            raise ValueError("user_id是必填参数")
            
        try:
            # 1. 失效现有会话
            self.sm.repo.invalidate_session(user_id, "portal")
            
            # 2. 设置上下文并触发重建
            self.sm.context['user_id'] = user_id
            self.sm.context['dept_id'] = 'portal'
            self.sm.renew_portal()
            
            # 3. 等待重建完成(最多30秒)
            max_wait = 30  # 秒
            start = time.time()
            
            while self.sm.state not in ('portal_ready', 'error'):
                if time.time() - start > max_wait:
                    raise RuntimeError("重建portal会话超时")
                time.sleep(0.1)  # 避免busy-wait
                
            if self.sm.state != 'portal_ready':
                raise RuntimeError("重建portal会话失败")
            return self.sm.context['portal_session']
            
        except Exception as e:
            self.logger.error(f"重建portal会话失败: {e}")
            raise RuntimeError(f"重建portal会话失败: {e}")

    def get_ccd_session(self, user_id: str, dept_id: str) -> dict:
        """
        获取指定科室的ccd会话
        Args:
            user_id: 必须提供的用户ID
            dept_id: 必须提供的科室ID
        Returns:
            包含cookies等信息的字典
        Raises:
            ValueError: 当参数为空时
            RuntimeError: 当登录失败时
        """

        if not user_id or not dept_id:
            raise ValueError("user_id和dept_id都是必填参数")
            
        # 确保已有portal会话
        if self.sm.state != 'portal_ready':
            self.get_portal_session(user_id)
            
        self.sm.context['user_id'] = user_id
        self.sm.context['dept_id'] = dept_id
        self.sm.get_ccd()
        
        # 等待状态机完成(最多30秒)
        max_wait = 30  # 秒
        start = time.time()
        
        while self.sm.state not in ('ccd_ready', 'error'):
            if time.time() - start > max_wait:
                raise RuntimeError(f"获取科室[{dept_id}]会话超时")
            time.sleep(0.1)  # 避免busy-wait
            
        if self.sm.state != 'ccd_ready':
            raise RuntimeError(f"获取科室[{dept_id}]会话失败")
        return self.sm.context['ccd_session']

    def mark_ccd_invalid(self, user_id: str, dept_id: str) -> dict:
        """
        标记CCD会话失效并重建
        Args:
            user_id: 用户ID
            dept_id: 科室ID
        Returns:
            重建后的CCD会话
        Raises:
            ValueError: 参数无效时
            RuntimeError: 重建失败时
        """
        #重置状态机
        self.sm.reset()

        if not user_id or not dept_id:
            raise ValueError("user_id和dept_id都是必填参数")
            
        # 1. 失效现有会话
        self.sm.repo.invalidate_session(user_id, dept_id)
        
        # 2. 设置上下文并触发重建
        self.sm.context.update({
            'user_id': user_id,
            'dept_id': dept_id,
            'portal_cookies': self.get_portal_session(user_id, do_reset=False)['cookies']
            #避免空行，设置为False
        })
        self.sm.renew_ccd()
        
        # 3. 等待重建完成(最多30秒)
        max_wait = 30  # 秒
        start = time.time()
        
        while self.sm.state not in ('ccd_ready', 'error'):
            if time.time() - start > max_wait:
                raise RuntimeError(f"重建科室[{dept_id}]会话超时")
            time.sleep(0.1)  # 避免busy-wait
            
        if self.sm.state != 'ccd_ready':
            raise RuntimeError(f"重建科室[{dept_id}]会话失败")
        return self.sm.context['ccd_session']

    def is_ccd_expired_response(self, response) -> bool:
        """
        根据一次 CCD 业务请求的 response 判断 cookie 是否失效：
        - 如果状态码是 301, 302, 307, 308（重定向到登录页），则视为失效
        - 否则（200 等），视为仍然有效
        """
        # Scrapy 在 meta.handle_httpstatus_list 中放行 302，此时 response.status == 302
        #print("######",response.headers)
        #print("######",response.status)
        if response.status in (301, 302, 307, 308) :
            # 可选：进一步检查 response.headers['Location'] 是否包含登录 URL 关键字
            #loc = response.headers.get('Location', b'').decode('utf8')
            #if self.login_url in loc:
            #    return True
            return True
        # 其他状态码（如 200）视为有效
        return False