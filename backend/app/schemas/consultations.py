from datetime import date, datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ConsultationStatus
from app.schemas.appointments import AppointmentResponse


class ConsultationStartRequest(BaseModel):
    appointment_id: UUID


class ConsultationConsentRequest(BaseModel):
    purpose: str = Field(default="CLINICAL_DOCUMENTATION_AND_AI_ASSISTANCE", max_length=255)
    language: str = Field(default="en-IN", max_length=20)
    consent_wording_version: str = Field(default="1.0", max_length=50)
    consent_text_snapshot: str = Field(..., min_length=10)
    is_granted: bool = True


class ConsultationConsentWithdrawRequest(BaseModel):
    withdrawal_reason: str = Field(..., min_length=3, max_length=500)


class ConsentRecordResponse(BaseModel):
    id: UUID
    organization_id: UUID
    patient_id: UUID
    consultation_id: UUID | None
    recorded_by_doctor_id: UUID
    purpose: str
    language: str
    consent_wording_version: str
    consent_text_snapshot: str
    is_granted: bool
    granted_at: datetime
    withdrawn_at: datetime | None
    withdrawal_reason: str | None

    model_config = ConfigDict(from_attributes=True)


class ConsultationResponse(BaseModel):
    id: UUID
    organization_id: UUID
    location_id: UUID
    appointment_id: UUID | None
    patient_id: UUID
    doctor_user_id: UUID
    status: ConsultationStatus
    started_at: datetime
    ended_at: datetime | None
    chief_complaint_summary: str | None
    longitudinal_comparison_json: dict[str, Any]
    consent: ConsentRecordResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class DoctorDashboardQueueItem(BaseModel):
    appointment: AppointmentResponse
    consultation_id: UUID | None = None
    has_previous_history: bool = False
    consent_status: str = "NOT_RECORDED"  # "NOT_RECORDED", "GRANTED", "WITHDRAWN"


class DoctorDashboardResponse(BaseModel):
    doctor_name: str
    specialization: str
    consultation_room: str | None
    target_date: date
    current_patient: DoctorDashboardQueueItem | None = None
    waiting_patients: list[DoctorDashboardQueueItem] = []
    upcoming_patients: list[DoctorDashboardQueueItem] = []
    completed_patients: list[DoctorDashboardQueueItem] = []
    reports_pending_approval: list[dict[str, Any]] = []

