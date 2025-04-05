from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from .models import Base
from .settings import DATABASE_URI

class DatabaseInitializer:
    print(DATABASE_URI)
    print(Base)
    def __init__(self):
        self.engine = create_engine(DATABASE_URI)
        self.Session = sessionmaker(bind=self.engine)

    def init_db(self, force=False):
        """Initialize database tables"""
        if force:
            Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        return True

    def check_db(self):
        """Check if spider_sessions table exists"""
        inspector = inspect(self.engine)
        return 'spider_sessions' in inspector.get_table_names()

    def get_session(self):
        """Get a new database session"""
        return self.Session()

db_initializer = DatabaseInitializer()
