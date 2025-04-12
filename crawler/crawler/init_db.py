from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from .models import Base
from .settings import DATABASE_URI
import logging

logger = logging.getLogger(__name__)

class DatabaseInitializer:
    def __init__(self):
        self.engine = create_engine(DATABASE_URI)
        self.Session = sessionmaker(bind=self.engine)
        self.inspector = inspect(self.engine)

    def init_db(self, force=False):
        """Initialize database tables with incremental updates"""
        if force:
            logger.info("强制重建所有数据库表")
            Base.metadata.drop_all(self.engine)
            Base.metadata.create_all(self.engine)
            return True
        
        # 检查表是否存在
        existing_tables = set(self.inspector.get_table_names())
        required_tables = set(Base.metadata.tables.keys())
        
        # 创建缺失的表
        tables_to_create = required_tables - existing_tables
        if tables_to_create:
            logger.info(f"创建缺失的表: {', '.join(tables_to_create)}")
            Base.metadata.create_all(self.engine, tables=[
                Base.metadata.tables[table] for table in tables_to_create
            ])
        
        # 检查并更新现有表的列
        for table_name in existing_tables & required_tables:
            self._update_table_columns(table_name)
        
        return True

    def _update_table_columns(self, table_name):
        """检查并更新表的列定义"""
        table = Base.metadata.tables[table_name]
        existing_columns = {c['name'] for c in self.inspector.get_columns(table_name)}
        model_columns = {c.name for c in table.columns}
        
        # 找出需要添加的列
        columns_to_add = model_columns - existing_columns
        if not columns_to_add:
            return
            
        logger.info(f"表 {table_name} 需要添加列: {', '.join(columns_to_add)}")
        with self.engine.begin() as conn:
            for column_name in columns_to_add:
                column = table.columns[column_name]
                conn.execute(text(
                    f"ALTER TABLE {table_name} ADD COLUMN {column.name} {column.type}"
                ))

    def check_db(self):
        """检查数据库表是否存在"""
        existing_tables = set(self.inspector.get_table_names())
        required_tables = set(Base.metadata.tables.keys())
        return existing_tables.issuperset(required_tables)

    def get_session(self):
        """获取新的数据库会话"""
        return self.Session()

db_initializer = DatabaseInitializer()
