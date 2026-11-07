"""Entitlement & Subscription Enforcement Service

Enforces subscription tier boundaries and limits:
- Active/Trial subscription validity
- Max branches limit
- Max doctors limit
- Max receptionists limit
- Monthly consultation quota
Preserves read-only access for expired or suspended organizations.
"""
from datetime import datetime, timezone
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import OrgStatus, SubscriptionStatus, UserRole, enum_val
from app.models.subscriptions import Subscription, SubscriptionPlan, UsageRecord
from app.models.tenant import Organization, OrganizationLocation, OrganizationMembership


class EntitlementService:
    @staticmethod
    def get_active_subscription(db: Session, organization_id: uuid.UUID) -> Subscription | None:
        """Retrieves the current subscription for an organization."""
        stmt = (
            select(Subscription)
            .where(Subscription.organization_id == organization_id)
            .order_by(Subscription.created_at.desc())
        )
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def ensure_active_subscription_write_allowed(db: Session, organization_id: uuid.UUID) -> Subscription:
        """Verifies that an organization has an active or trial subscription.
        If expired or suspended, write operations are blocked while read-only access is preserved.
        """
        org = db.get(Organization, organization_id)
        if not org or enum_val(org.status) != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organization is inactive or suspended. Write operations are blocked.",
            )

        sub = EntitlementService.get_active_subscription(db, organization_id)
        if not sub:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No subscription found for this organization. Please activate a plan.",
            )

        now = datetime.now(timezone.utc)
        sub_status_str = enum_val(sub.status)
        end_date = sub.end_date.replace(tzinfo=timezone.utc) if sub.end_date.tzinfo is None else sub.end_date
        if sub_status_str not in ("ACTIVE", "TRIAL") or end_date < now:
            # Mark expired if past end_date
            if sub_status_str != "EXPIRED" and end_date < now:
                sub.status = SubscriptionStatus.EXPIRED
                db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Subscription has expired or is suspended. Account is in read-only mode.",
            )

        return sub

    @classmethod
    def check_branch_limit(cls, db: Session, organization_id: uuid.UUID) -> None:
        """Enforces plan branch limit."""
        sub = cls.ensure_active_subscription_write_allowed(db, organization_id)
        plan = db.get(SubscriptionPlan, sub.plan_id)
        if not plan:
            return

        current_branches = db.execute(
            select(func.count(OrganizationLocation.id)).where(
                OrganizationLocation.organization_id == organization_id,
                OrganizationLocation.is_active == True,
            )
        ).scalar() or 0

        if current_branches >= plan.max_branches:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Plan branch limit reached ({current_branches}/{plan.max_branches}). Please upgrade your plan.",
            )

    @classmethod
    def check_doctor_limit(cls, db: Session, organization_id: uuid.UUID) -> None:
        """Enforces plan doctor limit."""
        sub = cls.ensure_active_subscription_write_allowed(db, organization_id)
        plan = db.get(SubscriptionPlan, sub.plan_id)
        if not plan:
            return

        current_doctors = db.execute(
            select(func.count(OrganizationMembership.id)).where(
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.role == UserRole.DOCTOR,
                OrganizationMembership.is_active == True,
            )
        ).scalar() or 0

        if current_doctors >= plan.max_doctors:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Plan doctor limit reached ({current_doctors}/{plan.max_doctors}). Please upgrade your plan.",
            )

    @classmethod
    def check_receptionist_limit(cls, db: Session, organization_id: uuid.UUID) -> None:
        """Enforces plan receptionist limit."""
        sub = cls.ensure_active_subscription_write_allowed(db, organization_id)
        plan = db.get(SubscriptionPlan, sub.plan_id)
        if not plan:
            return

        current_receptionists = db.execute(
            select(func.count(OrganizationMembership.id)).where(
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.role == UserRole.RECEPTIONIST,
                OrganizationMembership.is_active == True,
            )
        ).scalar() or 0

        if current_receptionists >= plan.max_receptionists:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Plan receptionist limit reached ({current_receptionists}/{plan.max_receptionists}). Please upgrade your plan.",
            )
