import scrapy
from .login_handler import LoginHandler
from crawler.init_db import DatabaseInitializer
import json
from dotenv import load_dotenv
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

class CrawlerMainSpider(scrapy.Spider):
    name = "crawler-main"
    
    def __init__(self):
        load_dotenv()
        login_url = os.getenv('LOGIN_URL')
        self.allowed_domains = [login_url.split('://')[1].split('/')[0]]
        self.user_info_url = os.getenv('USER_INFO_URL')
        
        # 检查数据库结构
        db_checker = DatabaseInitializer()
        if not db_checker.check_db():
            self.logger.error("数据库表结构检查失败，请确认表结构是否正确")
            sys.exit(1)
        self.logger.info("数据库表结构检查通过")
        
        self.login_handler = LoginHandler()

    def start_requests(self):
        """使用LoginHandler获取会话"""
        session = self.login_handler.get_session()
        
        # 使用会话中的cookies发起请求
        yield scrapy.Request(
            url=self.user_info_url,
            cookies=session['cookies'],
            callback=self.parse
        )

    def parse(self, response):
        """解析用户信息并存储"""
        from crawler.models import UserInfo
        from sqlalchemy.orm import sessionmaker
        
        try:
            data = json.loads(response.text)
            if data.get('code') == 200:
                user_data = data.get('data', {})
                login_name = user_data.get('loginName')
                user_code = user_data.get('code')
                
                if not login_name:
                    self.logger.error("用户信息中缺少loginName字段")
                    return
                
                # 创建数据库会话
                engine = create_engine(os.getenv('DATABASE_URI'))
                Session = sessionmaker(bind=engine)
                db_session = Session()
                
                try:
                    # 检查是否已有记录
                    user_info = db_session.query(UserInfo)\
                        .filter_by(login_name=login_name)\
                        .first()
                    
                    if user_info:
                        # 更新现有记录
                        user_info.user_code = user_code
                        user_info.raw_data = user_data
                    else:
                        # 创建新记录
                        user_info = UserInfo(
                            login_name=login_name,
                            user_code=user_code,
                            raw_data=user_data
                        )
                        db_session.add(user_info)
                    
                    db_session.commit()
                    self.logger.info(f"成功保存用户信息: {login_name}")
                except Exception as e:
                    db_session.rollback()
                    self.logger.error(f"保存用户信息失败: {str(e)}")
                finally:
                    db_session.close()
            else:
                self.logger.error(f"获取用户信息失败: {data.get('message')}")
        except json.JSONDecodeError:
            self.logger.error("用户信息响应不是有效的JSON格式")
