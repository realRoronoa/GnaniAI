from datetime import date
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_membership, get_current_tenant_org_id, require_receptionist
from app.db.session import get_db
from app.models.enums import AppointmentStatus, AppointmentType, enum_val
from app.models.tenant import OrganizationMembership
from app.schemas.appointments import (
    AppointmentCreate,
    AppointmentResponse,
    AppointmentStatusUpdate,
    DoctorAssignRequest,
    PatientSummaryInAppointment,
    QueueViewResponse,
    ReceptionOverviewResponse,
)
from app.services.appointment_service import AppointmentService

router = APIRouter(tags=["Appointments & Reception Queue"])


@router.post("/appointments", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
def create_appointment(
    data: AppointmentCreate,
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    membership: Annotated[OrganizationMembership, Depends(get_current_membership)],
    db: Annotated[Session, Depends(get_db)],
) -> AppointmentResponse:
    appointment = AppointmentService.create_appointment(
        db=db,
        organization_id=org_id,
        created_by_user_id=membership.user_id,
        data=data,
    )
    doc_user = appointment.doctor
    return AppointmentResponse(
        id=appointment.id,
        organization_id=appointment.organization_id,
        location_id=appointment.location_id,
        patient_id=appointment.patient_id,
        doctor_user_id=appointment.doctor_user_id,
        doctor_name=doc_user.full_name if doc_user else None,
        created_by_user_id=appointment.created_by_user_id,
        appointment_date=appointment.appointment_date,
        scheduled_time=appointment.scheduled_time,
        queue_position=appointment.queue_position,
        appointment_type=appointment.appointment_type,
        status=appointment.status,
        reason_for_visit=appointment.reason_for_visit,
        administrative_notes=appointment.administrative_notes,
        arrived_at=appointment.arrived_at,
        started_at=appointment.started_at,
        completed_at=appointment.completed_at,
        created_at=appointment.created_at,
        patient=PatientSummaryInAppointment.model_validate(appointment.patient) if appointment.patient else None,
    )


@router.patch("/appointments/{appointment_id}/status", response_model=AppointmentResponse)
def update_appointment_status(
    appointment_id: uuid.UUID,
    data: AppointmentStatusUpdate,
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    membership: Annotated[OrganizationMembership, Depends(get_current_membership)],
    db: Annotated[Session, Depends(get_db)],
) -> AppointmentResponse:
    appointment = AppointmentService.update_status(
        db=db,
        organization_id=org_id,
        appointment_id=appointment_id,
        new_status=data.status,
        actor_user_id=membership.user_id,
        actor_role=enum_val(membership.role),
    )
    doc_user = appointment.doctor
    return AppointmentResponse(
        id=appointment.id,
        organization_id=appointment.organization_id,
        location_id=appointment.location_id,
        patient_id=appointment.patient_id,
        doctor_user_id=appointment.doctor_user_id,
        doctor_name=doc_user.full_name if doc_user else None,
        created_by_user_id=appointment.created_by_user_id,
        appointment_date=appointment.appointment_date,
        scheduled_time=appointment.scheduled_time,
        queue_position=appointment.queue_position,
        appointment_type=appointment.appointment_type,
        status=appointment.status,
        reason_for_visit=appointment.reason_for_visit,
        administrative_notes=appointment.administrative_notes,
        arrived_at=appointment.arrived_at,
        started_at=appointment.started_at,
        completed_at=appointment.completed_at,
        created_at=appointment.created_at,
        patient=PatientSummaryInAppointment.model_validate(appointment.patient) if appointment.patient else None,
    )


@router.patch("/appointments/{appointment_id}/assign-doctor", response_model=AppointmentResponse)
def assign_doctor_to_appointment(
    appointment_id: uuid.UUID,
    data: DoctorAssignRequest,
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    membership: Annotated[OrganizationMembership, Depends(get_current_membership)],
    db: Annotated[Session, Depends(get_db)],
) -> AppointmentResponse:
    appointment = AppointmentService.assign_doctor(
        db=db,
        organization_id=org_id,
        appointment_id=appointment_id,
        new_doctor_user_id=data.doctor_user_id,
        actor_user_id=membership.user_id,
    )
    doc_user = appointment.doctor
    return AppointmentResponse(
        id=appointment.id,
        organization_id=appointment.organization_id,
        location_id=appointment.location_id,
        patient_id=appointment.patient_id,
        doctor_user_id=appointment.doctor_user_id,
        doctor_name=doc_user.full_name if doc_user else None,
        created_by_user_id=appointment.created_by_user_id,
        appointment_date=appointment.appointment_date,
        scheduled_time=appointment.scheduled_time,
        queue_position=appointment.queue_position,
        appointment_type=appointment.appointment_type,
        status=appointment.status,
        reason_for_visit=appointment.reason_for_visit,
        administrative_notes=appointment.administrative_notes,
        arrived_at=appointment.arrived_at,
        started_at=appointment.started_at,
        completed_at=appointment.completed_at,
        created_at=appointment.created_at,
        patient=PatientSummaryInAppointment.model_validate(appointment.patient) if appointment.patient else None,
    )


@router.get("/appointments/queue", response_model=QueueViewResponse)
def get_appointment_queue(
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    _: Annotated[OrganizationMembership, Depends(get_current_membership)],
    db: Annotated[Session, Depends(get_db)],
    target_date: date | None = Query(default=None),
    doctor_user_id: uuid.UUID | None = Query(default=None),
    location_id: uuid.UUID | None = Query(default=None),
    status_filter: AppointmentStatus | None = Query(default=None),
    appointment_type: AppointmentType | None = Query(default=None),
) -> QueueViewResponse:
    return AppointmentService.get_queue(
        db=db,
        organization_id=org_id,
        target_date=target_date,
        doctor_user_id=doctor_user_id,
        location_id=location_id,
        status_filter=status_filter,
        appointment_type=appointment_type,
    )


@router.get("/reception/overview", response_model=ReceptionOverviewResponse)
def get_reception_overview(
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    _: Annotated[OrganizationMembership, Depends(require_receptionist)],
    db: Annotated[Session, Depends(get_db)],
    target_date: date | None = Query(default=None),
) -> ReceptionOverviewResponse:
    return AppointmentService.get_reception_overview(
        db=db,
        organization_id=org_id,
        target_date=target_date,
    )

