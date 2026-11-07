from datetime import date, datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import AppointmentStatus, AppointmentType


class AppointmentCreate(BaseModel):
    patient_id: UUID
    doctor_user_id: UUID
    location_id: UUID | None = None
    appointment_date: date
    scheduled_time: datetime | None = None
    appointment_type: AppointmentType = AppointmentType.SCHEDULED
    reason_for_visit: str | None = None
    administrative_notes: str | None = None
    initial_status: AppointmentStatus | None = None  # e.g., ARRIVED or WAITING for walk-ins

    @field_validator("scheduled_time", mode="before")
    @classmethod
    def parse_scheduled_time(cls, v: Any) -> Any:
        if not v:
            return None
        if isinstance(v, str):
            v_str = v.strip()
            if not v_str:
                return None
            if len(v_str) <= 8 and ":" in v_str:
                try:
                    parts = [int(p) for p in v_str.split(":")]
                    now = datetime.now()
                    if len(parts) == 2:
                        return datetime(now.year, now.month, now.day, parts[0], parts[1])
                    elif len(parts) == 3:
                        return datetime(now.year, now.month, now.day, parts[0], parts[1], parts[2])
                except Exception:
                    pass
            try:
                return datetime.fromisoformat(v_str.replace("Z", "+00:00"))
            except Exception:
                pass
        return v


class AppointmentStatusUpdate(BaseModel):
    status: AppointmentStatus


class DoctorAssignRequest(BaseModel):
    doctor_user_id: UUID


class PatientSummaryInAppointment(BaseModel):
    id: UUID
    patient_identifier: str
    full_name: str
    age_years: int | None
    gender: str
    mobile_number: str
    preferred_language: str
    allergies_summary: str | None

    model_config = ConfigDict(from_attributes=True)


class AppointmentResponse(BaseModel):
    id: UUID
    organization_id: UUID
    location_id: UUID
    patient_id: UUID
    doctor_user_id: UUID
    doctor_name: str | None = None
    created_by_user_id: UUID | None
    appointment_date: date
    scheduled_time: datetime
    queue_position: int | None
    appointment_type: AppointmentType
    status: AppointmentStatus
    reason_for_visit: str | None
    administrative_notes: str | None
    arrived_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    patient: PatientSummaryInAppointment | None = None

    model_config = ConfigDict(from_attributes=True)


class ReceptionOverviewResponse(BaseModel):
    target_date: date
    total_today: int
    waiting: int
    arrived: int
    in_progress: int
    completed: int
    cancelled: int
    no_show: int


class DoctorQueueGroup(BaseModel):
    doctor_user_id: UUID | None = None
    doctor_name: str
    specialization: str
    consultation_room: str | None
    waiting_count: int
    appointments: list[AppointmentResponse] = []


class QueueViewResponse(BaseModel):
    target_date: date | None = None
    total_in_queue: int
    doctor_queues: list[DoctorQueueGroup] = []
    queue: list[AppointmentResponse] = []

