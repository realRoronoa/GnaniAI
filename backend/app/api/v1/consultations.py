from datetime import date
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_membership,
    get_current_tenant_org_id,
    require_doctor,
)
from app.db.session import get_db
from app.models.consultations_audio import ConsentRecord, Consultation
from app.models.tenant import OrganizationMembership
from app.schemas.consultations import (
    ConsentRecordResponse,
    ConsultationConsentRequest,
    ConsultationConsentWithdrawRequest,
    ConsultationResponse,
    ConsultationStartRequest,
    DoctorDashboardResponse,
)
from app.services.consultation_service import ConsultationService

router = APIRouter(tags=["Doctor Workspace & Clinical Consultations"])


@router.get("/doctor/dashboard", response_model=DoctorDashboardResponse)
def get_doctor_dashboard(
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    membership: Annotated[OrganizationMembership, Depends(require_doctor)],
    db: Annotated[Session, Depends(get_db)],
    target_date: date | None = Query(default=None),
) -> DoctorDashboardResponse:
    """Doctor Workspace: today's assigned outpatient queue, active encounter, and pending notes."""
    return ConsultationService.get_doctor_dashboard(
        db=db,
        organization_id=org_id,
        doctor_user_id=membership.user_id,
        target_date=target_date,
    )


@router.post("/consultations", response_model=ConsultationResponse, status_code=status.HTTP_201_CREATED)
def start_or_resume_consultation(
    data: ConsultationStartRequest,
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    membership: Annotated[OrganizationMembership, Depends(require_doctor)],
    db: Annotated[Session, Depends(get_db)],
) -> ConsultationResponse:
    consultation = ConsultationService.start_consultation(
        db=db,
        organization_id=org_id,
        doctor_user_id=membership.user_id,
        appointment_id=data.appointment_id,
    )
    # Fetch active consent if any
    consent = db.execute(
        select(ConsentRecord).where(ConsentRecord.consultation_id == consultation.id)
    ).scalar_one_or_none()

    return ConsultationResponse(
        id=consultation.id,
        organization_id=consultation.organization_id,
        location_id=consultation.location_id,
        appointment_id=consultation.appointment_id,
        patient_id=consultation.patient_id,
        doctor_user_id=consultation.doctor_user_id,
        status=consultation.status,
        started_at=consultation.started_at,
        ended_at=consultation.ended_at,
        chief_complaint_summary=consultation.chief_complaint_summary,
        longitudinal_comparison_json=consultation.longitudinal_comparison_json,
        consent=ConsentRecordResponse.model_validate(consent) if consent else None,
    )


@router.get("/consultations/{consultation_id}", response_model=ConsultationResponse)
def get_consultation(
    consultation_id: uuid.UUID,
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    _: Annotated[OrganizationMembership, Depends(get_current_membership)],
    db: Annotated[Session, Depends(get_db)],
) -> ConsultationResponse:
    consultation = db.get(Consultation, consultation_id)
    if not consultation or consultation.organization_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation session not found.")

    consent = db.execute(
        select(ConsentRecord).where(ConsentRecord.consultation_id == consultation.id)
    ).scalar_one_or_none()

    return ConsultationResponse(
        id=consultation.id,
        organization_id=consultation.organization_id,
        location_id=consultation.location_id,
        appointment_id=consultation.appointment_id,
        patient_id=consultation.patient_id,
        doctor_user_id=consultation.doctor_user_id,
        status=consultation.status,
        started_at=consultation.started_at,
        ended_at=consultation.ended_at,
        chief_complaint_summary=consultation.chief_complaint_summary,
        longitudinal_comparison_json=consultation.longitudinal_comparison_json,
        consent=ConsentRecordResponse.model_validate(consent) if consent else None,
    )


@router.post("/consultations/{consultation_id}/consent", response_model=ConsentRecordResponse)
def record_consultation_consent(
    consultation_id: uuid.UUID,
    data: ConsultationConsentRequest,
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    membership: Annotated[OrganizationMembership, Depends(require_doctor)],
    db: Annotated[Session, Depends(get_db)],
) -> ConsentRecordResponse:
    consent = ConsultationService.record_consent(
        db=db,
        organization_id=org_id,
        doctor_user_id=membership.user_id,
        consultation_id=consultation_id,
        data=data,
    )
    return ConsentRecordResponse.model_validate(consent)


@router.post("/consultations/{consultation_id}/consent/withdraw", response_model=ConsentRecordResponse)
def withdraw_consultation_consent(
    consultation_id: uuid.UUID,
    data: ConsultationConsentWithdrawRequest,
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    membership: Annotated[OrganizationMembership, Depends(require_doctor)],
    db: Annotated[Session, Depends(get_db)],
) -> ConsentRecordResponse:
    consent = ConsultationService.withdraw_consent(
        db=db,
        organization_id=org_id,
        doctor_user_id=membership.user_id,
        consultation_id=consultation_id,
        data=data,
    )
    return ConsentRecordResponse.model_validate(consent)

