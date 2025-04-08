import os
import requests
import logging
from pysm4 import encrypt_ecb
import base64
import json
from dotenv import load_dotenv
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from crawler.models import SpiderSession
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

class LoginHandler:
    def __init__(self):
        load_dotenv()
        self.username = os.getenv('USERNAME')
        self.password = os.getenv('PASSWORD') 
        self.sm4_key = os.getenv('SM4_KEY')
        self.login_url = os.getenv('LOGIN_URL')
        self.logger = logging.getLogger(__name__)
        
        # 初始化数据库连接
        self.engine = create_engine(os.getenv('DATABASE_URI'))
        self.Session = sessionmaker(bind=self.engine)

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
        """作废当前用户的会话"""
        db_session = self.Session()
        try:
            db_session.query(SpiderSession)\
                .filter_by(user_id=self.username)\
                .delete()
            db_session.commit()
            self.logger.info(f"已作废用户 {self.username} 的会话")
            return True
        except Exception as e:
            db_session.rollback()
            self.logger.error(f"作废会话失败: {str(e)}")
            return False
        finally:
            db_session.close()

    def _verify_session(self, cookies):
        """验证会话是否有效"""
        import requests
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

    def get_session(self):
        """获取有效会话，优先从数据库获取"""
        db_session = self.Session()
        try:
            # 检查数据库中是否有有效会话
            session = db_session.query(SpiderSession)\
                .filter_by(user_id=self.username)\
                .filter(SpiderSession.expires_at > datetime.now())\
                .first()
                
            if session:
                # 验证会话有效性
                if not self._verify_session(session.cookies):
                    self.logger.warning("会话已失效，执行重新登录")
                    self.invalidate_session()
                    return self._perform_login()
                    
                self.logger.debug(f"使用有效会话 - 用户: {session.user_id}, 过期时间: {session.expires_at}")
                return {
                    'user_id': session.user_id,
                    'cookies': session.cookies,
                    'access_token': session.access_token,
                    'user_code': session.user_code
                }
                
            # 没有有效会话则执行登录
            self.logger.debug(f"未找到有效会话，执行新登录 - 用户: {self.username}")
            session_data = self._perform_login()
            if session_data:
                self.logger.debug(f"登录成功 - 用户: {self.username}, 过期时间: {session_data.get('expires_at')}")
            return session_data
        finally:
            db_session.close()

    def refresh_access_token(self):
        """刷新access_token"""
        db_session = self.Session()
        try:
            session = db_session.query(SpiderSession)\
                .filter_by(user_id=self.username)\
                .filter(SpiderSession.expires_at > datetime.now())\
                .first()
                
            if not session:
                raise ValueError("没有有效的登录会话")
                
            import requests
            url = "https://yihu.gzsums.net/portal/newtoken"
            response = requests.get(url, cookies=session.cookies)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 200:
                    session.access_token = data['data']['access_token']
                    db_session.commit()
                    return session.access_token
                else:
                    raise ValueError(f"获取新token失败: {data.get('message')}")
            else:
                raise ValueError(f"刷新token请求失败: HTTP {response.status_code}")
        except Exception as e:
            db_session.rollback()
            raise ValueError(f"刷新access_token时出错: {str(e)}")
        finally:
            db_session.close()

    def get_dept_cookie(self, dept_id):
        """获取科室相关cookie"""
        db_session = self.Session()
        try:
            # 获取当前有效会话
            session = db_session.query(SpiderSession)\
                .filter_by(user_id=self.username)\
                .filter(SpiderSession.expires_at > datetime.now())\
                .first()
                
            if not session:
                self.logger.warning("没有有效的登录会话，重新获取...")
                session_data = self._perform_login()
                if not session_data or not session_data.get('access_token'):
                    raise ValueError("无法获取有效的登录会话")
                # 从新会话创建数据库记录
                session = SpiderSession(
                    user_id=session_data['user_id'],
                    cookies=session_data['cookies'],
                    access_token=session_data['access_token'],
                    user_code=session_data['user_code'],
                    expires_at=session_data['expires_at']
                )
                db_session.add(session)
                db_session.commit()

            if not session.access_token:
                self.logger.warning("会话中缺少access_token，尝试刷新...")
                session.access_token = self.refresh_access_token()
                if not session.access_token:
                    raise ValueError("无法获取有效的access_token")
                db_session.commit()

            # 构造请求获取科室cookie
            url = f"https://yihu.gzsums.net/ccd?token={session.access_token}&deptId={dept_id}"
            response = requests.get(url, cookies=session.cookies)
            
            if response.status_code == 200:
                # 合并新旧cookies
                new_cookies = dict(response.cookies)
                merged_cookies = {**session.cookies, **new_cookies}
                
                # 更新数据库中的cookies
                session.cookies = merged_cookies
                db_session.commit()
                
                return merged_cookies
            elif response.status_code == 401:  # token失效
                self.logger.warning("access_token失效，尝试刷新")
                new_token = self.refresh_access_token()
                if new_token:
                    # 使用新token重试
                    url = f"https://yihu.gzsums.net/ccd?token={new_token}&deptId={dept_id}"
                    response = requests.get(url, cookies=session.cookies)
                    if response.status_code == 200:
                        new_cookies = dict(response.cookies)
                        merged_cookies = {**session.cookies, **new_cookies}
                        session.cookies = merged_cookies
                        db_session.commit()
                        return merged_cookies
                    else:
                        raise ValueError(f"使用新token获取科室cookie失败: HTTP {response.status_code}")
            else:
                raise ValueError(f"获取科室cookie失败: HTTP {response.status_code}")
        except Exception as e:
            db_session.rollback()
            raise ValueError(f"获取科室cookie时出错: {str(e)}")
        finally:
            db_session.close()

    def _perform_login(self):
        """执行登录流程"""
        import requests
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
        """保存会话到数据库"""
        db_session = self.Session()
        try:
            # 先查询是否已有会话
            existing = db_session.query(SpiderSession)\
                .filter_by(user_id=session_data['user_id'])\
                .first()
                
            if existing:
                # 更新现有会话
                self.logger.debug("更新现有会话")
                existing.cookies = session_data['cookies']
                existing.access_token = session_data['access_token']
                existing.user_code = session_data['user_code']
                existing.expires_at = session_data['expires_at']
            else:
                # 创建新会话
                self.logger.debug("创建新会话")
                session = SpiderSession(
                    user_id=session_data['user_id'],
                    cookies=session_data['cookies'],
                    access_token=session_data['access_token'],
                    user_code=session_data['user_code'],
                    expires_at=session_data['expires_at']
                )
                db_session.add(session)
                
            db_session.commit()
        except Exception as e:
            db_session.rollback()
            raise
        finally:
            db_session.close()
