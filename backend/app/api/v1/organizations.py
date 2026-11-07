from datetime import datetime, timezone
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant_org_id, require_org_admin
from app.core.security import get_password_hash
from app.db.session import get_db
from app.models.enums import UserRole, enum_val
from app.models.patients_appointments import Appointment, DoctorSchedule
from app.models.subscriptions import Subscription, SubscriptionPlan, UsageRecord
from app.models.system_audit import AuditEvent
from app.models.tenant import (
    DoctorProfile,
    Organization,
    OrganizationLocation,
    OrganizationMembership,
    ReceptionistProfile,
    User,
)
from app.schemas.subscriptions import OrgSubscriptionOverview
from app.schemas.tenant import (
    DoctorCreate,
    DoctorResponse,
    DoctorScheduleCreate,
    DoctorScheduleResponse,
    LocationCreate,
    LocationResponse,
    OrgDashboardResponse,
    OrganizationProfileUpdate,
    OrganizationResponse,
    PublicOrganizationRegisterRequest,
    ReceptionistCreate,
    ReceptionistResponse,
    StaffOverviewResponse,
)
from app.integrations.email import email_service
from app.services.entitlement_service import EntitlementService

router = APIRouter(prefix="/org", tags=["Organization Admin & Entitlements"])


@router.get("/dashboard", response_model=OrgDashboardResponse)
def get_org_dashboard(
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    _: Annotated[OrganizationMembership, Depends(require_org_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> OrgDashboardResponse:
    org = db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")

    branches_count = db.execute(
        select(func.count(OrganizationLocation.id)).where(
            OrganizationLocation.organization_id == org_id,
            OrganizationLocation.is_active == True,
        )
    ).scalar() or 0

    doctors_count = db.execute(
        select(func.count(OrganizationMembership.id)).where(
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.role == UserRole.DOCTOR,
            OrganizationMembership.is_active == True,
        )
    ).scalar() or 0

    receptionists_count = db.execute(
        select(func.count(OrganizationMembership.id)).where(
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.role == UserRole.RECEPTIONIST,
            OrganizationMembership.is_active == True,
        )
    ).scalar() or 0

    sub = EntitlementService.get_active_subscription(db, org_id)
    plan_name = "No Plan"
    sub_status = "INACTIVE"
    quota_consultations = 0

    if sub:
        sub_status = enum_val(sub.status)
        plan = db.get(SubscriptionPlan, sub.plan_id)
        if plan:
            plan_name = plan.name
            quota_consultations = plan.monthly_consultation_limit

    month_str = datetime.now(timezone.utc).strftime("%Y-%m")
    usage = db.execute(
        select(UsageRecord).where(
            UsageRecord.organization_id == org_id,
            UsageRecord.period_month == month_str,
        )
    ).scalar_one_or_none()

    consultations_month = usage.consultations_count if usage else 0

    return OrgDashboardResponse(
        organization=OrganizationResponse.model_validate(org),
        branches_count=branches_count,
        doctors_count=doctors_count,
        receptionists_count=receptionists_count,
        subscription_status=sub_status,
        plan_name=plan_name,
        consultations_month_count=consultations_month,
        quota_consultations=quota_consultations,
    )


@router.get("/profile", response_model=OrganizationResponse)
def get_org_profile(
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    _: Annotated[OrganizationMembership, Depends(require_org_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> Organization:
    org = db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")
    return org


@router.patch("/profile", response_model=OrganizationResponse)
def update_org_profile(
    data: OrganizationProfileUpdate,
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    membership: Annotated[OrganizationMembership, Depends(require_org_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> Organization:
    EntitlementService.ensure_active_subscription_write_allowed(db, org_id)
    org = db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")

    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(org, field, val)

    audit = AuditEvent(
        organization_id=org_id,
        actor_user_id=membership.user_id,
        actor_role=enum_val(membership.role),
        event_type="ORGANIZATION_PROFILE_UPDATED",
        resource_type="ORGANIZATION",
        resource_id=org_id,
        action="UPDATE",
        metadata_json=data.model_dump(exclude_unset=True),
    )
    db.add(audit)

    db.commit()
    db.refresh(org)
    return org


# -----------------------------------------------------------------------------
# Branches
# -----------------------------------------------------------------------------
@router.get("/branches", response_model=list[LocationResponse])
def list_branches(
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    _: Annotated[OrganizationMembership, Depends(require_org_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> list[OrganizationLocation]:
    stmt = (
        select(OrganizationLocation)
        .where(OrganizationLocation.organization_id == org_id)
        .order_by(OrganizationLocation.created_at.asc())
    )
    return list(db.execute(stmt).scalars().all())


@router.post("/branches", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
def create_branch(
    data: LocationCreate,
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    membership: Annotated[OrganizationMembership, Depends(require_org_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> OrganizationLocation:
    # Enforce branch quota
    EntitlementService.check_branch_limit(db, org_id)

    # Check unique branch code within organization
    existing = db.execute(
        select(OrganizationLocation).where(
            OrganizationLocation.organization_id == org_id,
            OrganizationLocation.branch_code == data.branch_code,
        )
    ).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Branch code {data.branch_code} already exists in this organization.",
        )

    branch = OrganizationLocation(
        organization_id=org_id,
        name=data.name,
        branch_code=data.branch_code,
        address=data.address,
        phone=data.phone,
        is_active=True,
    )
    db.add(branch)
    db.flush()

    audit = AuditEvent(
        organization_id=org_id,
        actor_user_id=membership.user_id,
        actor_role=enum_val(membership.role),
        event_type="BRANCH_CREATED",
        resource_type="ORGANIZATION_LOCATION",
        resource_id=branch.id,
        action="CREATE",
        metadata_json={"branch_name": branch.name, "branch_code": branch.branch_code},
    )
    db.add(audit)

    db.commit()
    db.refresh(branch)
    return branch


# -----------------------------------------------------------------------------
# Staff Management: Doctors & Receptionists
# -----------------------------------------------------------------------------
@router.get("/staff", response_model=StaffOverviewResponse)
def get_staff_overview(
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    _: Annotated[OrganizationMembership, Depends(require_org_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> StaffOverviewResponse:
    # Doctors
    doc_stmts = (
        select(User, DoctorProfile)
        .join(OrganizationMembership, OrganizationMembership.user_id == User.id)
        .outerjoin(DoctorProfile, DoctorProfile.user_id == User.id)
        .where(
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.role == UserRole.DOCTOR,
            OrganizationMembership.is_active == True,
        )
    )
    doc_rows = db.execute(doc_stmts).all()
    doctors = [
        DoctorResponse(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            phone=u.phone,
            is_active=u.is_active,
            specialization=dp.specialization if dp else "General",
            qualification=dp.qualification if dp else "MBBS",
            registration_number=dp.registration_number if dp else "",
            consultation_room=dp.consultation_room if dp else None,
            languages_spoken=dp.languages_spoken if dp else "English, Hindi",
            location_id=dp.location_id if dp else None,
        )
        for u, dp in doc_rows
    ]

    # Receptionists
    rec_stmts = (
        select(User, ReceptionistProfile)
        .join(OrganizationMembership, OrganizationMembership.user_id == User.id)
        .outerjoin(ReceptionistProfile, ReceptionistProfile.user_id == User.id)
        .where(
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.role == UserRole.RECEPTIONIST,
            OrganizationMembership.is_active == True,
        )
    )
    rec_rows = db.execute(rec_stmts).all()
    receptionists = [
        ReceptionistResponse(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            phone=u.phone,
            is_active=u.is_active,
            desk_identifier=rp.desk_identifier if rp else None,
            shift_notes=rp.shift_notes if rp else None,
            location_id=rp.location_id if rp else None,
        )
        for u, rp in rec_rows
    ]

    return StaffOverviewResponse(doctors=doctors, receptionists=receptionists)


@router.post("/staff/doctors", response_model=DoctorResponse, status_code=status.HTTP_201_CREATED)
def create_doctor(
    data: DoctorCreate,
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    membership: Annotated[OrganizationMembership, Depends(require_org_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> DoctorResponse:
    # Enforce doctor entitlement limit
    EntitlementService.check_doctor_limit(db, org_id)

    # Validate location
    if data.location_id:
        loc = db.get(OrganizationLocation, data.location_id)
        if not loc or loc.organization_id != org_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid location specified.")

    existing_user = db.execute(select(User).where(User.email == data.email)).scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email {data.email} already exists.",
        )

    doctor_user = User(
        email=data.email,
        password_hash=get_password_hash(data.password),
        full_name=data.full_name,
        phone=data.phone,
        is_super_admin=False,
        is_active=True,
    )
    db.add(doctor_user)
    db.flush()

    db.add(
        OrganizationMembership(
            user_id=doctor_user.id,
            organization_id=org_id,
            location_id=data.location_id,
            role=UserRole.DOCTOR,
            is_active=True,
        )
    )

    profile = DoctorProfile(
        user_id=doctor_user.id,
        organization_id=org_id,
        location_id=data.location_id,
        specialization=data.specialization,
        qualification=data.qualification,
        registration_number=data.registration_number,
        consultation_room=data.consultation_room,
        languages_spoken=data.languages_spoken,
    )
    db.add(profile)
    db.flush()

    audit = AuditEvent(
        organization_id=org_id,
        actor_user_id=membership.user_id,
        actor_role=enum_val(membership.role),
        event_type="STAFF_DOCTOR_CREATED",
        resource_type="DOCTOR_PROFILE",
        resource_id=profile.id,
        action="CREATE",
        metadata_json={"doctor_email": doctor_user.email, "specialization": data.specialization},
    )
    db.add(audit)

    db.commit()

    return DoctorResponse(
        id=doctor_user.id,
        email=doctor_user.email,
        full_name=doctor_user.full_name,
        phone=doctor_user.phone,
        is_active=doctor_user.is_active,
        specialization=profile.specialization,
        qualification=profile.qualification,
        registration_number=profile.registration_number,
        consultation_room=profile.consultation_room,
        languages_spoken=profile.languages_spoken,
        location_id=profile.location_id,
    )


@router.post("/staff/receptionists", response_model=ReceptionistResponse, status_code=status.HTTP_201_CREATED)
def create_receptionist(
    data: ReceptionistCreate,
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    membership: Annotated[OrganizationMembership, Depends(require_org_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> ReceptionistResponse:
    # Enforce receptionist entitlement limit
    EntitlementService.check_receptionist_limit(db, org_id)

    if data.location_id:
        loc = db.get(OrganizationLocation, data.location_id)
        if not loc or loc.organization_id != org_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid location specified.")

    existing_user = db.execute(select(User).where(User.email == data.email)).scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email {data.email} already exists.",
        )

    rec_user = User(
        email=data.email,
        password_hash=get_password_hash(data.password),
        full_name=data.full_name,
        phone=data.phone,
        is_super_admin=False,
        is_active=True,
    )
    db.add(rec_user)
    db.flush()

    db.add(
        OrganizationMembership(
            user_id=rec_user.id,
            organization_id=org_id,
            location_id=data.location_id,
            role=UserRole.RECEPTIONIST,
            is_active=True,
        )
    )

    profile = ReceptionistProfile(
        user_id=rec_user.id,
        organization_id=org_id,
        location_id=data.location_id,
        desk_identifier=data.desk_identifier,
        shift_notes=data.shift_notes,
    )
    db.add(profile)
    db.flush()

    audit = AuditEvent(
        organization_id=org_id,
        actor_user_id=membership.user_id,
        actor_role=enum_val(membership.role),
        event_type="STAFF_RECEPTIONIST_CREATED",
        resource_type="RECEPTIONIST_PROFILE",
        resource_id=profile.id,
        action="CREATE",
        metadata_json={"receptionist_email": rec_user.email},
    )
    db.add(audit)

    db.commit()

    return ReceptionistResponse(
        id=rec_user.id,
        email=rec_user.email,
        full_name=rec_user.full_name,
        phone=rec_user.phone,
        is_active=rec_user.is_active,
        desk_identifier=profile.desk_identifier,
        shift_notes=profile.shift_notes,
        location_id=profile.location_id,
    )


# -----------------------------------------------------------------------------
# Schedules
# -----------------------------------------------------------------------------
@router.get("/schedules", response_model=list[DoctorScheduleResponse])
def list_schedules(
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    _: Annotated[OrganizationMembership, Depends(require_org_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> list[DoctorSchedule]:
    stmt = select(DoctorSchedule).where(DoctorSchedule.organization_id == org_id)
    return list(db.execute(stmt).scalars().all())


@router.post("/schedules", response_model=DoctorScheduleResponse, status_code=status.HTTP_201_CREATED)
def create_schedule(
    data: DoctorScheduleCreate,
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    membership: Annotated[OrganizationMembership, Depends(require_org_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> DoctorSchedule:
    EntitlementService.ensure_active_subscription_write_allowed(db, org_id)

    # Verify doctor belongs to this org
    doc_mem = db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == data.doctor_user_id,
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.role == UserRole.DOCTOR,
        )
    ).scalar_one_or_none()

    if not doc_mem:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Specified doctor does not belong to this organization.",
        )

    # Verify location belongs to this org
    loc = db.get(OrganizationLocation, data.location_id)
    if not loc or loc.organization_id != org_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid location specified.")

    schedule = DoctorSchedule(
        organization_id=org_id,
        location_id=data.location_id,
        doctor_user_id=data.doctor_user_id,
        day_of_week=data.day_of_week,
        start_time=data.start_time,
        end_time=data.end_time,
        slot_duration_minutes=data.slot_duration_minutes,
        is_active=True,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


# -----------------------------------------------------------------------------
# Subscription & Quotas
# -----------------------------------------------------------------------------
@router.get("/subscription", response_model=OrgSubscriptionOverview)
def get_subscription_overview(
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    _: Annotated[OrganizationMembership, Depends(require_org_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> OrgSubscriptionOverview:
    sub = EntitlementService.get_active_subscription(db, org_id)
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No subscription found.")

    plan = db.get(SubscriptionPlan, sub.plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription plan not found.")

    now = datetime.now(timezone.utc)
    end_date = sub.end_date.replace(tzinfo=timezone.utc) if sub.end_date.tzinfo is None else sub.end_date
    days_left = max((end_date - now).days, 0)
    is_active = enum_val(sub.status) in ("ACTIVE", "TRIAL") and end_date > now

    # Current usage
    month_str = now.strftime("%Y-%m")
    usage = db.execute(
        select(UsageRecord).where(
            UsageRecord.organization_id == org_id,
            UsageRecord.period_month == month_str,
        )
    ).scalar_one_or_none()

    branches_count = db.execute(
        select(func.count(OrganizationLocation.id)).where(
            OrganizationLocation.organization_id == org_id,
            OrganizationLocation.is_active == True,
        )
    ).scalar() or 0

    doctors_count = db.execute(
        select(func.count(OrganizationMembership.id)).where(
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.role == UserRole.DOCTOR,
            OrganizationMembership.is_active == True,
        )
    ).scalar() or 0

    receptionists_count = db.execute(
        select(func.count(OrganizationMembership.id)).where(
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.role == UserRole.RECEPTIONIST,
            OrganizationMembership.is_active == True,
        )
    ).scalar() or 0

    return OrgSubscriptionOverview(
        subscription_id=sub.id,
        plan_name=plan.name,
        plan_code=plan.code,
        status=sub.status,
        start_date=sub.start_date,
        end_date=sub.end_date,
        days_remaining=days_left,
        is_active=is_active,
        limits={
            "max_doctors": plan.max_doctors,
            "max_receptionists": plan.max_receptionists,
            "max_branches": plan.max_branches,
            "monthly_consultation_limit": plan.monthly_consultation_limit,
            "audio_storage_mb_limit": plan.audio_storage_mb_limit,
            "report_generation_limit": plan.report_generation_limit,
        },
        current_usage={
            "branches": branches_count,
            "doctors": doctors_count,
            "receptionists": receptionists_count,
            "consultations_this_month": usage.consultations_count if usage else 0,
            "audio_storage_mb": (usage.audio_storage_bytes_used // (1024 * 1024)) if usage else 0,
        },
    )


registration_router = APIRouter(prefix="/organizations", tags=["Public Organization Onboarding"])


@registration_router.post("/register", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
@router.post("/register", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
def register_organization(
    data: PublicOrganizationRegisterRequest,
    db: Annotated[Session, Depends(get_db)],
) -> Organization:
    """Public clinic onboarding inquiry endpoint.
    Creates a PENDING organization record, stores desired plan/commercials,
    notifies the Platform Owner team via email and dashboard, and awaits admin approval.
    """
    existing_user = db.execute(select(User).where(User.email == data.contact_email)).scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email {data.contact_email} already exists.",
        )

    requested_plan = getattr(data, "requested_plan", "PROFESSIONAL") or "PROFESSIONAL"
    requested_billing = getattr(data, "requested_billing_cycle", "MONTHLY") or "MONTHLY"
    coupon_code = getattr(data, "coupon_code", None)

    org = Organization(
        name=data.name,
        org_type=data.org_type,
        contact_email=data.contact_email,
        contact_phone=data.contact_phone or "N/A",
        address=data.address,
        status="PENDING",
        settings_json={
            "admin_full_name": data.admin_full_name,
            "requested_plan": requested_plan.upper(),
            "requested_billing_cycle": requested_billing.upper(),
            "coupon_code": coupon_code.upper() if coupon_code else None,
            "requested_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    db.add(org)
    db.flush()

    # Record Audit Event
    audit = AuditEvent(
        organization_id=org.id,
        actor_role="PUBLIC",
        event_type="ORG_REGISTRATION_REQUEST_RECEIVED",
        resource_type="ORGANIZATION",
        resource_id=org.id,
        action="SUBMIT_INQUIRY",
        metadata_json={
            "clinic_name": data.name,
            "admin_name": data.admin_full_name,
            "contact_email": data.contact_email,
            "requested_plan": requested_plan.upper(),
            "coupon_code": coupon_code,
        },
    )
    db.add(audit)

    # Dispatch Owner Notification Email
    email_service.send_owner_registration_alert(
        {
            "name": data.name,
            "org_type": data.org_type,
            "admin_full_name": data.admin_full_name,
            "contact_email": data.contact_email,
            "contact_phone": data.contact_phone,
            "address": data.address,
            "requested_plan": requested_plan.upper(),
            "requested_billing_cycle": requested_billing.upper(),
            "coupon_code": coupon_code,
        }
    )

    db.commit()
    db.refresh(org)
    return org
