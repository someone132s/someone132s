export interface Patient {
  id: number
  name: string
  gender: string
  age: number
  phone?: string
  address?: string
  medicalHistory?: string
  allergies?: string[]
  createdAt?: Date
  updatedAt?: Date
}

export interface PatientDetail extends Patient {
  bloodType?: string
  height?: number
  weight?: number
  diagnosis?: string[]
  treatments?: string[]
  notes?: string
}
