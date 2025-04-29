# Enhanced InfoTimelineSpider with incremental upsert logic and robust parsing
# 修改说明：
# 1. parse_patient_list:
#    - 增量插入/更新患者信息。先查询已存在的 EMPI，再 bulk_insert_mappings 插入新患者；
#      当 force_updatedb=True 时，对已存在患者使用 bulk_update_mappings 更新。
#    - 去掉 Scrapy callback 中的 return 生成器写法，统一使用 yield。
# 2. fetch_visit_records:
#    - 正确定位 Scrapy.Request 参数，move handle_httpstatus_list 到 meta 中，避免多余参数。
# 3. parse_visit_records:
#    - 使用 payload.get(...) or [] 保证 patientTimeLine 和 timeLine 始终为列表，绝不对 None 迭代。
#    - 构造 new_records，批量放入 record_buffer，并在达到阈值时直接调用 batch_save_records。
# 4. batch_save_records:
#    - 分批（batch_size=100）插入/更新：只处理足够大小的批次，保留剩余；
#    - 在同一方法末尾处理剩余所有条目，确保最后不满批次也被写入；
#    - 统计 total_inserted/total_updated 并更新 stats。
# 5. handle_request_error:
#    - 修正 HttpError 导入路径，捕获并记录 HTTP 错误状态。

import scrapy
import os
import json
from datetime import datetime
from scrapy.spidermiddlewares.httperror import HttpError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from crawler.models import Patient, VisitRecord
from .login_handler import LoginHandler
from dotenv import load_dotenv

class InfoTimelineSpider(scrapy.Spider):
    name = "info-timeline-spider"

    def __init__(self, user_id=None, dept_id=None, type=None, start_date=None, end_date=None,
                 force_updatedb=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not all([user_id, dept_id, type]):
            raise ValueError("必须提供 user_id, dept_id 和 type 参数")
        if type not in ['I', 'O']:
            raise ValueError("type 参数必须是 'I' 或 'O'")
        if not dept_id:
            raise ValueError("dept_id 参数不能为空")

        load_dotenv()
        self.user_id = user_id
        self.dept_id = dept_id
        self.type = type
        self.start_date = start_date if type == 'O' else None
        self.end_date = end_date if type == 'O' else None
        self.force_updatedb = force_updatedb

        self.record_buffer = []
        self.stats = {'patients': 0, 'records': 0, 'saved': 0, 'errors': 0, 'updated': 0}

        self.patient_list_url = os.getenv('PATIENT_LIST_URL')
        self.record_base_url = os.getenv('PATIENT_VISIT_RECORD_URL')
        self.engine = create_engine(os.getenv('DATABASE_URI'))
        self.Session = sessionmaker(bind=self.engine)
        self.login_handler = LoginHandler()

    def start_requests(self):
        # 获取cookie：yihu-ccd
        session = self.login_handler.get_ccd_session(self.user_id, self.dept_id)
        self.ccd_cookies = session['cookies']

        if not session:
            raise ValueError("无法获取有效会话")

        formdata = {'type': self.type, 'dept_id': self.dept_id,
                    'patient_name': '', 'inpatient_no': '', 'inpatient_diagnose': ''}
        if self.type == 'O':
            formdata.update({'start_date': self.start_date, 'end_date': self.end_date})

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        yield scrapy.FormRequest(
            method='POST', url=self.patient_list_url,
            cookies=self.ccd_cookies, meta={'cookiejar': 1},
            formdata=formdata, headers=headers, callback=self.parse_patient_list
        )

    def parse_patient_list(self, response):
        try:
            data = json.loads(response.text)
            patients = data.get('data', {}).get('List', {}).get('InPatientMainInfo') or []
            if isinstance(patients, dict): patients = [patients]

            mappings = []
            for p in patients:
                empi = p.get('EMPI')
                if not empi: continue
                mappings.append({
                    'empi': empi,
                    'patient_name': p.get('NAME'),
                    'patient_no': p.get('PATIENT_NO'),
                    'patient_type': p.get('IN_STATE'),
                    'dept_code': p.get('DEPT_CODE'),
                    'raw_data': p
                })
            empi_list = [m['empi'] for m in mappings]

            with self.Session() as session:
                existing = {e[0] for e in session.query(Patient.empi)
                                    .filter(Patient.empi.in_(empi_list)).all()}

                to_insert = [m for m in mappings if m['empi'] not in existing]
                if to_insert:
                    session.bulk_insert_mappings(Patient, to_insert)

                if self.force_updatedb:
                    to_update = [m for m in mappings if m['empi'] in existing]
                    if to_update:
                        session.bulk_update_mappings(Patient, to_update)

                session.commit()
                self.stats['patients'] = len(existing) + len(to_insert)
                self.logger.info(f"患者列表：{len(to_insert)} 新，{len(existing)} 已存")

            for m in mappings:
                yield self.fetch_visit_records(m['empi'], m['patient_name'])
        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"解析患者列表失败: {e}")
            self.logger.error(f"原始响应: {response.text}")

    def fetch_visit_records(self, empi, patient_name):
        return scrapy.Request(
            url = f"{self.record_base_url}?id={empi}",
            callback=self.parse_visit_records,
            errback=self.handle_request_error,
            meta={'cookiejar': 1, 'patient_empi': empi, 'patient_name': patient_name,
                  'handle_httpstatus_list': [400,401,403,404,500]}
        )

    def parse_visit_records(self, response):
        # —— 会话过期检测 ——  
        if self.login_handler.is_ccd_expired_response(response):
            self.logger.warning("检测到 CCD 会话已过期，正在重建并重试…")
            # 重建 CCD 会话
            new_sess = self.login_handler.mark_ccd_invalid(self.user_id, self.dept_id)
            # 用新 Cookie 重试当前 URL
            yield scrapy.Request(
                url=response.url,
                callback=self.parse_visit_records,
                dont_filter=True,
                cookies=new_sess['cookies'],        # 新的 CCD cookies
                meta={'cookiejar': response.meta.get('cookiejar', 1),
                      'patient_empi': response.meta['patient_empi'],
                      'patient_name': response.meta['patient_name'],
                      'handle_httpstatus_list': [200,302]}
            )
            return

        empi = response.meta.get('patient_empi')
        pname = response.meta.get('patient_name')
        try:
            payload = json.loads(response.text)
            if payload.get('code') != 200:
                self.logger.error(f"获取就诊记录失败: {payload.get('message')}")
                return
            entries = payload.get('data', {}).get('patientTimeLine') or []
            if not entries:
                self.logger.info(f"{pname}({empi})无就诊记录")
                return

            new_records = []
            for entry in entries:
                visits = entry.get('timeLine') or []
                for v in visits:
                    vid = v.get('visitFlowId')
                    if not vid: continue
                    new_records.append({
                        'visit_flow_id': vid,
                        'empi': empi,
                        'admit_date': datetime.strptime(v.get('admitDate',''), '%Y%m%d%H%M%S')
                                        if v.get('admitDate') else None,
                        'discharge_date': datetime.strptime(v.get('dischargeDate',''), '%Y%m%d%H%M%S')
                                        if v.get('dischargeDate') else None,
                        'dept_code': v.get('deptCode'),
                        'dept_name': v.get('deptName'),
                        'clinic_type': v.get('clinicTypeName'),
                        'visit_flow_domain': v.get('visitFlowDomain'),
                        'timeline_raw_data': v
                    })

            cnt = len(new_records)
            self.stats['records'] += cnt
            self.logger.info(f"{pname}({empi}) 获取 {cnt} 条就诊记录")

            if new_records:
                self.record_buffer.extend(new_records)
                if len(self.record_buffer) >= 100:
                    self.batch_save_records()
        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"解析就诊记录失败: {e}")
            self.logger.error(f"{pname}({empi}) 原始响应: {response.text}")

    def batch_save_records(self):
        """对 visit_flow_id 做增量插入/更新，并填充 patient_id 外键"""
        if not self.record_buffer:
            return
        BATCH = 100
        total_i = total_u = 0
        with self.Session() as session:
            # 1) 先查询所有 EMPI 对应的 Patient.id
            empis = list({r['empi'] for r in self.record_buffer})
            patients = session.query(Patient.empi, Patient.id) \
                .filter(Patient.empi.in_(empis)).all()
            empi_to_id = {empi: pid for empi, pid in patients}
            # 2) 为每条记录填充 patient_id
            for rec in self.record_buffer:
                rec['patient_id'] = empi_to_id.get(rec['empi'])

            # 3) 分批处理
            while len(self.record_buffer) >= BATCH:
                batch = self.record_buffer[:BATCH]
                vfids = [r['visit_flow_id'] for r in batch]
                exist = {x[0] for x in session.query(VisitRecord.visit_flow_id)
                                  .filter(VisitRecord.visit_flow_id.in_(vfids)).all()}
                ins = [r for r in batch if r['visit_flow_id'] not in exist]
                upd = [r for r in batch if r['visit_flow_id'] in exist]
                if ins:
                    session.bulk_insert_mappings(VisitRecord, ins)
                if self.force_updatedb and upd:
                    session.bulk_update_mappings(VisitRecord, upd)
                session.commit()
                total_i += len(ins)
                total_u += len(upd) if self.force_updatedb else 0
                self.record_buffer = self.record_buffer[BATCH:]

            # 4) 处理剩余不足 BATCH 的记录
            if self.record_buffer:
                batch = self.record_buffer
                vfids = [r['visit_flow_id'] for r in batch]
                exist = {x[0] for x in session.query(VisitRecord.visit_flow_id)
                                  .filter(VisitRecord.visit_flow_id.in_(vfids)).all()}
                ins = [r for r in batch if r['visit_flow_id'] not in exist]
                upd = [r for r in batch if r['visit_flow_id'] in exist]
                if ins:
                    session.bulk_insert_mappings(VisitRecord, ins)
                if self.force_updatedb and upd:
                    session.bulk_update_mappings(VisitRecord, upd)
                session.commit()
                total_i += len(ins)
                total_u += len(upd) if self.force_updatedb else 0
                self.record_buffer.clear()

        # 5) 更新统计并记录日志
        self.stats['saved'] += total_i
        self.stats['updated'] += total_u
        self.logger.info(f"写入: {total_i}, 更新: {total_u} 更新完毕")

    def handle_request_error(self, failure):
        self.stats['errors'] += 1
        self.logger.error(f"请求失败: {failure!r}")
        if failure.check(HttpError):
            resp = failure.value.response
            self.logger.error(f"HTTP 错误: {resp.status} {resp.url}")

    def closed(self, reason):
        # 最后补写
        if self.record_buffer:
            self.logger.info(f"关闭时写入剩余{len(self.record_buffer)} 条记录")
            self.batch_save_records()
