import os
import json
import re
import scrapy
from urllib.parse import urlencode
from datetime import datetime
from crawler.models import MedicalDocument
from .login_handler import LoginHandler
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv


class MDContentSpider(scrapy.Spider):
    name = "md-content-spider"
    
    VOID_VALUE = "void"  # 直接存储为字符串，不带引号
    
    def __init__(self, document_unique_id=None, filepath=None, doc_type=None, payload_type=None,
                 fileSystemFk=1, dicomNum='', reportStatus='', modality='',
                 dicomStudyTime='', name='', external_document_unique_id=None, *args, **kwargs):
        super(MDContentSpider, self).__init__(*args, **kwargs)
        if not all([doc_type, payload_type]) or filepath is None:
            raise ValueError("必须提供doc_type和payload_type参数，filepath可为void")
            
        self.document_unique_id = document_unique_id
        self.filepath = filepath
        self.doc_type = doc_type  # 文档类型(如payLoadType.JianCha)
        self.payload_type = payload_type  # 响应数据类型
        self.fileSystemFk = fileSystemFk
        self.dicomNum = dicomNum
        self.reportStatus = reportStatus
        self.modality = modality
        self.dicomStudyTime = dicomStudyTime
        self.name = name
        self.external_document_unique_id = external_document_unique_id

        load_dotenv()
        self.engine = create_engine(os.getenv('DATABASE_URI'))
        self.Session = sessionmaker(bind=self.engine)
        self.login_handler = LoginHandler()
        
        # 初始化URL配置
        self.showinfo_url = os.getenv('DOCUMENT_SHOWINFO_URL')
        self.showinfo_plt_url = os.getenv('DOCUMENT_SHOWINFO_PLT_URL')

    def start_requests(self):
        """构造并提交GET请求获取文档内容"""
        if self.filepath == self.VOID_VALUE:
            self.logger.info(f"文档{self.document_unique_id}标记为void，跳过爬取并写入数据库")
            # 把 void 包装成 JSON 数组 ["void"]，直接写入数据库
            self._save_document_content([self.VOID_VALUE])
            # 仍然产出一个item，方便pipeline或日志记录
            yield {
                'document_unique_id': self.document_unique_id,
                'content': [self.VOID_VALUE]
            }
            return
            
        session = self.login_handler.get_session()
        if not session:
            raise ValueError("无法获取有效会话")

        # 根据文档类型(doc_type)构造不同请求
        if self.doc_type in ['payLoadType.JianCha', 'payLoadType.JianYan']:
            # showinfo类型 - 参数直接放在查询字符串中
            url = self.showinfo_url
            # 构造请求参数，过滤空值(None/空字符串)
            # 注意：服务器要求空参数必须完全省略，不能传None或空字符串
            # 构造原始参数，保留None值用于后续统一处理
            params = {
                'documentuniqueid': str(self.external_document_unique_id or self.document_unique_id),
                'filepath': self.filepath,
                'fileSystemFk': str(self.fileSystemFk),
                'dicomNum': self.dicomNum,  # 保留原始值
                'reportStatus': self.reportStatus,
                'modality': self.modality,
                'dicomStudyTime': self.dicomStudyTime,
                'name': self.name,
                'payLoadType': self.payload_type,
                'checkType': self.doc_type.split('.')[1],
                'document_unique_id': str(self.external_document_unique_id or self.document_unique_id)
            }
            # 统一处理None和字符串"None"，确保urlencode生成key=形式
            params = {
                k: "" 
                if v is None or (isinstance(v, str) and v.lower() == "none")
                else str(v)
                for k, v in params.items()
            }
        else:
            # showinfo/plt类型 - 参数封装在JSON对象中
            url = self.showinfo_plt_url
            # 构造JSON参数，过滤空值(None/空字符串)
            # 注意：服务器要求空参数必须完全省略，不能传None或空字符串
            # 构造原始JSON参数，保留None值用于后续统一处理
            json_data = {
                'documentuniqueid': self.external_document_unique_id or self.document_unique_id,
                'filepath': self.filepath,
                'fileSystemFk': self.fileSystemFk,
                'dicomNum': self.dicomNum,
                'reportStatus': self.reportStatus,
                'modality': self.modality,
                'dicomStudyTime': self.dicomStudyTime,
                'name': self.name,
                'nodes': ["//ClinicalDocument"],
                'parseModel': "0",
                'imageNode': ''
            }
            # 统一处理None和字符串"None"，确保JSON中不出现null或"None"
            json_data = {
                k: ""
                if v is None or (isinstance(v, str) and v.lower() == "none")
                else v
                for k, v in json_data.items()
            }
            params = {
                'documentVO_2_paramData': json.dumps(json_data)
            }

        headers = {
            "Accept": "application/json",
        }

        # 构造GET请求URL
        query_string = urlencode(params)
        request_url = f"{url}?{query_string}"
        
        request = scrapy.Request(
            url=request_url,
            method='GET',
            cookies=session['cookies'],
            headers=headers,
            callback=self.parse_response
        )
        yield request

    def parse_response(self, response):
        """解析API响应并保存文档内容到数据库"""
        #print("#####",response.text)
        if response.status != 200:
            self.logger.error(f"请求失败，状态码: {response.status}")
            raise ValueError(f"无效响应状态码: {response.status}")

        try:
            data = json.loads(response.text)
            if data.get('code') != 200:
                raise ValueError(f"API返回错误: {data.get('errmsg')}")
                
            # 根据请求文档类型(doc_type)处理不同格式数据
            if self.doc_type in ['payLoadType.JianCha', 'payLoadType.JianYan']:  # 示例值，根据实际情况调整
                content = data.get('data', {})
            else:
                content = self._process_plt_response(data)
            
            self._save_document_content(content)
                
            yield {
                'document_unique_id': self.document_unique_id,
                'content': content
            }
            
        except Exception as e:
            self.logger.error(f"解析响应失败: {str(e)}")
            raise

    def _save_document_content(self, content):
        """保存文档内容到数据库"""
        db_session = self.Session()
        try:
            document = db_session.query(MedicalDocument)\
                .filter_by(document_id=self.document_unique_id)\
                .first()
                
            if document:
                document.document_content = content
                document.last_updated = datetime.now()
                db_session.commit()
                self.logger.info(f"成功更新文档 {self.document_unique_id}")
            else:
                self.logger.warning(f"未找到文档记录 {self.document_unique_id}，无法更新")
                
        except Exception as e:
            db_session.rollback()
            self.logger.error(f"数据库更新失败: {str(e)}")
            raise
        finally:
            db_session.close()

    def _process_plt_response(self, data):
        """处理plt类型的响应数据"""
        content_list = data.get('data', {}).get('nameValueMap', {}).get('contentList', [])
        for item in content_list:
            if 'text' in item:
                # 移除image标签
                item['text'] = re.sub(r'<image>.*?</image>', 'temp_removed', item['text'])
        return content_list
