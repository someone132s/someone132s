import os
import json
import scrapy
from urllib.parse import urlencode
from datetime import datetime
from crawler.models import Patient, VisitRecord
from .login_handler import LoginHandler
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv


class VisitItemsSpider(scrapy.Spider):
    name = "visit-items-spider"
    
    def __init__(self, empi=None, admit_date=None, domain=None, visit_id=None, *args, **kwargs):
        super(VisitItemsSpider, self).__init__(*args, **kwargs)
        if not all([empi, admit_date, domain, visit_id]):
            raise ValueError("必须提供empi, admit_date, domain和visit_id参数")
            
        self.empi = empi
        self.admit_date = admit_date
        self.domain = domain
        self.visit_id = visit_id

        self.url = os.getenv('PATIENT_VISIT_ITEMS_URL')
        
        load_dotenv()
        self.engine = create_engine(os.getenv('DATABASE_URI'))
        self.Session = sessionmaker(bind=self.engine)
        self.login_handler = LoginHandler()

    def start_requests(self):
        """构造并提交POST请求"""
        session = self.login_handler.get_session()
        if not session:
            raise ValueError("无法获取有效会话")

        formdata = {
            'empi': self.empi,
            'admitDate': self.admit_date,
            'domain': self.domain,
            'id': self.visit_id
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "*/*",
            "Connection": "keep-alive",
        }

        request = scrapy.FormRequest(
            url=self.url,
            method='POST',
            formdata=formdata,
            cookies=session['cookies'],
            headers=headers,
            callback=self.parse_response
        )
        
        yield request

    def parse_response(self, response):
        """解析API响应并保存到数据库"""
        if response.status != 200:
            self.logger.error(f"请求失败，状态码: {response.status}")
            raise ValueError(f"无效响应状态码: {response.status}")

        try:
            data = json.loads(response.text)
            if data.get('code') != 200:
                raise ValueError(f"API返回错误: {data.get('message')}")
                
            # 提取科室编号(取第一个document的patCurDep)
            pat_cur_dep = data.get('data', {}).get('documentList', [{}])[0].get('patCurDep')
            
            # 提取就诊项目列表
            payload_type_list = data.get('data', {}).get('payLoadTypeList', [])
            
            # 更新数据库
            db_session = self.Session()
            try:
                visit_record = db_session.query(VisitRecord)\
                    .filter_by(visit_flow_id=self.visit_id)\
                    .first()
                    
                if visit_record:
                    visit_record.pat_cur_dep = pat_cur_dep
                    visit_record.payload_type_info = payload_type_list
                    db_session.commit()
                    self.logger.info(f"成功更新就诊记录 {self.visit_id} 的科室和项目信息")
                else:
                    self.logger.warning(f"未找到就诊记录 {self.visit_id}，无法更新")
                    
            except Exception as e:
                db_session.rollback()
                self.logger.error(f"数据库更新失败: {str(e)}")
                raise
            finally:
                db_session.close()
                
            yield {
                'visit_flow_id': self.visit_id,
                'pat_cur_dep': pat_cur_dep,
                'payload_type_list': payload_type_list
            }
            
        except Exception as e:
            self.logger.error(f"解析响应失败: {str(e)}")
            raise
