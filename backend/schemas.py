from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class PatientBase(BaseModel):
    name: str
    gender: Optional[str] = None
    age: Optional[int] = None

class PatientCreate(PatientBase):
    pass

class PatientUpdate(PatientBase):
    pass

class Patient(PatientBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class MedicalRecordBase(BaseModel):
    diagnosis: Optional[str] = None
    treatment: Optional[str] = None
    notes: Optional[str] = None

class MedicalRecordCreate(MedicalRecordBase):
    patient_id: int

class MedicalRecordUpdate(MedicalRecordBase):
    pass

class MedicalRecord(MedicalRecordBase):
    id: int
    patient_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class PatientWithRecords(Patient):
    records: List[MedicalRecord] = []
