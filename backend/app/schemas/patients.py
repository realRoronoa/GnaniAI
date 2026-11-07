from datetime import date, datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class PatientCreate(BaseModel):
    full_name: str = Field(..., max_length=255)
    gender: str = Field(..., max_length=20)
    mobile_number: str = Field(..., max_length=30)
    email: EmailStr | None = None
    date_of_birth: date | None = None
    age_years: int | None = Field(default=None, ge=0, le=130)
    preferred_language: str = Field(default="en-IN", max_length=20)
    patient_identifier: str | None = Field(default=None, max_length=100)
    allergies_summary: str | None = None
    allergy_verification_status: str = Field(default="UNVERIFIED", max_length=50)
    administrative_notes: str | None = None


class PatientUpdate(BaseModel):
    full_name: str | None = None
    gender: str | None = None
    mobile_number: str | None = None
    email: EmailStr | None = None
    date_of_birth: date | None = None
    age_years: int | None = None
    preferred_language: str | None = None
    allergies_summary: str | None = None
    allergy_verification_status: str | None = None
    administrative_notes: str | None = None


class PatientResponse(BaseModel):
    id: UUID
    organization_id: UUID
    patient_identifier: str
    full_name: str
    date_of_birth: date | None
    age_years: int | None
    gender: str
    mobile_number: str
    email: str | None
    preferred_language: str
    allergies_summary: str | None
    allergy_verification_status: str
    administrative_notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DuplicateMatchSummary(BaseModel):
    id: UUID
    patient_identifier: str
    full_name: str
    gender: str
    age_years: int | None
    mobile_number: str
    match_reasons: list[str]


class DuplicateCheckResponse(BaseModel):
    has_matches: bool
    potential_matches: list[DuplicateMatchSummary]
    recommendation: str


class HistoricalMedicationItem(BaseModel):
    id: UUID
    consultation_id: UUID
    consultation_date: datetime
    medication_name: str
    dosage: str | None
    frequency: str | None
    duration: str | None
    route: str
    is_historical: bool = True
    special_instructions: str | None


class PastConsultationSummary(BaseModel):
    id: UUID
    appointment_id: UUID | None
    started_at: datetime
    ended_at: datetime | None
    doctor_name: str
    chief_complaint_summary: str | None
    status: str
    has_approved_report: bool


class LongitudinalPatientHistoryResponse(BaseModel):
    patient: PatientResponse
    total_consultations: int
    allergy_state: dict[str, Any]
    past_consultations: list[PastConsultationSummary]
    historical_medications: list[HistoricalMedicationItem]
    longitudinal_symptoms: list[dict[str, Any]]

