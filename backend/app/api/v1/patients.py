import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_membership,
    get_current_tenant_org_id,
    require_doctor,
    require_receptionist,
)
from app.db.session import get_db
from app.models.tenant import OrganizationMembership
from app.schemas.patients import (
    DuplicateCheckResponse,
    LongitudinalPatientHistoryResponse,
    PatientCreate,
    PatientResponse,
    PatientUpdate,
)
from app.services.patient_service import PatientService

router = APIRouter(prefix="/patients", tags=["Patient Management & History"])


@router.get("/check-duplicates", response_model=DuplicateCheckResponse)
def check_duplicate_patients(
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    _: Annotated[OrganizationMembership, Depends(get_current_membership)],
    db: Annotated[Session, Depends(get_db)],
    mobile_number: str | None = Query(default=None, description="Mobile number to check"),
    full_name: str | None = Query(default=None, description="Patient full name to check"),
) -> DuplicateCheckResponse:
    """Pre-registration duplicate verification.
    Warning returns potential matches but allows receptionists to proceed for family members.
    """
    return PatientService.check_duplicates(
        db=db,
        organization_id=org_id,
        mobile_number=mobile_number,
        full_name=full_name,
    )


@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
def register_patient(
    data: PatientCreate,
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    _: Annotated[OrganizationMembership, Depends(get_current_membership)],
    db: Annotated[Session, Depends(get_db)],
) -> PatientResponse:
    patient = PatientService.create_patient(db=db, organization_id=org_id, data=data)
    return PatientResponse.model_validate(patient)


@router.get("", response_model=list[PatientResponse])
def search_patients(
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    _: Annotated[OrganizationMembership, Depends(get_current_membership)],
    db: Annotated[Session, Depends(get_db)],
    q: str | None = Query(default=None, description="Search query by name, UHID, or mobile number"),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[PatientResponse]:
    patients = PatientService.search_patients(db=db, organization_id=org_id, query=q, limit=limit)
    return [PatientResponse.model_validate(p) for p in patients]


@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(
    patient_id: uuid.UUID,
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    _: Annotated[OrganizationMembership, Depends(get_current_membership)],
    db: Annotated[Session, Depends(get_db)],
) -> PatientResponse:
    patient = PatientService.get_patient(db=db, organization_id=org_id, patient_id=patient_id)
    return PatientResponse.model_validate(patient)


@router.patch("/{patient_id}", response_model=PatientResponse)
def update_patient(
    patient_id: uuid.UUID,
    data: PatientUpdate,
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    _: Annotated[OrganizationMembership, Depends(get_current_membership)],
    db: Annotated[Session, Depends(get_db)],
) -> PatientResponse:
    patient = PatientService.update_patient(
        db=db, organization_id=org_id, patient_id=patient_id, data=data
    )
    return PatientResponse.model_validate(patient)


@router.get("/{patient_id}/longitudinal-history", response_model=LongitudinalPatientHistoryResponse)
def get_patient_longitudinal_history(
    patient_id: uuid.UUID,
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    _: Annotated[OrganizationMembership, Depends(require_doctor)],
    db: Annotated[Session, Depends(get_db)],
) -> LongitudinalPatientHistoryResponse:
    """Doctor longitudinal medical history: past visits, approved notes, and historical medications."""
    return PatientService.get_longitudinal_history(
        db=db, organization_id=org_id, patient_id=patient_id
    )

