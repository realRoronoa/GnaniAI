from datetime import datetime, time
from decimal import Decimal
from typing import Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import BillingCycle, OrgStatus, UserRole


class OrganizationCreate(BaseModel):
    name: str = Field(..., max_length=255)
    org_type: str = Field(default="POLYCLINIC")
    contact_email: EmailStr
    contact_phone: str = Field(..., max_length=30)
    address: str | None = None
    registration_number: str | None = None
    settings_json: dict[str, Any] = Field(default_factory=dict)

    # Initial Org Admin credentials
    admin_full_name: str = Field(..., max_length=255)
    admin_email: EmailStr
    admin_password: str = Field(..., min_length=6)
    admin_phone: str | None = None


class PublicOrganizationRegisterRequest(BaseModel):
    name: str = Field(..., max_length=255)
    org_type: str = Field(default="CLINIC")
    contact_email: EmailStr
    contact_phone: str | None = None
    address: str | None = None
    admin_full_name: str = Field(..., max_length=255)
    admin_password: str | None = Field(default=None)
    requested_plan: str = Field(default="PROFESSIONAL")
    requested_billing_cycle: str = Field(default="MONTHLY")
    coupon_code: str | None = None


class OnboardingApprovalRequest(BaseModel):
    plan_id: UUID
    billing_cycle: BillingCycle = BillingCycle.MONTHLY
    duration_days: int = Field(default=30, ge=1)
    coupon_code: str | None = None
    custom_final_price_inr: Decimal | None = None
    admin_email: EmailStr
    admin_full_name: str
    temporary_password: str | None = None


class OnboardingApprovalResponse(BaseModel):
    organization_id: UUID
    organization_name: str
    status: OrgStatus
    subscription_id: UUID
    plan_code: str
    admin_user_id: UUID
    admin_email: str
    temporary_password: str
    message: str



class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    org_type: str
    contact_email: str
    contact_phone: str
    address: str | None
    registration_number: str | None
    status: OrgStatus
    settings_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrganizationStatusUpdate(BaseModel):
    status: OrgStatus


class OrganizationProfileUpdate(BaseModel):
    name: str | None = None
    contact_email: EmailStr | None = None
    contact_phone: str | None = None
    address: str | None = None
    settings_json: dict[str, Any] | None = None


class LocationCreate(BaseModel):
    name: str = Field(..., max_length=255)
    branch_code: str = Field(..., max_length=50)
    address: str | None = None
    phone: str | None = None


class LocationResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    branch_code: str
    address: str | None
    phone: str | None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DoctorCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., max_length=255)
    phone: str | None = None
    location_id: UUID | None = None
    specialization: str = Field(..., max_length=150)
    qualification: str = Field(..., max_length=255)
    registration_number: str = Field(..., max_length=100)
    consultation_room: str | None = None
    languages_spoken: str = Field(default="English, Hindi")


class DoctorResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    phone: str | None
    is_active: bool
    specialization: str
    qualification: str
    registration_number: str
    consultation_room: str | None
    languages_spoken: str
    location_id: UUID | None


class ReceptionistCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., max_length=255)
    phone: str | None = None
    location_id: UUID | None = None
    desk_identifier: str | None = None
    shift_notes: str | None = None


class ReceptionistResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    phone: str | None
    is_active: bool
    desk_identifier: str | None
    shift_notes: str | None
    location_id: UUID | None


class StaffOverviewResponse(BaseModel):
    doctors: list[DoctorResponse]
    receptionists: list[ReceptionistResponse]


class DoctorScheduleCreate(BaseModel):
    location_id: UUID
    doctor_user_id: UUID
    day_of_week: int = Field(..., ge=0, le=6)
    start_time: time
    end_time: time
    slot_duration_minutes: int = Field(default=15, ge=5, le=120)


class DoctorScheduleResponse(BaseModel):
    id: UUID
    organization_id: UUID
    location_id: UUID
    doctor_user_id: UUID
    day_of_week: int
    start_time: time
    end_time: time
    slot_duration_minutes: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class PlatformOverviewResponse(BaseModel):
    total_organizations: int
    active_organizations: int
    total_subscriptions: int
    active_subscriptions: int
    expired_subscriptions: int
    total_doctors: int
    total_receptionists: int
    total_consultations: int


class OrgDashboardResponse(BaseModel):
    organization: OrganizationResponse
    branches_count: int
    doctors_count: int
    receptionists_count: int
    subscription_status: str
    plan_name: str
    consultations_month_count: int
    quota_consultations: int
