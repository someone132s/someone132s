from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta

Base = declarative_base()

class SpiderSession(Base):
    __tablename__ = 'spider_sessions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50))  # 移除unique
    dept_id = Column(String(100), default="default")  # 新增
    cookies = Column(JSONB)
    access_token = Column(String(255))
    user_code = Column(String(50))
    created_at = Column(DateTime, default=datetime.now)
    expires_at = Column(DateTime)

    # 新增复合唯一约束
    __table_args__ = (
        UniqueConstraint('user_id', 'dept_id', name='uq_user_dept'),
    )

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
    
    id = Column(Integer, primary_key=True)
    empi = Column(String(50), unique=True, nullable=False)
    patient_name = Column(String(100), nullable=False)
    patient_no = Column(String(50), nullable=False)
    patient_type = Column(String(10), nullable=False)  # I/O
    dept_code = Column(String(100), index=True)
    raw_data = Column(JSONB)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, onupdate=datetime.now)
    
    visits = relationship("VisitRecord", back_populates="patient")

class VisitRecord(Base):
    __tablename__ = 'visit_records'
    
    id = Column(Integer, primary_key=True)
    visit_flow_id = Column(String(100), unique=True, nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey('patients.id', ondelete='CASCADE'), 
                     nullable=False, index=True)
    empi = Column(String(50), nullable=False)  # 保留作为冗余字段
    admit_date = Column(DateTime)
    discharge_date = Column(DateTime)
    dept_code = Column(String(100))  # 科室代码
    dept_name = Column(String(100))  # 科室名称
    pat_cur_dep = Column(String(50))  # 科室护士站代号
    clinic_type = Column(String(20))  # 门诊/住院
    visit_flow_domain = Column(String(100))
    timeline_raw_data = Column(JSONB)
    payload_type_info = Column(JSONB)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, onupdate=datetime.now)
    
    patient = relationship("Patient", back_populates="visits")
    documents = relationship("MedicalDocument", back_populates="visit")

    def __repr__(self):
        return f"<VisitRecord(flow_id={self.visit_flow_id}, dept={self.dept_name}, date={self.admit_date})>"

class MedicalDocument(Base):
    __tablename__ = 'medical_documents'

    # 主键和外键
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(100), unique=True, nullable=False, index=True)
    visit_record_id = Column(Integer, ForeignKey('visit_records.id', ondelete='CASCADE'),
                          nullable=False, index=True)
    
    # 冗余字段
    visit_flow_id = Column(String(100), nullable=True)
    empi = Column(String(50), nullable=True)

    # 文档内容
    doc_type = Column(String(50), nullable=False)
    payload_type = Column(String(50))
    document_metadata = Column(JSONB)
    document_content = Column(JSONB)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, onupdate=datetime.now)

    # 关联关系
    visit = relationship("VisitRecord", back_populates="documents")

    def __repr__(self):
        return f"<MedicalDocument(id={self.document_id}, type={self.payload_type})>"
