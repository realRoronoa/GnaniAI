from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import BillingCycle, PaymentMode, SubscriptionStatus


class PlanCreate(BaseModel):
    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=50)
    description: str | None = Field(default=None, max_length=255)
    monthly_price: Decimal = Field(..., ge=0)
    annual_price: Decimal = Field(..., ge=0)
    max_doctors: int = Field(..., ge=1)
    max_receptionists: int = Field(..., ge=0)
    max_branches: int = Field(..., ge=1)
    monthly_consultation_limit: int = Field(..., ge=1)
    audio_storage_mb_limit: int = Field(..., ge=100)
    report_generation_limit: int = Field(..., ge=1)
    included_features_json: list[str] = Field(default_factory=list)
    duration_days: int = Field(default=30, ge=1)
    trial_days: int = Field(default=14, ge=0)


class PlanPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    monthly_price: Decimal | None = None
    annual_price: Decimal | None = None
    max_doctors: int | None = None
    max_receptionists: int | None = None
    max_branches: int | None = None
    monthly_consultation_limit: int | None = None
    audio_storage_mb_limit: int | None = None
    report_generation_limit: int | None = None
    included_features_json: list[str] | None = None
    is_active: bool | None = None


class PlanResponse(BaseModel):
    id: UUID
    name: str
    code: str
    description: str | None = None
    monthly_price: Decimal
    annual_price: Decimal
    max_doctors: int
    max_receptionists: int
    max_branches: int
    monthly_consultation_limit: int
    audio_storage_mb_limit: int
    report_generation_limit: int
    included_features_json: list[str]
    duration_days: int
    trial_days: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubscriptionActivateRequest(BaseModel):
    organization_id: UUID
    plan_id: UUID
    billing_cycle: BillingCycle = BillingCycle.MONTHLY
    payment_mode: PaymentMode = PaymentMode.DEVELOPMENT_MANUAL
    gateway_reference: str | None = None
    duration_days: int | None = None


class SubscriptionResponse(BaseModel):
    id: UUID
    organization_id: UUID
    plan_id: UUID
    status: SubscriptionStatus
    billing_cycle: BillingCycle
    start_date: datetime
    end_date: datetime
    auto_renew: bool
    plan: PlanResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class OrgSubscriptionOverview(BaseModel):
    subscription_id: UUID
    plan_name: str
    plan_code: str
    status: SubscriptionStatus
    start_date: datetime
    end_date: datetime
    days_remaining: int
    is_active: bool
    limits: dict
    current_usage: dict


class CouponCreate(BaseModel):
    code: str = Field(..., max_length=50)
    description: str | None = Field(default=None, max_length=255)
    discount_type: str = Field(default="PERCENTAGE")
    discount_value: Decimal = Field(..., ge=0)
    applicable_plan_codes: list[str] = Field(default_factory=list)
    max_redemptions: int = Field(default=100, ge=1)
    valid_until: datetime | None = None
    is_active: bool = True


class CouponPatch(BaseModel):
    description: str | None = None
    discount_type: str | None = None
    discount_value: Decimal | None = None
    applicable_plan_codes: list[str] | None = None
    max_redemptions: int | None = None
    valid_until: datetime | None = None
    is_active: bool | None = None


class CouponResponse(BaseModel):
    id: UUID
    code: str
    description: str | None = None
    discount_type: str
    discount_value: Decimal
    applicable_plan_codes: list[str]
    max_redemptions: int
    current_redemptions: int
    valid_until: datetime | None = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ValidateCouponRequest(BaseModel):
    coupon_code: str
    plan_code: str


class ValidateCouponResponse(BaseModel):
    valid: bool
    coupon_code: str
    discount_type: str = "NONE"
    discount_value: Decimal = Decimal("0.00")
    discount_amount_monthly: Decimal = Decimal("0.00")
    discount_amount_annual: Decimal = Decimal("0.00")
    final_price_monthly: Decimal = Decimal("0.00")
    final_price_annual: Decimal = Decimal("0.00")
    message: str

