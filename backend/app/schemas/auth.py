from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field

from app.models.enums import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)


class UserProfileSummary(BaseModel):
    id: UUID
    email: str
    full_name: str
    phone: str | None = None
    role: UserRole
    organization_id: UUID | None = None
    location_id: UUID | None = None
    is_super_admin: bool = False


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserProfileSummary


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class UserMeResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    phone: str | None
    is_super_admin: bool
    is_active: bool
    role: UserRole
    organization_id: UUID | None
    location_id: UUID | None
    doctor_profile: dict | None = None
    receptionist_profile: dict | None = None

