import os
import json
import scrapy
from datetime import datetime
from scrapy.http import FormRequest
from crawler.models import MedicalDocument, VisitRecord
from .login_handler import LoginHandler
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import insert
from dotenv import load_dotenv


class MedicalDocumentSpider(scrapy.Spider):
    name = "medical-document-spider"
    
    # 需要执行时间范围筛选的文档类型列表
    # 只有这些类型的文档会进行就诊时间范围检查
    NEEDS_TIME_FILTER_TYPES = ['payLoadType.JianYan']
    
    def __init__(self, empi=None, user_id=None, dept_id=None, domain=None, admit_date=None, discharge_date=None, payload_types=None, 
                 visit_flow_id=None, doc_type=None, strict_date_check=True, **kwargs):
        super().__init__(**kwargs)
        required_params = {
            'user_id': user_id,
            'dept_id': dept_id,
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
        self.user_id = user_id
        self.dept_id = dept_id
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


    def start_requests(self, page_no=0, cookies=None):
        if cookies is None:
            session = self.login_handler.get_ccd_session(self.user_id, self.dept_id)
            if not session:
                raise ValueError("无法获取有效 CCD 会话")
            cookies = session['cookies']

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
                "jcSearchType": "0"       #0 表示本次，1表示所有
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
            cookies = cookies,
            meta={'page_no': page_no, 'cookiejar': 1, 'handle_httpstatus_list': [200, 302]},
            dont_filter=True,
            headers=headers,
            callback=self.parse_page,
        )

    def parse_page(self, response):
        # —— 会话过期检测 ——  
        if self.login_handler.is_ccd_expired_response(response):
            self.logger.warning("检测到 CCD 会话已过期，正在重建并重试本页…")
            # 1. 重建 CCD 会话，拿到新的 cookies
            new_session = self.login_handler.mark_ccd_invalid(self.user_id, self.dept_id)
            # 2. 更新 spider 内部 cookie 存储（可选）
            #    这样 start_requests() 里拿到的 session 就是新的
            #    或者直接在 start_requests 中每次都重新取 session
            # 3. 重新发起本页请求
            yield from self.start_requests(page_no=response.meta['page_no'],cookies=new_session['cookies'])
            return

        try:
            data = json.loads(response.text)
            
            if response.status != 200 or data.get("code") != 200:
                raise ValueError(f"Invalid response status: {response.status}, code: {data.get('code')}")
            
            page_info = data["data"].get("page", {})
            self.total_pages = page_info.get("totalPage", 0)

            # 收集所有entry的documentList
            entries = data["data"].get("list") or []
            for entry in entries:
                docs = entry.get("documentList")
                if docs:
                    self.all_documents.extend(docs)
                else:
                    self.logger.warning(f"页 {response.meta['page_no']} 某 entry 无 documentList")
            
            self.current_page += 1
            if self.current_page < self.total_pages:
                yield from self.start_requests(page_no=self.current_page)
            else:
                # 全局去重
                seen = set()
                unique_docs = []
                for d in self.all_documents:
                    doc_id = d.get("documentuniqueid")
                    if doc_id and doc_id not in seen:
                        seen.add(doc_id)
                        unique_docs.append(d)
                removed = len(self.all_documents) - len(unique_docs)
                if removed:
                    self.logger.info(f"全局去重去掉 {removed} 份重复文档")
                self.all_documents = unique_docs

                self.logger.info(f"总页数: {self.total_pages}, 唯一文档数: {len(self.all_documents)}")
                if self.all_documents:
                    yield from self.process_all_documents()
                
        except Exception as e:
            self.logger.error(f"Failed to parse page {response.meta['page_no']}: {str(e)}")
            self.logger.error(f"Raw request is {response.text}")
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

    def should_filter_document(self, doc):
        """判断文档是否需要时间范围筛选"""
        # 根据初始化参数决定是否过滤
        return self.doc_type in self.NEEDS_TIME_FILTER_TYPES

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
            # 0. 过滤文档 (只有NEEDS_TIME_FILTER_TYPES中的类型会检查时间范围)
            original_count = len(self.all_documents)
            self.all_documents = [
                doc for doc in self.all_documents
                if not self.should_filter_document(doc) or 
                   self.is_document_in_visit(doc)
            ]
            filtered_count = original_count - len(self.all_documents)
            if filtered_count > 0:
                self.logger.info(f"过滤掉{filtered_count}份不在就诊期间的文档")
                
            # 1. 预取VisitRecord映射
            # 调试日志：记录visitFlowId分布
            from collections import Counter
            flow_id_stats = Counter(d.get('visitFlowId') for d in self.all_documents)
            self.logger.debug(f"文档visitFlowId统计: {flow_id_stats}")
            
            # 过滤无效visitFlowId并清理格式
            valid_docs = [d for d in self.all_documents if d.get('visitFlowId')]
            flow_ids = {d["visitFlowId"].strip() for d in valid_docs}
            
            # 分批查询避免IN子句过长
            batch_size = 100
            mapping = []
            flow_ids_list = list(flow_ids)
            for i in range(0, len(flow_ids_list), batch_size):
                batch = flow_ids_list[i:i+batch_size]
                mapping.extend(
                    session.query(VisitRecord.visit_flow_id, VisitRecord.id)
                          .filter(VisitRecord.visit_flow_id.in_(batch))
                          .all()
                )
            flowid_to_recordid = {fid: recid for fid, recid in mapping}
            self.logger.debug(f"成功映射{len(flowid_to_recordid)}个visitFlowId")

            # 2. 批量upsert文档
            BATCH_SIZE = 50  # 文档较大，批次调小
            total_inserted = total_updated = 0
            
            for i in range(0, len(valid_docs), BATCH_SIZE):
                batch = valid_docs[i:i+BATCH_SIZE]
                doc_ids = [d["documentuniqueid"] for d in batch]
                
                # 查询已存在文档
                existing = {d[0] for d in session.query(MedicalDocument.document_id)
                           .filter(MedicalDocument.document_id.in_(doc_ids)).all()}
                
                # 处理当前批次
                to_insert = []
                to_update = []
                for doc in batch:
                    doc_id = doc["documentuniqueid"]
                    visit_flow_id = doc["visitFlowId"].strip()
                    vrid = flowid_to_recordid.get(visit_flow_id)
                    
                    if vrid is None:
                        self.logger.warning(f"找不到visitFlowId对应的记录: {visit_flow_id}, 文档ID: {doc_id}")
                        continue
                        
                    doc_data = {
                        "document_id": doc_id,
                        "visit_record_id": vrid,
                        "visit_flow_id": doc["visitFlowId"],
                        "empi": self.empi,
                        "payload_type": doc["payLoadType"],
                        "doc_type": self.doc_type,
                        "document_metadata": doc,
                        "updated_at": datetime.now()
                    }
                    
                    if doc_id in existing:
                        # 获取主键id用于更新
                        doc_id_obj = session.query(MedicalDocument.id) \
                                          .filter_by(document_id=doc_id).first()
                        if doc_id_obj:
                            doc_data["id"] = doc_id_obj[0]
                            to_update.append(doc_data)
                    else:
                        doc_data["created_at"] = datetime.now()
                        to_insert.append(doc_data)
                
                # 执行批量操作
                try:
                    if to_insert:
                        # 使用ON CONFLICT DO NOTHING进行批量插入
                        stmt = insert(MedicalDocument).values(to_insert)
                        stmt = stmt.on_conflict_do_nothing(index_elements=['document_id'])
                        result = session.execute(stmt)
                        total_inserted += result.rowcount
                    if to_update:
                        session.bulk_update_mappings(MedicalDocument, to_update)
                        total_updated += len(to_update)
                    session.commit()
                    
                except Exception as e:
                    session.rollback()
                    self.logger.error(f"批量处理失败: {e}")
                    # 失败后改为逐条处理
                    for doc_data in to_insert + to_update:
                        try:
                            if "id" in doc_data:  # 更新
                                session.merge(MedicalDocument(**doc_data))
                            else:  # 插入
                                session.add(MedicalDocument(**doc_data))
                            session.commit()
                        except Exception as e:
                            self.logger.error(f"文档 {doc_data['document_id']} 处理失败: {e}")
                            session.rollback()

            self.logger.info(f"文档处理完成: 新增{total_inserted} 更新{total_updated}")
            return []  # 返回空列表避免TypeError

        except Exception as e:
            session.rollback()
            self.logger.exception("批量处理文档失败")
            raise
        finally:
            session.close()
