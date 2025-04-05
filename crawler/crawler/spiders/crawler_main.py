import scrapy
from .login_handler import LoginHandler
from crawler.init_db import DatabaseInitializer
import json
from dotenv import load_dotenv
import os
import sys

class CrawlerMainSpider(scrapy.Spider):
    name = "crawler-main"
    
    def __init__(self):
        load_dotenv()
        login_url = os.getenv('LOGIN_URL')
        self.allowed_domains = [login_url.split('://')[1].split('/')[0]]
        self.start_urls = [login_url.rsplit('/', 2)[0]]  # 移除/portal/login部分
        
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
            url=self.start_urls[0],
            cookies=session['cookies'],
            callback=self.parse
        )

    def parse(self, response):
        """解析页面数据"""
        # 检查会话是否有效
        if 'login' in response.url:
            self.logger.warning("会话已过期，需要重新登录")
            session = self.login_handler.get_session()
            yield scrapy.Request(
                url=self.start_urls[0],
                cookies=session['cookies'],
                callback=self.parse,
                dont_filter=True
            )
            return
            
        # 登录成功，输出响应并退出
        self.logger.info(f"登录成功，响应内容: {response.text}")
        return
