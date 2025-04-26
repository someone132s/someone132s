import os
import json
import scrapy
from datetime import datetime
from scrapy.http import FormRequest
from crawler.models import MedicalDocument, VisitRecord
from .login_handler import LoginHandler
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv


class MedicalDocumentSpider(scrapy.Spider):
    name = "medical-document-spider"
    
    def __init__(self, empi=None, domain=None, admit_date=None, discharge_date=None, payload_types=None, 
                 visit_flow_id=None, doc_type=None, strict_date_check=True, **kwargs):
        required_params = {
            'empi': empi,
            'domain': domain,
            'admit_date': admit_date,
            'discharge_date': discharge_date,
            'payload_types': payload_types,
            'visit_flow_id': visit_flow_id,
            'doc_type': doc_type
        }
        
        missing_params = [name for name, value in required_params.items() if value is None]
        if missing_params:
            raise ValueError(f"缺少必要参数: {', '.join(missing_params)}")
            
        load_dotenv()
        self.empi = empi
        self.domain = domain
        self.admit_date = admit_date
        self.discharge_date = discharge_date
        self.strict_date_check = strict_date_check
        self.payload_types = payload_types
        self.visit_flow_id = visit_flow_id
        self.doc_type = doc_type
        self.base_url = os.getenv('MEDICAL_DOCUMENT_URL')
        self.current_page = 0
        self.all_documents = []
        self.engine = create_engine(os.getenv('DATABASE_URI'))
        self.Session = sessionmaker(bind=self.engine)
        self.login_handler = LoginHandler()
        super().__init__(**kwargs)

    def start_requests(self, page_no=0):
        session = self.login_handler.get_session()
        if not session:
            raise ValueError("无法获取有效会话")

        formdata = {
            "empi": self.empi,
            "domain": self.domain,
            "admitDate": self.admit_date,
            "payLoadType": self.payload_types,
            "type": self.doc_type,
            "pageNo": str(page_no)
        }

        if self.doc_type == "payLoadType.JianYan":
            formdata.update({"searchType": "0"})
        elif self.doc_type == "payLoadType.JianCha":
            formdata.update({
                "id": self.visit_flow_id,
                "jcSearchType": "1"
            })
        else:
            formdata["id"] = self.visit_flow_id

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "*/*",
            "Connection": "keep-alive",
        }

        yield FormRequest(
            url=self.base_url,
            method='POST',
            formdata=formdata,
            cookies=session['cookies'],
            headers=headers,
            callback=self.parse_page,
            meta={'page_no': page_no}
        )

    def parse_page(self, response):
        try:
            data = json.loads(response.text)
            
            if response.status != 200 or data.get("code") != 200:
                raise ValueError(f"Invalid response status: {response.status}, code: {data.get('code')}")
            
            if 'data' not in data or 'page' not in data['data'] or 'totalPage' not in data['data']['page']:
                raise ValueError("Invalid response: missing pagination data")
            self.total_pages = data['data']['page']['totalPage']
            
            if "data" in data and "list" in data["data"] and len(data["data"]["list"]) > 0:
                if "documentList" in data["data"]["list"][0]:
                    self.all_documents.extend(data["data"]["list"][0]["documentList"])
                else:
                    self.logger.warning(f"No documentList found in page {response.meta['page_no']}")
            
            self.current_page += 1
            if self.current_page < self.total_pages:
                yield from self.start_requests(page_no=self.current_page)
            else:
                self.logger.info(f"Total pages processed: {self.total_pages}")
                self.logger.info(f"Total documents collected: {len(self.all_documents) if self.all_documents else 0}")
                
                if self.all_documents:
                    yield from self.process_all_documents()
                
        except Exception as e:
            self.logger.error(f"Failed to parse page {response.meta['page_no']}: {str(e)}")
            raise

    def parse_special_date(self, date_str):
        """处理特殊日期值00010101000000并统一日期格式"""
        if date_str == "00010101000000":
            self.logger.info("发现住院中患者，使用当前时间作为出院时间")
            return datetime.now()
        
        try:
            # 尝试解析"20250410155830"格式
            if len(date_str) == 14 and date_str.isdigit():
                return datetime.strptime(date_str, "%Y%m%d%H%M%S")
            # 尝试解析"2025-04-01 11:13"格式并补全秒数
            if len(date_str) == 16 and ":" in date_str:  # 2025-04-01 11:13
                date_str += ":00"  # 补全秒数
                return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            # 其他格式尝试原样解析
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        except ValueError as e:
            self.logger.warning(f"无法解析日期格式: {date_str}, 错误: {str(e)}")
            return None

    def is_document_in_visit(self, doc):
        """检查文档是否在就诊时间范围内"""
        doc_time = self.parse_special_date(doc.get("dicomStudyTime"))
        if not doc_time:
            return not self.strict_date_check
            
        admit_time = self.parse_special_date(self.admit_date)
        discharge_time = self.parse_special_date(self.discharge_date)
        
        if not all([admit_time, discharge_time]):
            self.logger.error("无法解析入院或出院日期")
            return False
            
        return admit_time <= doc_time <= discharge_time

    def process_all_documents(self):
        session = self.Session()
        try:
            # 0. 过滤不在就诊期间的文档
            original_count = len(self.all_documents)
            self.all_documents = [doc for doc in self.all_documents if self.is_document_in_visit(doc)]
            filtered_count = original_count - len(self.all_documents)
            if filtered_count > 0:
                self.logger.info(f"过滤掉{filtered_count}份不在就诊期间的文档")
                
            # 1. 预取VisitRecord映射
            flow_ids = {d["visitFlowId"] for d in self.all_documents}
            mapping = session.query(VisitRecord.visit_flow_id, VisitRecord.id) \
                            .filter(VisitRecord.visit_flow_id.in_(flow_ids)) \
                            .all()
            flowid_to_recordid = {fid: recid for fid, recid in mapping}

            # 2. 批量upsert文档
            to_insert, to_update = [], []
            for doc in self.all_documents:
                doc_id = doc["documentuniqueid"]
                vrid = flowid_to_recordid.get(doc["visitFlowId"])
                base = {
                    "document_id": doc_id,
                    "visit_record_id": vrid,
                    "visit_flow_id": doc["visitFlowId"],
                    "empi": self.empi,
                    "file_path": doc.get("filepath"),
                    "payload_type": doc["payLoadType"],
                    "document_metadata": doc,
                    "updated_at": datetime.now()
                }
                existing = session.query(MedicalDocument.id) \
                                 .filter_by(document_id=doc_id).first()
                if existing:
                    base["id"] = existing[0]  # 添加主键id
                    to_update.append(base)
                else:
                    base["created_at"] = datetime.now()
                    to_insert.append(base)

            if to_insert:
                session.bulk_insert_mappings(MedicalDocument, to_insert)
            if to_update:
                session.bulk_update_mappings(MedicalDocument, to_update)
            session.commit()
            self.logger.info(f"Inserted {len(to_insert)} docs, updated {len(to_update)} docs")

        except Exception as e:
            session.rollback()
            self.logger.exception("批量处理文档失败")
            raise
        finally:
            session.close()
            return []
