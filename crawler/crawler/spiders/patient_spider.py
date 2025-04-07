import scrapy
from urllib.parse import urlencode
from datetime import datetime
from crawler.models import Patient
from .login_handler import LoginHandler
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
import json

class PatientSpider(scrapy.Spider):
    name = "patient"
    
    def __init__(self, type=None, dept_id=None, start_date=None, end_date=None, *args, **kwargs):
        super(PatientSpider, self).__init__(*args, **kwargs)
        load_dotenv()
        
        if type not in ['I', 'O']:
            raise ValueError("type参数必须是'I'或'O'")
        if not dept_id:
            raise ValueError("dept_id参数不能为空")
            
        self.type = type
        self.dept_id = dept_id
        self.start_date = start_date if type == 'O' else None
        self.end_date = end_date if type == 'O' else None
        
        self.patient_list_url = "https://yihu.gzsums.net/ccd/api/inpatient/list"
        self.allowed_domains = ["yihu.gzsums.net"]
        
        # 初始化数据库
        self.engine = create_engine(os.getenv('DATABASE_URI'))
        self.Session = sessionmaker(bind=self.engine)

        self.login_handler = LoginHandler()

    def start_requests(self):
        """使用LoginHandler获取会话"""
        session = self.login_handler.get_session()

        formdata = {
            'type': self.type,
            'dept_id': self.dept_id,
            'patient_name': '',
            'inpatient_no': '',
            'inpatient_diagnose': ''
        }
        
        if self.type == 'O':
            formdata['start_date'] = self.start_date
            formdata['end_date'] = self.end_date

        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; PG199 Build/UP1A.231005.007; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/74.0.3729.186 Mobile Safari/537.36"
        }

        request = scrapy.FormRequest(
            url=self.patient_list_url,
            cookies=session['cookies'],
            formdata=formdata,
            headers=headers,
            callback=self.parse_patient_list
        )
        
        # 打印完整的请求信息用于调试
        print("=== 请求URL ===")
        print(request.url)
        print("\n=== 请求头 ===")
        print(request.headers)
        print("\n=== 请求体 ===")
        print(request.body)
        print("\n=== Cookies ===")
        print(request.cookies)
        
        yield request

    def parse_patient_list(self, response):
        db_session = self.Session()
        #print("########",response.text)
        try:
            data = json.loads(response.text)
            if data.get('code') == 200:
                patients = data.get('data', [])
                
                for patient in patients:
                    empi = patient.get('empi')
                    if not empi:
                        continue
                        
                    # 保存患者信息
                    existing = db_session.query(Patient)\
                        .filter_by(empi=empi)\
                        .first()
                        
                    if existing:
                        existing.patient_name = patient.get('patient_name')
                        existing.inpatient_no = patient.get('inpatient_no')
                        existing.patient_type = self.type
                        existing.dept_code = self.dept_id
                        existing.raw_data = patient
                    else:
                        new_patient = Patient(
                            empi=empi,
                            patient_name=patient.get('patient_name'),
                            inpatient_no=patient.get('inpatient_no'),
                            patient_type=self.type,
                            dept_code=self.dept_id,
                            raw_data=patient
                        )
                        db_session.add(new_patient)
                
                db_session.commit()
                self.logger.info(f"成功保存{len(patients)}条患者记录")
            else:
                self.logger.error(f"获取患者列表失败: {data.get('message')}")
                
        except Exception as e:
            db_session.rollback()
            self.logger.error(f"保存患者信息失败: {str(e)}")
            #self.logger.error(f"响应: {response.text}")
        finally:
            db_session.close()
