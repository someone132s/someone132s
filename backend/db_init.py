from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

SQLALCHEMY_DATABASE_URL = "sqlite:///./medical.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Patient(Base):
    __tablename__ = "patients"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50))
    gender = Column(String(10))
    age = Column(Integer)
    admission_date = Column(DateTime, default=datetime.now)
    diagnosis = Column(String(200))
    treatment = Column(String(200))

def init_db():
    Base.metadata.create_all(bind=engine)
    print("数据库初始化完成")

if __name__ == "__main__":
    init_db()
