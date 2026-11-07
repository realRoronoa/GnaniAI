from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AppointmentStatus, AppointmentType


class AppointmentCreate(BaseModel):
    patient_id: UUID
    doctor_user_id: UUID
    location_id: UUID
    appointment_date: date
    scheduled_time: datetime
    appointment_type: AppointmentType = AppointmentType.SCHEDULED
    reason_for_visit: str | None = None
    administrative_notes: str | None = None
    initial_status: AppointmentStatus | None = None  # e.g., ARRIVED or WAITING for walk-ins


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
    doctor_user_id: UUID
    doctor_name: str
    specialization: str
    consultation_room: str | None
    waiting_count: int
    appointments: list[AppointmentResponse]


class QueueViewResponse(BaseModel):
    target_date: date
    total_in_queue: int
    doctor_queues: list[DoctorQueueGroup]

