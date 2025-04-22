import os
import time
import subprocess
import argparse
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from crawler.models import VisitRecord
from dotenv import load_dotenv

class TestCrawler:
    def __init__(self, force_update=False):
        load_dotenv()
        self.engine = create_engine(os.getenv('DATABASE_URI'))
        self.Session = sessionmaker(bind=self.engine)
        
        self.force_update = force_update

    def get_test_records(self, limit=5):
        """从数据库获取指定数量的测试记录"""
        session = self.Session()
        try:
            if self.force_update:
                # 强制更新模式下获取所有记录
                records = session.query(VisitRecord)\
                    .order_by(VisitRecord.updated_at.asc())\
                    .limit(limit)\
                    .all()
            else:
                # 普通模式下只获取未更新的记录
                cutoff_date = datetime.now() - timedelta(days=1)
                records = session.query(VisitRecord)\
                    .filter(VisitRecord.updated_at < cutoff_date)\
                    .limit(limit)\
                    .all()
            return records
        finally:
            session.close()

    def run_spider_for_record(self, record):
        """为单条记录运行爬虫"""
        cmd = [
            'scrapy', 'crawl', 'visit-items-spider',
            '-a', f'empi={record.empi}',
            '-a', f'admit_date={record.admit_date.strftime("%Y-%m-%d")}',
            '-a', f'domain={record.visit_flow_domain}',
            '-a', f'visit_id={record.visit_flow_id}',
            '-a', f'force_updatedb={str(self.force_update).lower()}'
        ]
        process = subprocess.Popen(cmd, cwd='crawler')
        return process.wait()

    def test_and_verify(self, limit=5):
        """测试主流程"""
        records = self.get_test_records(limit)
        if not records:
            print("没有找到需要更新的记录")
            return

        print(f"找到 {len(records)} 条需要更新的记录")
        for i, record in enumerate(records, 1):
            print(f"正在处理第 {i} 条记录 (ID: {record.visit_flow_id})")
            retcode = self.run_spider_for_record(record)
            if retcode == 0:
                print(f"记录 {record.visit_flow_id} 更新成功")
            else:
                print(f"记录 {record.visit_flow_id} 更新失败")

            time.sleep(3)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='测试visit-items爬虫')
    parser.add_argument('-l', '--limit', type=int, default=5, 
                       help='要测试的记录数量，默认5条')
    parser.add_argument('-f', '--force', action='store_true',
                       help='是否强制更新所有记录')
    args = parser.parse_args()

    tester = TestCrawler(force_update=args.force)
    tester.test_and_verify(limit=args.limit)
