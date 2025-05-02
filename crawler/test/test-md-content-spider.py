import os
import json
import subprocess
from argparse import ArgumentParser
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from crawler.models import MedicalDocument, Base

load_dotenv()

class MDContentTester:
    def __init__(self, minimal=False, dryrun=False):
        """
        初始化测试器
        :param minimal: 是否使用最小参数模式(默认False)
        :param dryrun: 是否只打印命令不执行(默认False)
        """
        self.minimal = minimal
        self.dryrun = dryrun
        self.engine = create_engine(os.getenv('DATABASE_URI'))
        self.Session = sessionmaker(bind=self.engine)

    def get_test_document(self, document_id):
        """根据document_id获取特定文档记录"""
        session = self.Session()
        try:
            document = session.query(MedicalDocument)\
                .filter(MedicalDocument.document_id == document_id)\
                .filter(MedicalDocument.document_metadata != None)\
                .first()
            if not document:
                raise ValueError(f"未找到document_id={document_id}的有效记录")
            return document
        finally:
            session.close()

    def extract_params(self, document):
        """
        从document_metadata提取参数
        :return: 参数字典
        """
        metadata = document.document_metadata
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        
        # 基础参数
        doc_type = document.doc_type
        is_jiancha = doc_type in ['payLoadType.JianCha', 'payLoadType.JianYan']
        
        # 获取dicomStudyTime原始值
        dicom_study_time = metadata.get('dicomStudyTime', '')
            
        # 必须参数
        required_params = {
            'user_id': '224G',
            #直接写死
            'dept_id': 'f8d9a5d128b3586433c3efea570e65e7',
            #直接写死
            'document_unique_id': document.document_id,
            'doc_type': document.doc_type,
            'filepath': metadata.get('filepath', 'void'),
            'fileSystemFk': str(metadata.get('fileSystemFk', '1')),
            'payload_type': metadata.get('payLoadType', '')
        }
        
        # 可选参数
        optional_params = {}
        if not self.minimal:
            # 检验检查类特有参数
            if is_jiancha:
                check_type = doc_type.split('.')[1] if '.' in doc_type else ''
                optional_params['checkType'] = check_type
                
            optional_params.update({
                'dicomNum': str(metadata.get('dicomNum', '')),
                'reportStatus': str(metadata.get('reportStatus', '')),
                'modality': str(metadata.get('modality', '')),
                'dicomStudyTime': dicom_study_time,
                'name': metadata.get('patientName', ''),
                'external_document_unique_id': metadata.get('documentUniqueId', ''),
                'document_unique_id': document.document_id
            })
            
        # 合并参数
        params = {**required_params, **optional_params}
        return {k: v for k, v in params.items() if v is not None and v != ''}

    def build_command(self, params):
        """构建scrapy命令"""
        args = ' '.join([f'-a {k}="{v}"' for k, v in params.items()])
        return f'scrapy crawl md-content-spider {args}'

    def run_test(self, document_id):
        """执行指定文档的测试"""
        try:
            doc = self.get_test_document(document_id)
            params = self.extract_params(doc)
            cmd = self.build_command(params)
            
            print(f"\n测试文档 {document_id}:")
            print("参数:", json.dumps(params, indent=2, ensure_ascii=False))
            
            if self.dryrun:
                print("[DRYRUN]", cmd)
            else:
                print("执行命令:", cmd)
                try:
                    subprocess.run(cmd, shell=True, check=True)
                except subprocess.CalledProcessError as e:
                    print(f"执行失败: {e}")
        except ValueError as e:
            print(f"错误: {e}")

if __name__ == '__main__':
    parser = ArgumentParser(description='MDContentSpider测试工具')
    parser.add_argument('--document_id', required=True, help='要测试的文档ID')
    parser.add_argument('--minimal', action='store_true', help='使用最小参数模式')
    parser.add_argument('--dryrun', action='store_true', help='只打印命令不执行')
    args = parser.parse_args()

    tester = MDContentTester(minimal=args.minimal, dryrun=args.dryrun)
    tester.run_test(args.document_id)
