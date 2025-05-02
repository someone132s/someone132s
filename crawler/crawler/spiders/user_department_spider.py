import scrapy
from .login_handler import LoginHandler
from crawler.init_db import DatabaseInitializer
import json
from dotenv import load_dotenv
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from urllib.parse import urlencode

class UserDepartmentSpider(scrapy.Spider):
    name = "user-department-spider"
    
    def __init__(self, user_id=None, *args, **kwargs):
        super(UserDepartmentSpider, self).__init__(*args, **kwargs)
        if not all([user_id]):
            raise ValueError("必须提供user_id参数")
        self.user_id = user_id

        load_dotenv()
        login_url = os.getenv('LOGIN_URL')
        self.allowed_domains = [login_url.split('://')[1].split('/')[0]]
        self.user_info_url = os.getenv('USER_INFO_URL')
        self.dept_url = os.getenv('DEPT_URL')
        
        # 检查数据库结构
        db_checker = DatabaseInitializer()
        if not db_checker.check_db():
            self.logger.error("数据库表结构检查失败，请确认表结构是否正确")
            sys.exit(1)
        self.logger.info("数据库表结构检查通过")
        
        self.login_handler = LoginHandler()

    def start_requests(self, cookies=None):
        """使用LoginHandler获取会话"""
        if cookies is None:
            session = self.login_handler.get_portal_session(self.user_id)
            if not session:
                raise ValueError("无法获取有效 Portal 会话")
            cookies = session['cookies']
        
        # 使用会话中的cookies发起请求
        yield scrapy.Request(
            url=self.user_info_url,
            cookies=cookies,
            callback=self.parse
        )

    def parse(self, response):
        """解析用户信息并存储"""
        from crawler.models import UserInfo, Department
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
                    # 保存用户信息
                    user_info = db_session.query(UserInfo)\
                        .filter_by(login_name=login_name)\
                        .first()
                    
                    if user_info:
                        user_info.user_code = user_code
                        user_info.raw_data = user_data
                    else:
                        user_info = UserInfo(
                            login_name=login_name,
                            user_code=user_code,
                            raw_data=user_data
                        )
                        db_session.add(user_info)
                    
                    # 获取科室列表
                    dept_url = self.dept_url
                    params = {
                        'show_mod': 1,
                        'dept_types': 'I,O,OP'
                    }
                    yield scrapy.Request(
                        url=f"{dept_url}?{urlencode(params)}",
                        cookies=response.request.cookies,
                        callback=self.parse_departments,
                        meta={'db_session': db_session}
                    )
                    
                except Exception as e:
                    db_session.rollback()
                    self.logger.error(f"数据库操作失败: {str(e)}")
            else:
                self.logger.error(f"获取用户信息失败: {data.get('message')}")
        except json.JSONDecodeError:
            self.logger.error("用户信息响应不是有效的JSON格式")

    def parse_departments(self, response):
        """解析科室列表并存储"""
        from crawler.models import Department
        db_session = response.meta['db_session']
        
        try:
            data = json.loads(response.text)
            if data.get('code') == 200:
                dept_list = data.get('data', [{}])[0].get('deptList', [])
                
                for dept in dept_list:
                    dept_code = dept.get('CODE')
                    dept_name = dept.get('DEPT_NAME')
                    
                    if not dept_code or not dept_name:
                        continue
                    
                    # 保存科室信息
                    department = db_session.query(Department)\
                        .filter_by(dept_code=dept_code)\
                        .first()
                    
                    if department:
                        department.dept_name = dept_name
                        department.raw_data = dept
                    else:
                        department = Department(
                            dept_code=dept_code,
                            dept_name=dept_name,
                            raw_data=dept
                        )
                        db_session.add(department)
                
                db_session.commit()
                self.logger.info(f"成功保存{len(dept_list)}个科室信息")
            else:
                self.logger.error(f"获取科室列表失败: {data.get('message')}")
        except json.JSONDecodeError:
            self.logger.error("科室列表响应不是有效的JSON格式")
        finally:
            db_session.close()
