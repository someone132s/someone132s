from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime, timedelta

Base = declarative_base()

class SpiderSession(Base):
    __tablename__ = 'spider_sessions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), unique=True)
    cookies = Column(JSONB)
    access_token = Column(String(255))
    user_code = Column(String(50))
    created_at = Column(DateTime, default=datetime.now)
    expires_at = Column(DateTime)

    def is_valid(self):
        return self.expires_at > datetime.now()

class UserInfo(Base):
    __tablename__ = 'user_infos'
    
    login_name = Column(String(50), primary_key=True)
    user_code = Column(String(50))
    raw_data = Column(JSONB)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, onupdate=datetime.now)

class Department(Base):
    __tablename__ = 'departments'
    
    dept_code = Column(String(100), primary_key=True)
    dept_name = Column(String(100))
    raw_data = Column(JSONB)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, onupdate=datetime.now)

class Patient(Base):
    __tablename__ = 'patients'
    
    empi = Column(String(50), primary_key=True)
    patient_name = Column(String(100))
    patient_no = Column(String(50))
    patient_type = Column(String(10))  # I/O
    dept_code = Column(String(100), ForeignKey('departments.dept_code'))
    raw_data = Column(JSONB)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, onupdate=datetime.now)
