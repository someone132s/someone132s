import scrapy
from urllib.parse import urlencode
from datetime import datetime
from crawler.models import Patient, VisitRecord
from .login_handler import LoginHandler
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
import json

class PatientSpider(scrapy.Spider):
    name = "patient"
    
    def __init__(self, type=None, dept_id=None, start_date=None, end_date=None, 
                 force_updatedb=False, fetch_records=True, *args, **kwargs):
        super(PatientSpider, self).__init__(*args, **kwargs)
        self.redirect_count = 0  # 重定向计数器
        load_dotenv()
        self.fetch_records = fetch_records  # 控制是否获取就诊记录
        
        if type not in ['I', 'O']:
            raise ValueError("type参数必须是'I'或'O'")
        if not dept_id:
            raise ValueError("dept_id参数不能为空")
            
        self.type = type
        self.dept_id = dept_id
        self.start_date = start_date if type == 'O' else None
        self.end_date = end_date if type == 'O' else None
        self.force_updatedb = force_updatedb  # 强制更新数据库标志

        self.patient_list_url = os.getenv('PATIENT_LIST_URL')
        self.allowed_domains = ["yihu.gzsums.net"]
        
        # 初始化数据库
        self.engine = create_engine(os.getenv('DATABASE_URI'))
        self.Session = sessionmaker(bind=self.engine)

        self.login_handler = LoginHandler()

    def start_requests(self):
        """使用LoginHandler获取会话"""
        self.login_handler.get_dept_cookie(self.dept_id)
        session = self.login_handler.get_session()

        formdata = {
            'type': self.type,
            'dept_id\t': self.dept_id,  # 添加制表符编码
            'patient_name': '',
            'inpatient_no': '',
            'inpatient_diagnose': ''
        }
        
        if self.type == 'O':
            formdata['start_date'] = self.start_date
            formdata['end_date'] = self.end_date

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
#            "User-Agent": "Mozilla/5.0 (Linux; Android 10; PG199 Build/UP1A.231005.007; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/74.0.3729.186 Mobile Safari/537.36",
            "Accept": "*/*",
#            "Host": "yihu.gzsums.net",
            "Connection": "keep-alive",
        }

        request = scrapy.FormRequest(
            method='POST',
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
        # 状态码检查
        if response.status == 302:
            self.redirect_count += 1
            if self.redirect_count > 1:  # 避免循环
                raise ValueError("多次重定向，可能登录失败")
                
            self.logger.warning("会话失效，重新发起请求")
            # 确保使用最新的cookies
            session = self.login_handler.get_session()
            if session and 'cookies' in session:
                response.request.cookies.update(session['cookies'])
            return self.start_requests()
        
        elif response.status != 200:
            self.logger.error(f"无效响应状态码: {response.status}")
            raise ValueError(f"请求失败，状态码: {response.status}")
        
        # 重置计数器
        self.redirect_count = 0
        
        db_session = self.Session()
        try:
            data = json.loads(response.text)
            patients = data.get('data', {}).get('List', {}).get('InPatientMainInfo', [])
            #print("#####patients",patients)
            if not isinstance(patients, list):
                self.logger.error(f"无效的患者数据格式: {type(patients)}")
                patients = []
            
            updated_count = 0
            inserted_count = 0
            for idx, patient in enumerate(patients, 1):
                empi = patient.get('EMPI')
                if not empi:
                    self.logger.warning(f"患者记录{idx}缺少EMPI，跳过")
                    continue
                
                if self.fetch_records:
                    yield scrapy.Request(
                        url=f"https://yihu.gzsums.net/ccd/api/inpatient/record?id={empi}",
                        cookies=response.request.cookies,
                        callback=self.parse_visit_records,
                        meta={'patient_empi': empi}
                    )
                
                # 打印诊断信息
                diag = patient.get('DIAG_NAME1')
                self.logger.info(f"处理患者{idx}/{len(patients)}: {patient.get('NAME')} - 诊断: {diag}")
                #调试信息
                #print("#####patient",patient)
                # 保存患者信息
                existing = db_session.query(Patient)\
                    .filter_by(empi=empi)\
                    .first()
                    
                if self.force_updatedb or not existing:
                    if existing:
                        existing.patient_name = patient.get('NAME')
                        existing.patient_no = patient.get('PATIENT_NO')
                        existing.patient_type = self.type
                        existing.dept_code = self.dept_id
                        existing.raw_data = patient
                        updated_count += 1
                    else:
                        new_patient = Patient(
                            empi=empi,
                            patient_name=patient.get('NAME'),
                            patient_no=patient.get('PATIENT_NO'),
                            patient_type=self.type,
                            dept_code=self.dept_id,
                            raw_data=patient
                        )
                        db_session.add(new_patient)
                        inserted_count += 1
            
            try:
                db_session.commit()
                self.logger.info(f"患者记录处理完成 - 本次返回: {len(patients)}条, 更新: {updated_count}条, 新增: {inserted_count}条")
            except Exception as e:
                db_session.rollback()
                self.logger.error(f"提交事务失败: {str(e)}")
                raise    
              
        except Exception as e:
            db_session.rollback()
            self.logger.error(f"保存患者信息失败: {str(e)}")
            self.logger.error(f"响应: {response.text}")
        finally:
            db_session.close()

    def parse_visit_records(self, response):
        empi = response.meta['patient_empi']
        data = json.loads(response.text)
        if data.get('code') != 200:
            self.logger.error(f"获取就诊记录失败: {data.get('message')}")
            return
            
        timeline = data.get('data', {}).get('patientTimeLine', [])
        if not timeline:
            self.logger.info(f"患者{empi}无就诊记录")
            return
            
        db_session = self.Session()
        try:
            for record in timeline:
                for visit in record.get('timeLine', []):
                    visit_flow_id = visit.get('visitFlowId')
                    if not visit_flow_id:
                        continue
                        
                    admit_date_str = visit.get('admitDate')
                    admit_date = datetime.strptime(admit_date_str, '%Y%m%d%H%M%S') if admit_date_str else None
                    
                    existing = db_session.query(VisitRecord)\
                        .filter_by(visit_flow_id=visit_flow_id)\
                        .first()
                        
                    if existing:
                        existing.admit_date = admit_date
                        existing.dept_code = visit.get('deptCode')
                        existing.dept_name = visit.get('deptName')
                        existing.clinic_type = visit.get('clinicTypeName')
                        existing.raw_data = visit
                    else:
                        new_visit = VisitRecord(
                            visit_flow_id=visit_flow_id,
                            empi=empi,
                            admit_date=admit_date,
                            dept_code=visit.get('deptCode'),
                            dept_name=visit.get('deptName'),
                            clinic_type=visit.get('clinicTypeName'),
                            raw_data=visit
                        )
                        db_session.add(new_visit)
                        
            db_session.commit()
            self.logger.info(f"成功保存患者{empi}的{len(timeline)}条就诊记录")
        except Exception as e:
            db_session.rollback()
            self.logger.error(f"保存就诊记录失败: {str(e)}")
            self.logger.error(f"错误记录: {json.dumps(visit, ensure_ascii=False)}")
        finally:
            db_session.close()
