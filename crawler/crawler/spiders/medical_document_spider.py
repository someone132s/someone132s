import os
import json
import scrapy
from datetime import datetime
from scrapy.http import FormRequest, Request
from crawler.models import MedicalDocument
from .login_handler import LoginHandler
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv


class MedicalDocumentSpider(scrapy.Spider):
    name = "medical-document-spider"
    
    def __init__(self, empi=None, domain=None, admit_date=None, payload_types=None, visit_flow_id=None, doc_type=None, **kwargs):
        # 检查参数是否为空字符串或None
        required_params = {
            'empi': empi,
            'domain': domain,
            'admit_date': admit_date,
            'payload_types': payload_types,
            'visit_flow_id': visit_flow_id,
            'doc_type': doc_type
        }
        
        missing_params = [name for name, value in required_params.items() if not value and value != 0]
        if missing_params:
            raise ValueError(f"缺少必要参数: {', '.join(missing_params)}")
            
        self.empi = empi
        self.domain = domain
        self.admit_date = admit_date
        self.payload_types = payload_types
        self.visit_flow_id = visit_flow_id
        self.doc_type = doc_type
        self.base_url = "https://yihu.gzsums.net/ccd/api/inpatient/data"
        self.current_page = 0
        self.all_documents = []  # 临时存储所有文档
        load_dotenv()
        self.engine = create_engine(os.getenv('DATABASE_URI'))
        self.Session = sessionmaker(bind=self.engine)
        self.login_handler = LoginHandler()
        super().__init__(**kwargs)

    def start_requests(self, page_no=0):
        """构造并提交POST请求"""
        session = self.login_handler.get_session()
        if not session:
            raise ValueError("无法获取有效会话")

        # 基础参数
        formdata = {
            "empi": self.empi,
            "domain": self.domain,
            "admitDate": self.admit_date,
            "payLoadType": self.payload_types,
            "type": self.doc_type,
            "pageNo": str(page_no)
        }

        # 根据类型添加特殊参数
        if self.doc_type == "payLoadType.JianYan":
            formdata.update({
                "searchType": "0"  # 0-所有检验 1-最近一周
            })
        elif self.doc_type == "payLoadType.JianCha":
            formdata.update({
                "id": self.visit_flow_id,
                "jcSearchType": "1"  # 固定为1(本次检查)
            })
        else:
            # 其他类型添加visit_flow_id
            formdata["id"] = self.visit_flow_id

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "*/*",
            "Connection": "keep-alive",
        }

        request = FormRequest(
            url=self.base_url,
            method='POST',
            formdata=formdata,
            cookies=session['cookies'],
            headers=headers,
            callback=self.parse_page,
            meta={'page_no': page_no}
        )
        
        yield request

    def parse_page(self, response):
        print("#####",response)
        try:
            data = json.loads(response.text)
            
            # 检查响应状态码和数据有效性
            if response.status != 200 or data.get("code") != 200:
                raise ValueError(f"Invalid response status: {response.status}, code: {data.get('code')}")
            
            # 检查分页信息
            if 'data' not in data or 'page' not in data['data'] or 'totalPage' not in data['data']['page']:
                raise ValueError("Invalid response: missing pagination data")
            self.total_pages = data['data']['page']['totalPage']
            
            # 检查并收集当前页文档
            if "data" in data and "list" in data["data"] and len(data["data"]["list"]) > 0:
                if "documentList" in data["data"]["list"][0]:
                    self.all_documents.extend(data["data"]["list"][0]["documentList"])
                else:
                    self.logger.warning(f"No documentList found in page {response.meta['page_no']}")
            else:
                self.logger.warning(f"No valid data found in page {response.meta['page_no']}")
            
            # 递归请求下一页
            self.current_page += 1
            if self.current_page < self.total_pages: # 必须是小于，不可以是等于
                yield from self.start_requests(page_no=self.current_page)
            else:
                # 所有页收集完成，处理数据
                self.logger.info(f"Total pages processed: {self.total_pages}")
                self.logger.info(f"Total documents collected: {len(self.all_documents) if self.all_documents else 0}")
                
                if self.all_documents:  # 确保有文档才处理
                    result = self.process_all_documents()
                    if result is None:
                        self.logger.error("process_all_documents returned None")
                        return
                    yield from result
                else:
                    self.logger.warning("No documents collected from all pages")
                
        except Exception as e:
            self.logger.error(f"Failed to parse page {response.meta['page_no']}: {str(e)}")
            raise

    def process_all_documents(self):
        self.logger.info("Starting to process all documents")
        processed_count = 0
        try:
            for doc in self.all_documents:
                try:
                    # 注意主键是documentuniqueid(小写)
                    doc_id = doc["documentuniqueid"]
                    
                    db_session = self.Session()

                    # 检查文档是否已存在
                    existing_doc = db_session.query(MedicalDocument).filter_by(
                        document_id=doc_id
                    ).first()
                    
                    if existing_doc:
                        # 更新现有文档
                        existing_doc.visit_flow_id = doc.get("visitFlowId")
                        existing_doc.empi = self.empi
                        existing_doc.file_path = doc.get("filepath")
                        existing_doc.payload_type = doc["payLoadType"]
                        existing_doc.document_metadata = doc  # 直接存储整个文档对象
                        existing_doc.document_content = None  # 留空content字段
                        existing_doc.status = "success"
                        existing_doc.updated_at = datetime.now()
                    else:
                        # 创建新文档
                        new_doc = MedicalDocument(
                            document_id=doc_id,
                            visit_flow_id=doc.get("visitFlowId"),
                            empi=self.empi,
                            file_path=doc.get("filepath"),
                            payload_type=doc["payLoadType"],
                            document_metadata=doc,  # 直接存储整个文档对象
                            document_content=None,  # 留空content字段
                            status="success"
                        )
                        db_session.add(new_doc)
                    
                    db_session.commit()
                    
                except Exception as e:
                    db_session.rollback()
                    self.logger.error(f"Failed to process document {doc_id}: {str(e)}")
            processed_count += 1
            if processed_count % 10 == 0:  # 每处理10个文档记录一次
                self.logger.info(f"Processed {processed_count}/{len(self.all_documents)} documents")
                
        finally:
            if 'db_session' in locals():
                db_session.close()
            self.logger.info(f"Finished processing {processed_count} documents")
            return []  # 返回空列表避免NoneType错误
