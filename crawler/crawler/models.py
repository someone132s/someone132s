from sqlalchemy import create_engine, Column, Integer, String, JSON, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timedelta

Base = declarative_base()

class SpiderSession(Base):
    __tablename__ = 'spider_sessions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), unique=True)
    cookies = Column(JSON)
    access_token = Column(String(255))
    user_code = Column(String(50))
    created_at = Column(DateTime, default=datetime.now)
    expires_at = Column(DateTime)

    def is_valid(self):
        return self.expires_at > datetime.now()
