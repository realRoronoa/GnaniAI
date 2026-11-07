from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base, GUID, TimestampUUIDMixin
from app.models.enums import BillingCycle, PaymentMode, PaymentStatus, SubscriptionStatus

if TYPE_CHECKING:
    from app.models.tenant import Organization, User


class SubscriptionPlan(Base, TimestampUUIDMixin):
    __tablename__ = "subscription_plans"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    monthly_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    annual_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    max_doctors: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    max_receptionists: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    max_branches: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    monthly_consultation_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=200)
    audio_storage_mb_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=1024)
    report_generation_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=200)
    included_features_json: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=list,
    )
    description: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    trial_days: Mapped[int] = mapped_column(Integer, nullable=False, default=14)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    subscriptions: Mapped[list[Subscription]] = relationship(
        "Subscription",
        back_populates="plan",
    )


class Subscription(Base, TimestampUUIDMixin):
    __tablename__ = "subscriptions"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("subscription_plans.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        String(50),
        nullable=False,
        default=SubscriptionStatus.TRIAL,
        index=True,
    )
    billing_cycle: Mapped[BillingCycle] = mapped_column(
        String(20),
        nullable=False,
        default=BillingCycle.MONTHLY,
    )
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    auto_renew: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    activated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    organization: Mapped[Organization] = relationship("Organization", back_populates="subscriptions")
    plan: Mapped[SubscriptionPlan] = relationship("SubscriptionPlan", back_populates="subscriptions")
    activated_by_user: Mapped[User | None] = relationship("User")
    transactions: Mapped[list[PaymentTransaction]] = relationship(
        "PaymentTransaction",
        back_populates="subscription",
    )
    usage_records: Mapped[list[UsageRecord]] = relationship(
        "UsageRecord",
        back_populates="subscription",
    )


class PaymentTransaction(Base, TimestampUUIDMixin):
    __tablename__ = "payment_transactions"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subscription_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("subscriptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="INR")
    payment_mode: Mapped[PaymentMode] = mapped_column(
        String(50),
        nullable=False,
        default=PaymentMode.DEVELOPMENT_MANUAL,
    )
    gateway_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[PaymentStatus] = mapped_column(
        String(50),
        nullable=False,
        default=PaymentStatus.PENDING,
        index=True,
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization: Mapped[Organization] = relationship("Organization")
    subscription: Mapped[Subscription | None] = relationship("Subscription", back_populates="transactions")


class UsageRecord(Base, TimestampUUIDMixin):
    __tablename__ = "usage_records"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subscription_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("subscriptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    period_month: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # e.g. "2026-11"
    consultations_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    audio_storage_bytes_used: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    reports_generated_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active_doctors_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active_receptionists_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active_branches_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    organization: Mapped[Organization] = relationship("Organization", back_populates="usage_records")
    subscription: Mapped[Subscription | None] = relationship("Subscription", back_populates="usage_records")

    __table_args__ = (
        UniqueConstraint("organization_id", "period_month", name="uq_org_usage_period"),
    )


class DiscountCoupon(Base, TimestampUUIDMixin):
    __tablename__ = "discount_coupons"

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    discount_type: Mapped[str] = mapped_column(String(20), nullable=False, default="PERCENTAGE")  # PERCENTAGE or FLAT_INR
    discount_value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    applicable_plan_codes: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=list,
    )
    max_redemptions: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    current_redemptions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


