from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
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
    dept_code = Column(String(100))
    raw_data = Column(JSONB)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, onupdate=datetime.now)
    
    visits = relationship("VisitRecord", back_populates="patient")

class VisitRecord(Base):
    __tablename__ = 'visit_records'
    
    visit_flow_id = Column(String(100), primary_key=True)
    empi = Column(String(50), ForeignKey('patients.empi'))
    admit_date = Column(DateTime)
    dept_code = Column(String(100))  # 科室代码
    dept_name = Column(String(100))  # 科室名称
    pat_cur_dep = Column(String(50))  # 科室护士站代号
    clinic_type = Column(String(20))  # 门诊/住院
    visit_flow_domain = Column(String(100))
    timeline_raw_data = Column(JSONB)  # 原raw_data重命名
    payload_type_info = Column(JSONB)  # 存储payLoadTypeList完整结构
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, onupdate=datetime.now)
    
    patient = relationship("Patient", back_populates="visits")

    def __repr__(self):
        return f"<VisitRecord(flow_id={self.visit_flow_id}, dept={self.dept_name}, date={self.admit_date})>"
