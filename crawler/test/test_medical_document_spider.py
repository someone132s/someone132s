import os
import argparse
import subprocess
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from crawler.models import VisitRecord
from dotenv import load_dotenv

class TestMedicalDocumentSpider:
    """测试medical-document-spider的测试程序"""
    
    # 需要排除的文档类型
    EXCLUDE_TYPES = ["payLoadType.FrontPage"]
    
    def __init__(self, dryrun=False, clinic_type=None):
        load_dotenv()
        self.engine = create_engine(os.getenv('DATABASE_URI'))
        self.Session = sessionmaker(bind=self.engine)
        self.dryrun = dryrun
        self.clinic_type = clinic_type
        self.skipped = 0
        self.processed = 0

    def process_discharge_date(self, record):
        """处理discharge_date特殊值"""
        if not record.discharge_date:
            print("❌ 错误：discharge_date为空，跳过该记录")
            return None
        
        if str(record.discharge_date) == "00010101000000":
            current_time = datetime.now().strftime("%Y%m%d%H%M%S")
            print(f"⚠️ 患者在院，使用当前时间代替: {current_time}")
            return current_time
        
        return record.discharge_date.strftime("%Y%m%d%H%M%S")

    def build_spider_commands(self, record):
        """为每个type-value对构造爬虫命令"""
        if not record.payload_type_info:
            print("⚠️ 警告：payload_type_info为空")
            self.skipped += 1
            return []
            
        discharge_date = self.process_discharge_date(record)
        if discharge_date is None:
            self.skipped += 1
            return []
            
        commands = []
        for payload_item in record.payload_type_info:
            if payload_item["type"] in self.EXCLUDE_TYPES:
                continue
                
            if not payload_item.get("value"):
                print(f"⚠️ 警告：跳过空value的payload类型 {payload_item['type']}")
                continue
                
            cmd = [
                'scrapy', 'crawl', 'medical-document-spider',
                '-a', f'empi={record.empi}',
                '-a', f'domain={record.visit_flow_domain}',
                '-a', f'admit_date={record.admit_date.strftime("%Y%m%d%H%M%S")}',
                '-a', f'discharge_date={discharge_date}',
                '-a', f'visit_flow_id={record.visit_flow_id}',
                '-a', f'doc_type={payload_item["type"]}',
                '-a', f'payload_types={payload_item["value"]}'
            ]
            commands.append(cmd)
            
        if not commands:
            print("⚠️ 警告：无有效payload类型")
            self.skipped += 1
            
        return commands

    def get_total_count(self):
        """获取总记录数"""
        session = self.Session()
        try:
            return session.query(VisitRecord).count()
        finally:
            session.close()

    def fetch_batch(self, offset, limit):
        """批量获取记录"""
        session = self.Session()
        try:
            return session.query(VisitRecord)\
                   .order_by(VisitRecord.id)\
                   .offset(offset)\
                   .limit(limit)\
                   .all()
        finally:
            session.close()

    def fetch_valid_records(self, target_count, batch_size=20):
        """分批次获取有效记录"""
        if hasattr(self, 'visit_flow_id') and self.visit_flow_id:
            # 优先查询指定visit_flow_id的记录
            session = self.Session()
            try:
                record = session.query(VisitRecord)\
                       .filter_by(visit_flow_id=self.visit_flow_id)\
                       .first()
                if record and self.is_valid_record(record):
                    print(f"✅ 找到指定visit_flow_id的记录: {self.visit_flow_id}")
                    return [record]
                else:
                    print(f"❌ 未找到有效的visit_flow_id记录: {self.visit_flow_id}")
                    return []
            finally:
                session.close()
        else:
            # 原有批量查询逻辑
            valid_records = []
            total_count = self.get_total_count()
            print(f"ℹ️ 数据库共有{total_count}条记录，开始筛选...")

            for offset in range(0, total_count, batch_size):
                batch = self.fetch_batch(offset, batch_size)
                print(f"处理批次: {offset}-{offset+batch_size} ({len(batch)}条)")

                for record in batch:
                    if self.is_valid_record(record):
                        valid_records.append(record)
                        print(f"✅ 有效记录: {record.visit_flow_id}")
                        if len(valid_records) >= target_count:
                            return valid_records[:target_count]

            return valid_records

    def is_valid_record(self, record):
        """检查记录有效性"""
        if not all([record.empi, record.visit_flow_domain, record.admit_date]):
            print(f"❌ 无效记录{record.visit_flow_id}: 缺少必要字段")
            return False
            
        if not record.payload_type_info:
            print(f"❌ 无效记录{record.visit_flow_id}: payload_type_info为空")
            return False
            
        # 检查clinic_type是否符合要求
        if hasattr(self, 'clinic_type') and self.clinic_type:
            if record.clinic_type != self.clinic_type:
                print(f"❌ 无效记录{record.visit_flow_id}: clinic_type不匹配")
                return False
                
        valid_types = [t for t in record.payload_type_info 
                     if t["type"] not in self.EXCLUDE_TYPES]
        if not valid_types:
            print(f"❌ 无效记录{record.visit_flow_id}: 无有效payload类型")
            return False
            
        return True

    def run_tests(self, target_count=5):
        """主测试流程"""
        session = self.Session()
        try:
            valid_records = self.fetch_valid_records(target_count)
            print(f"\nℹ️ 找到{len(valid_records)}条有效记录，开始测试...")
            
            for record in valid_records:
                commands = self.build_spider_commands(record)
                if not commands:
                    continue
                    
                for cmd in commands:
                    # 总是输出构造的命令
                    print("✅ 构造的爬虫命令:")
                    print(" \\\n  ".join(cmd))
                    
                    if not self.dryrun:
                        # 实际执行模式
                        doc_type = next((arg for arg in cmd if arg.startswith('-a doc_type=')), None)
                        if doc_type:
                            doc_type = doc_type.split('=')[1]
                            print(f"🚀 执行爬虫(doc_type={doc_type})...")
                        else:
                            print("🚀 执行爬虫(未知doc_type)...")
                        subprocess.run(cmd, cwd='crawler')
                        self.processed += 1
                    
            print(f"\n📊 测试结果: 处理{self.processed}条, 跳过{self.skipped}条")
            
        finally:
            session.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='测试medical-document爬虫')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-l', '--limit', type=int, default=5,
                     help='需要的有效记录数量，默认5条')
    group.add_argument('--visit-flow-id', type=str,
                     help='指定要测试的visit_flow_id')
    parser.add_argument('--batch-size', type=int, default=20,
                     help='每批次查询数量，默认20条')
    parser.add_argument('--dryrun', action='store_true',
                     help='空跑模式，只输出命令不执行')
    parser.add_argument('--clinic-type', type=str,
                     help='指定clinic_type筛选条件')
    args = parser.parse_args()

    tester = TestMedicalDocumentSpider(dryrun=args.dryrun, clinic_type=args.clinic_type)
    if args.visit_flow_id:
        # 添加visit_flow_id属性
        tester.visit_flow_id = args.visit_flow_id
        tester.run_tests(target_count=1)  # 指定visit_flow_id时只处理1条记录
    else:
        tester.run_tests(target_count=args.limit)
