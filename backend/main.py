from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
from . import models, schemas
from .database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="医疗助手API", version="1.0.0")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据库依赖
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", tags=["Root"])
async def root():
    return {"message": "医疗助手API服务"}

# 患者管理API
@app.get("/api/v1/patients", response_model=List[schemas.Patient])
def get_patients(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Patient).offset(skip).limit(limit).all()

@app.post("/api/v1/patients", response_model=schemas.Patient)
def create_patient(patient: schemas.PatientCreate, db: Session = Depends(get_db)):
    db_patient = models.Patient(**patient.dict())
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return db_patient

@app.get("/api/v1/patients/{patient_id}", response_model=schemas.PatientWithRecords)
def get_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="患者不存在")
    return patient

# 病历管理API
@app.get("/api/v1/patients/{patient_id}/records", response_model=List[schemas.MedicalRecord])
def get_patient_records(patient_id: int, db: Session = Depends(get_db)):
    return db.query(models.MedicalRecord).filter(models.MedicalRecord.patient_id == patient_id).all()

@app.post("/api/v1/patients/{patient_id}/records", response_model=schemas.MedicalRecord)
def create_medical_record(
    patient_id: int, 
    record: schemas.MedicalRecordCreate, 
    db: Session = Depends(get_db)
):
    db_record = models.MedicalRecord(**record.dict(), patient_id=patient_id)
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    return db_record

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
