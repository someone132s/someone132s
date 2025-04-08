import os
import requests
import logging
from pysm4 import encrypt_ecb
import base64
import json
from dotenv import load_dotenv
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from transitions import Machine
from crawler.models import SpiderSession
from .session_repository import SessionRepository

class LoginStateMachine:
    states = [
        'init',
        'config_loaded',
        'db_connected',
        'session_query_db',
        'session_has_session',
        'session_no_session',
        'login_encrypting',
        'login_requesting',
        'ready',
        'error'
    ]

    def __init__(self, username: str, password: str, sm4_key: str, login_url: str, db_uri: str):
        self.username = username
        self.password = password
        self.sm4_key = sm4_key
        self.login_url = login_url
        self.logger = logging.getLogger(__name__)
        self.retry_count = 0
        self.max_retries = 3
        self.context = {}
        
        self.repo = SessionRepository(db_uri)
        self._setup_state_machine()

    def _setup_state_machine(self):
        self.machine = Machine(
            model=self,
            states=LoginStateMachine.states,
            initial='init',
            ignore_invalid_triggers=True
        )
        
        # 添加状态转换，目标状态使用点号分隔的完整名称
        self.machine.add_transition('load_config', 'init', 'config_loaded')
        self.machine.add_transition('connect_db', 'config_loaded', 'db_connected')
        self.machine.add_transition('check_session', 'db_connected', 'session_query_db')
        self.machine.add_transition('found_session', 'session_query_db', 'session_has_session')
        self.machine.add_transition('no_session', 'session_query_db', 'session_no_session')
        self.machine.add_transition('start_login', 'session_no_session', 'login_encrypting')
        self.machine.add_transition('send_request', 'login_encrypting', 'login_requesting')
        self.machine.add_transition('complete', ['login_requesting', 'session_has_session'], 'ready')
        self.machine.add_transition('error', '*', 'error')
        
        # 添加回调（注意：状态名称自动将"."转换为"_"，所以回调名称使用下划线格式）
        self.machine.on_enter_config_loaded('_on_config_loaded')
        self.machine.on_enter_db_connected('_on_db_connected')
        self.machine.on_enter_session_query_db('_on_query_db')
        self.machine.on_enter_session_has_session('_on_has_session')
        self.machine.on_enter_session_no_session('_on_no_session')
        self.machine.on_enter_login_encrypting('_on_encrypting')
        self.machine.on_enter_login_requesting('_on_requesting')
        self.machine.on_enter_error('_on_error')

    def _on_config_loaded(self):
        """配置加载回调"""
        try:
            self.context.update({
                'username': self.username,
                'password': self.password,
                'sm4_key': self.sm4_key,
                'login_url': self.login_url
            })
            self.connect_db()
        except Exception as e:
            self.logger.error(f"加载配置失败: {str(e)}")
            self.error(error=e)

    def _on_db_connected(self):
        """数据库连接回调"""
        try:
            self.check_session()
        except Exception as e:
            self.logger.error(f"数据库连接失败: {str(e)}")
            self.error(error=e)

    def _on_query_db(self):
        """查询会话回调"""
        try:
            session = self.repo.get_active_session(self.username)
            if session:
                self.context['session'] = session
                self.found_session()
            else:
                self.no_session()
        except Exception as e:
            self.logger.error(f"查询会话失败: {str(e)}")
            self.error(error=e)

    def _verify_session(self, cookies):
        """验证会话是否有效"""
        try:
            response = requests.get(
                os.getenv('USER_INFO_URL'),
                cookies=cookies,
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return data.get('data', {}).get('loginName') == self.username
            return False
        except Exception as e:
            self.logger.warning(f"会话验证失败: {str(e)}")
            return False

    def _on_has_session(self):
        """存在会话回调"""
        try:
            session = self.context['session']
            if self._verify_session(session.cookies):
                self.context['result'] = {
                    'user_id': session.user_id,
                    'cookies': session.cookies,
                    'access_token': session.access_token,
                    'user_code': session.user_code
                }
                self.complete()
            else:
                self.repo.invalidate_session(self.username)
                self.start_login()
        except Exception as e:
            self.logger.error(f"会话验证失败: {str(e)}")
            self.error(error=e)

    def _on_encrypting(self):
        """密码加密回调"""
        try:
            encrypted = self.encrypt_password(self.password)
            self.context['encrypted_pwd'] = encrypted
            self.send_request()
        except Exception as e:
            self.logger.error(f"密码加密失败: {str(e)}")
            self.error(error=e)

    def _on_requesting(self):
        """登录请求回调"""
        try:
            login_data = {
                "scheme": "login3",
                "userName": self.username,
                "passWord": self.context['encrypted_pwd'],
                "city": "未知",
                "ip": "10.248.200.14",
                "equipmentType": "PG199",
                "needverifycode": "0"
            }
            
            response = requests.post(
                self.login_url,
                data=login_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                allow_redirects=False
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 200:
                    expires = datetime.now() + timedelta(days=30)
                    session_data = {
                        'user_id': self.username,
                        'cookies': dict(response.cookies),
                        'access_token': result['data']['access_token'],
                        'user_code': result['data']['user_code'],
                        'expires_at': expires
                    }
                    self.repo.save_session(session_data)
                    self.context['result'] = session_data
                    self.complete()
                else:
                    raise ValueError(f"登录失败: {result.get('message')}")
            else:
                raise ValueError(f"HTTP请求失败: {response.status_code}")
        except Exception as e:
            self.logger.error(f"登录请求失败: {str(e)}")
            self.error(error=e)

    def _on_error(self, error: Exception):
        """错误处理回调"""
        self.logger.error(f"状态机错误: {str(error)}")
        if self.retry_count < self.max_retries:
            self.retry_count += 1
            self.logger.info(f"准备重试({self.retry_count}/{self.max_retries})")
            self.load_config()
        else:
            raise RuntimeError(f"超过最大重试次数: {str(error)}")


class LoginHandler:
    def __init__(self):
        load_dotenv()
        self.username = os.getenv('USERNAME')
        self.password = os.getenv('PASSWORD')
        self.sm4_key = os.getenv('SM4_KEY')
        self.login_url = os.getenv('LOGIN_URL')
        self.logger = logging.getLogger(__name__)
        
        # 初始化状态机
        self.state_machine = LoginStateMachine(
            username=self.username,
            password=self.password,
            sm4_key=self.sm4_key,
            login_url=self.login_url,
            db_uri=os.getenv('DATABASE_URI')
        )

    def encrypt_password(self, password):
        """使用SM4加密密码"""
        try:
            if not self.sm4_key or len(self.sm4_key) != 32:
                raise ValueError("SM4密钥必须是32字符的16进制字符串")
            
            key_bytes = bytes.fromhex(self.sm4_key)
            if len(key_bytes) != 16:
                raise ValueError("转换后的SM4密钥必须为16字节")
            key_str = key_bytes.decode('latin1')
            
            encrypted_base64 = encrypt_ecb(password, key_str)
            cipher_bytes = base64.b64decode(encrypted_base64)
            return cipher_bytes.hex()
        except Exception as e:
            raise ValueError(f"密码加密失败: {str(e)}")

    def invalidate_session(self):
        """作废当前用户的会话(使用Repository版本)"""
        try:
            self.state_machine.repo.invalidate_session(self.username)
            self.logger.info(f"已作废用户 {self.username} 的会话")
            return True
        except Exception as e:
            self.logger.error(f"作废会话失败: {str(e)}")
            return False

    def get_session(self):
        """获取有效会话(状态机版本)"""
        self.state_machine.load_config()
        while self.state_machine.state != 'ready':
            if self.state_machine.state == 'error':
                raise RuntimeError("获取会话失败")
            
        return self.state_machine.context.get('result')

    def refresh_access_token(self):
        """刷新access_token(使用Repository版本)"""
        try:
            session = self.state_machine.repo.get_active_session(self.username)
            if not session:
                raise ValueError("没有有效的登录会话")
                
            new_token_url = os.getenv('NEW_TOKEN_URL')
            response = requests.get(new_token_url, cookies=session.cookies)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 200:
                    updated = {
                        'access_token': data['data']['access_token'],
                        'expires_at': datetime.now() + timedelta(days=1)
                    }
                    self.state_machine.repo.save_session({
                        'user_id': self.username,
                        **updated
                    })
                    return data['data']['access_token']
                raise ValueError(f"获取新token失败: {data.get('message')}")
            raise ValueError(f"刷新token请求失败: HTTP {response.status_code}")
        except Exception as e:
            self.logger.error(f"刷新token失败: {str(e)}")
            raise ValueError(f"刷新access_token时出错: {str(e)}")

    def get_dept_cookie(self, dept_id):
        """获取科室相关cookie(使用Repository版本)"""
        try:
            # 获取当前有效会话
            session = self.state_machine.repo.get_active_session(self.username)
            if not session:
                self.logger.warning("没有有效的登录会话，重新获取...")
                session_data = self.get_session()
                if not session_data or not session_data.get('access_token'):
                    raise ValueError("无法获取有效的登录会话")

            if not session.access_token:
                self.logger.warning("会话中缺少access_token，尝试刷新...")
                session.access_token = self.refresh_access_token()
                if not session.access_token:
                    raise ValueError("无法获取有效的access_token")

            # 构造请求获取科室cookie
            url = f"{os.getenv('DEPT_COOKIE_URL')}?token={session.access_token}&deptId={dept_id}"
            response = requests.get(url, cookies=session.cookies)
            
            if response.status_code == 200:
                # 合并新旧cookies
                new_cookies = dict(response.cookies)
                merged_cookies = {**session.cookies, **new_cookies}
                
                # 更新数据库中的cookies
                self.state_machine.repo.save_session({
                    'user_id': self.username,
                    'cookies': merged_cookies,
                    'access_token': session.access_token,
                    'user_code': session.user_code,
                    'expires_at': session.expires_at
                })
                return merged_cookies
                
            elif response.status_code == 401:  # token失效
                self.logger.warning("access_token失效，尝试刷新")
                new_token = self.refresh_access_token()
                if new_token:
                    # 使用新token重试
                    url = f"{os.getenv('DEPT_COOKIE_URL')}?token={new_token}&deptId={dept_id}"
                    response = requests.get(url, cookies=session.cookies)
                    if response.status_code == 200:
                        new_cookies = dict(response.cookies)
                        merged_cookies = {**session.cookies, **new_cookies}
                        self.state_machine.repo.save_session({
                            'user_id': self.username,
                            'cookies': merged_cookies
                        })
                        return merged_cookies
                    raise ValueError(f"使用新token获取科室cookie失败: HTTP {response.status_code}")
            raise ValueError(f"获取科室cookie失败: HTTP {response.status_code}")
        except Exception as e:
            self.logger.error(f"获取科室cookie失败: {str(e)}")
            raise ValueError(f"获取科室cookie时出错: {str(e)}")

    def _perform_login(self):
        """执行登录流程"""
        from scrapy.http import TextResponse
        
        encrypted_pwd = self.encrypt_password(self.password)
        
        login_data = {
            "scheme": "login3",
            "userName": self.username,
            "passWord": encrypted_pwd,
            "city": "未知",
            "ip": "10.248.200.14",
            "equipmentType": "PG199",
            "needverifycode": "0"
        }
        
        self.logger.debug(f"提交登录表单: {login_data}")

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
    #        "User-Agent": "Mozilla/5.0 (Linux; Android 10; PG199 Build/UP1A.231005.007; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/74.0.3729.186 Mobile Safari/537.36"
        }
        
        try:
            response = requests.post(
                self.login_url,
                data=login_data,
                headers=headers,
                allow_redirects=False
            )
            
            self.logger.debug(f"登录响应: {response}")
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 200:
                    # 构造会话数据
                    expires = None
                    if 'Set-Cookie' in response.headers:
                        set_cookie = response.headers['Set-Cookie']
                        if isinstance(set_cookie, str):
                            set_cookie = [set_cookie]
                        else:
                            set_cookie = [c.strip() for c in set_cookie.split(',') if c.strip()]
                        
                        for cookie in set_cookie:
                            if 'Expires=' in cookie:
                                expires_str = cookie.split('Expires=')[1].split(';')[0]
                                try:
                                    expires = parsedate_to_datetime(expires_str) if expires_str else None
                                except ValueError:
                                    self.logger.warning(f"无法解析过期时间: {expires_str}, 将使用默认过期时间")
                                    expires = datetime.now() + timedelta(hours=1)
                                break
                    
                    session_data = {
                        'user_id': self.username,
                        'cookies': dict(response.cookies),
                        'access_token': result['data']['access_token'],
                        'user_code': result['data']['user_code'],
                        'expires_at': expires or datetime.now() + timedelta(days=30)
                    }
                    self.logger.debug(f"会话数据: {session_data}")
                    # 保存会话到数据库
                    self.save_session(session_data)
                    return session_data
                else:
                    raise ValueError(f"登录失败: {result.get('message')}")
            else:
                raise ValueError(f"HTTP请求失败: {response.status_code}")
        except Exception as e:
            raise ValueError(f"登录过程中发生错误: {str(e)}")

    def save_session(self, session_data):
        """保存会话到数据库(使用Repository版本)"""
        try:
            self.state_machine.repo.save_session(session_data)
            self.logger.debug("成功保存会话数据")
        except Exception as e:
            self.logger.error(f"保存会话失败: {str(e)}")
            raise
