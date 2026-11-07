from datetime import datetime, timedelta, timezone
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_platform_owner
from app.core.security import get_password_hash
from app.db.session import get_db
from app.models.enums import BillingCycle, OrgStatus, PaymentMode, PaymentStatus, SubscriptionStatus, UserRole, enum_val
from app.models.patients_appointments import Appointment
from app.models.subscriptions import DiscountCoupon, PaymentTransaction, Subscription, SubscriptionPlan, UsageRecord
from app.models.system_audit import AuditEvent
from app.models.tenant import Organization, OrganizationLocation, OrganizationMembership, User
from app.schemas.subscriptions import (
    CouponCreate,
    CouponPatch,
    CouponResponse,
    PlanCreate,
    PlanPatch,
    PlanResponse,
    SubscriptionActivateRequest,
    SubscriptionResponse,
)
from app.schemas.tenant import (
    OnboardingApprovalRequest,
    OnboardingApprovalResponse,
    OrganizationCreate,
    OrganizationResponse,
    OrganizationStatusUpdate,
    PlatformOverviewResponse,
)
from app.integrations.email import email_service
import secrets

router = APIRouter(prefix="/platform", tags=["Platform Owner / Super Admin"])


@router.get("/overview", response_model=PlatformOverviewResponse)
def get_platform_overview(
    _: Annotated[User, Depends(require_platform_owner)],
    db: Annotated[Session, Depends(get_db)],
) -> PlatformOverviewResponse:
    total_orgs = db.execute(select(func.count(Organization.id))).scalar() or 0
    active_orgs = db.execute(
        select(func.count(Organization.id)).where(Organization.status == OrgStatus.ACTIVE)
    ).scalar() or 0

    total_subs = db.execute(select(func.count(Subscription.id))).scalar() or 0
    active_subs = db.execute(
        select(func.count(Subscription.id)).where(Subscription.status == SubscriptionStatus.ACTIVE)
    ).scalar() or 0
    expired_subs = db.execute(
        select(func.count(Subscription.id)).where(Subscription.status == SubscriptionStatus.EXPIRED)
    ).scalar() or 0

    total_doctors = db.execute(
        select(func.count(OrganizationMembership.id)).where(
            OrganizationMembership.role == UserRole.DOCTOR,
            OrganizationMembership.is_active == True,
        )
    ).scalar() or 0

    total_receptionists = db.execute(
        select(func.count(OrganizationMembership.id)).where(
            OrganizationMembership.role == UserRole.RECEPTIONIST,
            OrganizationMembership.is_active == True,
        )
    ).scalar() or 0

    total_consultations = db.execute(select(func.count(Appointment.id))).scalar() or 0

    return PlatformOverviewResponse(
        total_organizations=total_orgs,
        active_organizations=active_orgs,
        total_subscriptions=total_subs,
        active_subscriptions=active_subs,
        expired_subscriptions=expired_subs,
        total_doctors=total_doctors,
        total_receptionists=total_receptionists,
        total_consultations=total_consultations,
    )


@router.get("/organizations", response_model=list[OrganizationResponse])
def list_organizations(
    _: Annotated[User, Depends(require_platform_owner)],
    db: Annotated[Session, Depends(get_db)],
) -> list[Organization]:
    stmt = select(Organization).order_by(Organization.created_at.desc())
    return list(db.execute(stmt).scalars().all())


@router.post("/organizations", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
def create_organization(
    data: OrganizationCreate,
    current_admin: Annotated[User, Depends(require_platform_owner)],
    db: Annotated[Session, Depends(get_db)],
) -> Organization:
    # Check if admin email already exists
    existing_user = db.execute(select(User).where(User.email == data.admin_email)).scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email {data.admin_email} already exists.",
        )

    # Create Organization
    org = Organization(
        name=data.name,
        org_type=data.org_type,
        contact_email=data.contact_email,
        contact_phone=data.contact_phone,
        address=data.address,
        registration_number=data.registration_number,
        status=OrgStatus.ACTIVE,
        settings_json=data.settings_json,
    )
    db.add(org)
    db.flush()

    # Create Initial Branch (Main Branch)
    main_branch = OrganizationLocation(
        organization_id=org.id,
        name=f"{org.name} - Main Branch",
        branch_code="MAIN-01",
        address=org.address,
        phone=org.contact_phone,
        is_active=True,
    )
    db.add(main_branch)
    db.flush()

    # Create Org Admin User
    admin_user = User(
        email=data.admin_email,
        password_hash=get_password_hash(data.admin_password),
        full_name=data.admin_full_name,
        phone=data.admin_phone,
        is_super_admin=False,
        is_active=True,
    )
    db.add(admin_user)
    db.flush()

    # Create Membership
    membership = OrganizationMembership(
        user_id=admin_user.id,
        organization_id=org.id,
        location_id=main_branch.id,
        role=UserRole.ORG_ADMIN,
        is_active=True,
    )
    db.add(membership)

    # Attach default Starter plan in trial mode
    starter_plan = db.execute(
        select(SubscriptionPlan).where(SubscriptionPlan.code == "STARTER")
    ).scalar_one_or_none()

    if starter_plan:
        now = datetime.now(timezone.utc)
        trial_sub = Subscription(
            organization_id=org.id,
            plan_id=starter_plan.id,
            status=SubscriptionStatus.TRIAL,
            billing_cycle=BillingCycle.MONTHLY,
            start_date=now,
            end_date=now + timedelta(days=starter_plan.trial_days),
            auto_renew=False,
            activated_by_user_id=current_admin.id,
        )
        db.add(trial_sub)

    # Record Audit Event
    audit = AuditEvent(
        organization_id=org.id,
        actor_user_id=current_admin.id,
        actor_role=UserRole.PLATFORM_OWNER.value,
        event_type="ORGANIZATION_ONBOARDED",
        resource_type="ORGANIZATION",
        resource_id=org.id,
        action="CREATE",
        metadata_json={"organization_name": org.name, "admin_email": admin_user.email},
    )
    db.add(audit)

    db.commit()
    db.refresh(org)
    return org


@router.patch("/organizations/{org_id}/status", response_model=OrganizationResponse)
def update_organization_status(
    org_id: uuid.UUID,
    data: OrganizationStatusUpdate,
    current_admin: Annotated[User, Depends(require_platform_owner)],
    db: Annotated[Session, Depends(get_db)],
) -> Organization:
    org = db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")

    old_status = org.status
    org.status = data.status

    audit = AuditEvent(
        organization_id=org.id,
        actor_user_id=current_admin.id,
        actor_role=UserRole.PLATFORM_OWNER.value,
        event_type="ORGANIZATION_STATUS_UPDATED",
        resource_type="ORGANIZATION",
        resource_id=org.id,
        action="UPDATE",
        metadata_json={"old_status": enum_val(old_status), "new_status": enum_val(data.status)},
    )
    db.add(audit)

    db.commit()
    db.refresh(org)
    return org


@router.post("/organizations/{org_id}/approve-onboarding", response_model=OnboardingApprovalResponse)
def approve_organization_onboarding(
    org_id: uuid.UUID,
    data: OnboardingApprovalRequest,
    current_admin: Annotated[User, Depends(require_platform_owner)],
    db: Annotated[Session, Depends(get_db)],
) -> OnboardingApprovalResponse:
    org = db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")

    plan = db.get(SubscriptionPlan, data.plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription plan not found.")

    now = datetime.now(timezone.utc)
    org.status = OrgStatus.ACTIVE

    # Compute final price
    amount = data.custom_final_price_inr
    if amount is None:
        amount = plan.annual_price if data.billing_cycle == BillingCycle.ANNUAL else plan.monthly_price
        if data.coupon_code:
            coupon = db.execute(
                select(DiscountCoupon).where(
                    DiscountCoupon.code == data.coupon_code.upper().strip(),
                    DiscountCoupon.is_active.is_(True),
                )
            ).scalar_one_or_none()
            if coupon:
                if coupon.discount_type == "PERCENTAGE":
                    pct = coupon.discount_value / Decimal("100")
                    amount = max(Decimal("0.00"), amount * (Decimal("1.00") - pct))
                else:
                    amount = max(Decimal("0.00"), amount - coupon.discount_value)

    # 1. Provision / activate subscription
    existing_sub = db.execute(
        select(Subscription).where(
            Subscription.organization_id == org.id,
            Subscription.status == SubscriptionStatus.ACTIVE,
        )
    ).scalar_one_or_none()

    if existing_sub:
        existing_sub.plan_id = plan.id
        existing_sub.billing_cycle = data.billing_cycle
        existing_sub.end_date = now + timedelta(days=data.duration_days)
        subscription = existing_sub
    else:
        subscription = Subscription(
            organization_id=org.id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE,
            billing_cycle=data.billing_cycle,
            start_date=now,
            end_date=now + timedelta(days=data.duration_days),
            auto_renew=True,
            activated_by_user_id=current_admin.id,
        )
        db.add(subscription)
    db.flush()

    # 2. Record payment transaction
    payment = PaymentTransaction(
        organization_id=org.id,
        subscription_id=subscription.id,
        amount=amount,
        currency="INR",
        payment_mode=PaymentMode.DEVELOPMENT_MANUAL,
        gateway_reference=f"ONBOARD-ACT-{uuid.uuid4().hex[:8].upper()}",
        status=PaymentStatus.VERIFIED,
        verified_at=now,
    )
    db.add(payment)

    # 3. Ensure primary clinic branch location exists
    main_branch = db.execute(
        select(OrganizationLocation).where(OrganizationLocation.organization_id == org.id)
    ).scalars().first()
    if not main_branch:
        main_branch = OrganizationLocation(
            organization_id=org.id,
            name=f"{org.name} - Main Branch",
            branch_code="MAIN-01",
            address=org.address,
            phone=org.contact_phone,
            is_active=True,
        )
        db.add(main_branch)
        db.flush()

    # 4. Generate or use password and provision single initial Org Admin
    temp_pass = (
        data.temporary_password.strip()
        if (data.temporary_password and data.temporary_password.strip())
        else secrets.token_urlsafe(9)
    )

    admin_user = db.execute(select(User).where(User.email == data.admin_email)).scalar_one_or_none()
    if not admin_user:
        admin_user = User(
            email=data.admin_email,
            password_hash=get_password_hash(temp_pass),
            full_name=data.admin_full_name,
            phone=org.contact_phone,
            is_super_admin=False,
            is_active=True,
        )
        db.add(admin_user)
        db.flush()
    else:
        admin_user.password_hash = get_password_hash(temp_pass)
        admin_user.full_name = data.admin_full_name
        admin_user.is_active = True
        db.flush()

    # Link membership
    membership = db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == admin_user.id,
            OrganizationMembership.organization_id == org.id,
        )
    ).scalar_one_or_none()
    if not membership:
        membership = OrganizationMembership(
            user_id=admin_user.id,
            organization_id=org.id,
            location_id=main_branch.id,
            role=UserRole.ORG_ADMIN,
            is_active=True,
        )
        db.add(membership)
    else:
        membership.role = UserRole.ORG_ADMIN
        membership.is_active = True

    # 5. Record initial monthly usage record
    period_str = now.strftime("%Y-%m")
    usage = db.execute(
        select(UsageRecord).where(
            UsageRecord.organization_id == org.id,
            UsageRecord.period_month == period_str,
        )
    ).scalar_one_or_none()
    if not usage:
        usage = UsageRecord(
            organization_id=org.id,
            subscription_id=subscription.id,
            period_month=period_str,
            consultations_count=0,
            audio_storage_bytes_used=0,
            reports_generated_count=0,
            active_doctors_count=0,
            active_receptionists_count=0,
            active_branches_count=1,
        )
        db.add(usage)

    # 6. Audit Event
    audit = AuditEvent(
        organization_id=org.id,
        actor_user_id=current_admin.id,
        actor_role=UserRole.PLATFORM_OWNER.value,
        event_type="ORG_ONBOARDING_APPROVED",
        resource_type="ORGANIZATION",
        resource_id=org.id,
        action="APPROVE_AND_PROVISION",
        metadata_json={
            "plan_code": plan.code,
            "billing_cycle": data.billing_cycle.value,
            "final_amount": float(amount),
            "admin_email": admin_user.email,
        },
    )
    db.add(audit)

    # 7. Send Welcome Email with credentials
    email_service.send_customer_approval_welcome(
        admin_email=admin_user.email,
        admin_name=admin_user.full_name or "Clinic Administrator",
        org_name=org.name,
        plan_name=plan.name,
        temp_password=temp_pass,
    )

    db.commit()

    return OnboardingApprovalResponse(
        organization_id=org.id,
        organization_name=org.name,
        status=org.status,
        subscription_id=subscription.id,
        plan_code=plan.code,
        admin_user_id=admin_user.id,
        admin_email=admin_user.email,
        temporary_password=temp_pass,
        message=f"Organization '{org.name}' successfully activated with {plan.name} plan!",
    )



# -----------------------------------------------------------------------------
# Plan Management
# -----------------------------------------------------------------------------
@router.get("/plans", response_model=list[PlanResponse])
def list_plans(
    _: Annotated[User, Depends(require_platform_owner)],
    db: Annotated[Session, Depends(get_db)],
) -> list[SubscriptionPlan]:
    return list(db.execute(select(SubscriptionPlan).order_by(SubscriptionPlan.monthly_price.asc())).scalars().all())


@router.post("/plans", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
def create_plan(
    data: PlanCreate,
    _: Annotated[User, Depends(require_platform_owner)],
    db: Annotated[Session, Depends(get_db)],
) -> SubscriptionPlan:
    existing = db.execute(
        select(SubscriptionPlan).where(SubscriptionPlan.code == data.code)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Plan code {data.code} already exists.")

    plan = SubscriptionPlan(**data.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.patch("/plans/{plan_id}", response_model=PlanResponse)
def patch_plan(
    plan_id: uuid.UUID,
    data: PlanPatch,
    _: Annotated[User, Depends(require_platform_owner)],
    db: Annotated[Session, Depends(get_db)],
) -> SubscriptionPlan:
    plan = db.get(SubscriptionPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found.")

    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(plan, field, val)

    db.commit()
    db.refresh(plan)
    return plan


# -----------------------------------------------------------------------------
# Subscription Activation & Billing
# -----------------------------------------------------------------------------
@router.post("/subscriptions/activate", response_model=SubscriptionResponse)
def activate_subscription(
    data: SubscriptionActivateRequest,
    current_admin: Annotated[User, Depends(require_platform_owner)],
    db: Annotated[Session, Depends(get_db)],
) -> Subscription:
    org = db.get(Organization, data.organization_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")

    plan = db.get(SubscriptionPlan, data.plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found.")

    duration_days = data.duration_days or (365 if data.billing_cycle == BillingCycle.ANNUAL else 30)
    now = datetime.now(timezone.utc)

    # Check for existing subscription to upgrade or extend
    existing_sub = db.execute(
        select(Subscription).where(Subscription.organization_id == org.id).order_by(Subscription.created_at.desc())
    ).scalar_one_or_none()

    if existing_sub:
        existing_sub.plan_id = plan.id
        existing_sub.status = SubscriptionStatus.ACTIVE
        existing_sub.billing_cycle = data.billing_cycle
        existing_sub.start_date = now
        existing_sub.end_date = now + timedelta(days=duration_days)
        existing_sub.activated_by_user_id = current_admin.id
        subscription = existing_sub
    else:
        subscription = Subscription(
            organization_id=org.id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE,
            billing_cycle=data.billing_cycle,
            start_date=now,
            end_date=now + timedelta(days=duration_days),
            auto_renew=True,
            activated_by_user_id=current_admin.id,
        )
        db.add(subscription)

    db.flush()

    # Record Payment Transaction
    amount = plan.annual_price if data.billing_cycle == BillingCycle.ANNUAL else plan.monthly_price
    payment = PaymentTransaction(
        organization_id=org.id,
        subscription_id=subscription.id,
        amount=amount,
        currency="INR",
        payment_mode=data.payment_mode,
        gateway_reference=data.gateway_reference or f"MANUAL-ACT-{uuid.uuid4().hex[:8].upper()}",
        status=PaymentStatus.VERIFIED,
        verified_at=now,
    )
    db.add(payment)

    # Audit event
    audit = AuditEvent(
        organization_id=org.id,
        actor_user_id=current_admin.id,
        actor_role=UserRole.PLATFORM_OWNER.value,
        event_type="SUBSCRIPTION_ACTIVATED",
        resource_type="SUBSCRIPTION",
        resource_id=subscription.id,
        action="ACTIVATE",
        metadata_json={
            "plan_code": plan.code,
            "billing_cycle": data.billing_cycle.value,
            "amount": float(amount),
        },
    )
    db.add(audit)

    db.commit()
    db.refresh(subscription)
    return subscription


@router.get("/subscriptions", response_model=list[SubscriptionResponse])
def list_subscriptions(
    _: Annotated[User, Depends(require_platform_owner)],
    db: Annotated[Session, Depends(get_db)],
) -> list[Subscription]:
    return list(db.execute(select(Subscription).order_by(Subscription.created_at.desc())).scalars().all())


@router.get("/audit-events")
def list_audit_events(
    _: Annotated[User, Depends(require_platform_owner)],
    db: Annotated[Session, Depends(get_db)],
) -> list[dict]:
    events = db.execute(select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(100)).scalars().all()
    return [
        {
            "id": str(e.id),
            "organization_id": str(e.organization_id),
            "actor_user_id": str(e.actor_user_id) if e.actor_user_id else None,
            "actor_role": e.actor_role,
            "event_type": e.event_type,
            "resource_type": e.resource_type,
            "resource_id": str(e.resource_id),
            "action": e.action,
            "metadata_json": e.metadata_json,
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]


@router.get("/coupons", response_model=list[CouponResponse])
def list_coupons(
    _: Annotated[User, Depends(require_platform_owner)],
    db: Annotated[Session, Depends(get_db)],
) -> list[DiscountCoupon]:
    return list(db.execute(select(DiscountCoupon).order_by(DiscountCoupon.created_at.desc())).scalars().all())


@router.post("/coupons", response_model=CouponResponse, status_code=status.HTTP_201_CREATED)
def create_coupon(
    data: CouponCreate,
    _: Annotated[User, Depends(require_platform_owner)],
    db: Annotated[Session, Depends(get_db)],
) -> DiscountCoupon:
    existing = db.execute(select(DiscountCoupon).where(DiscountCoupon.code == data.code.upper().strip())).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail=f"Coupon code '{data.code}' already exists.")

    coupon = DiscountCoupon(
        code=data.code.upper().strip(),
        description=data.description,
        discount_type=data.discount_type,
        discount_value=data.discount_value,
        applicable_plan_codes=data.applicable_plan_codes,
        max_redemptions=data.max_redemptions,
        current_redemptions=0,
        valid_until=data.valid_until,
        is_active=data.is_active,
    )
    db.add(coupon)
    db.commit()
    db.refresh(coupon)
    return coupon


@router.patch("/coupons/{coupon_id}", response_model=CouponResponse)
def update_coupon(
    coupon_id: uuid.UUID,
    data: CouponPatch,
    _: Annotated[User, Depends(require_platform_owner)],
    db: Annotated[Session, Depends(get_db)],
) -> DiscountCoupon:
    coupon = db.get(DiscountCoupon, coupon_id)
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found.")

    if data.description is not None:
        coupon.description = data.description
    if data.discount_type is not None:
        coupon.discount_type = data.discount_type
    if data.discount_value is not None:
        coupon.discount_value = data.discount_value
    if data.applicable_plan_codes is not None:
        coupon.applicable_plan_codes = data.applicable_plan_codes
    if data.max_redemptions is not None:
        coupon.max_redemptions = data.max_redemptions
    if data.valid_until is not None:
        coupon.valid_until = data.valid_until
    if data.is_active is not None:
        coupon.is_active = data.is_active

    db.commit()
    db.refresh(coupon)
    return coupon


@router.delete("/coupons/{coupon_id}")
def delete_coupon(
    coupon_id: uuid.UUID,
    _: Annotated[User, Depends(require_platform_owner)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    coupon = db.get(DiscountCoupon, coupon_id)
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found.")
    coupon.is_active = False
    db.commit()
    return {"message": f"Coupon '{coupon.code}' deactivated successfully."}


@router.get("/ai-status")
def get_ai_status(
    _: Annotated[User, Depends(require_platform_owner)],
) -> dict:
    import json
    import os
    from app.core.config import settings

    cache_dir = getattr(settings, "GNANI_CACHE_DIR", "./storage/gnani_cache")
    counter_file = os.path.join(cache_dir, "usage_counter.json")

    cached_entries_count = 0
    if os.path.exists(cache_dir):
        cached_entries_count = len([f for f in os.listdir(cache_dir) if f.endswith(".json") and f != "usage_counter.json"])

    usage_data = {"live_calls_count": 0, "max_allowed_calls": getattr(settings, "GNANI_MAX_LIVE_CALLS", 6), "credits_used_estimate": 0}
    if os.path.exists(counter_file):
        try:
            with open(counter_file, "r", encoding="utf-8") as f:
                usage_data = json.load(f)
        except Exception:
            pass

    return {
        "provider_mode": settings.AI_PROVIDER,
        "circuit_breaker_active": usage_data.get("live_calls_count", 0) >= usage_data.get("max_allowed_calls", 6),
        "live_calls_made": usage_data.get("live_calls_count", 0),
        "live_calls_cap": usage_data.get("max_allowed_calls", 6),
        "cached_entries": cached_entries_count,
        "cache_directory": cache_dir,
        "credit_safety_mode": "ACTIVE (5,000 credit boundary preserved)",
    }

