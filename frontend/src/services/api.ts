import axios from "axios";
import type { Patient, PatientCreate, MedicalRecord, MedicalRecordCreate } from "@/types/patient";

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
});

export default {
  // 患者管理API
  getPatients(skip: number = 0, limit: number = 100) {
    return apiClient.get<Patient[]>("/patients", { params: { skip, limit } });
  },

  getPatient(id: number) {
    return apiClient.get<Patient>(`/patients/${id}`);
  },

  createPatient(patient: PatientCreate) {
    return apiClient.post<Patient>("/patients", patient);
  },

  // 病历管理API
  getPatientRecords(patientId: number) {
    return apiClient.get<MedicalRecord[]>(`/patients/${patientId}/records`);
  },

  createMedicalRecord(patientId: number, record: MedicalRecordCreate) {
    return apiClient.post<MedicalRecord>(
      `/patients/${patientId}/records`,
      record
    );
  },
};
