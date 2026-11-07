from datetime import datetime, timezone
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import create_access_token, create_refresh_token, decode_token, verify_password
from app.db.session import get_db
from app.models.enums import OrgStatus, UserRole
from app.models.tenant import DoctorProfile, Organization, OrganizationMembership, ReceptionistProfile, User
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserMeResponse,
    UserProfileSummary,
)

router = APIRouter(prefix="/auth", tags=["Authentication & Identity"])


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    user = db.execute(select(User).where(User.email == request.email)).scalar_one_or_none()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact your organization administrator.",
        )

    # Determine user role, organization, and location
    role = UserRole.PLATFORM_OWNER if user.is_super_admin else None
    org_id = None
    location_id = None

    if not user.is_super_admin:
        membership = db.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user.id,
                OrganizationMembership.is_active == True,
            )
        ).scalar_one_or_none()

        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User has no active organization membership.",
            )

        org = db.get(Organization, membership.organization_id)
        if not org or org.status != OrgStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organization account is inactive, suspended, or deactivated.",
            )

        role = membership.role
        org_id = membership.organization_id
        location_id = membership.location_id

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    role_val = role.value if hasattr(role, "value") else (str(role) if role else None)

    extra_claims = {
        "role": role_val,
        "org_id": str(org_id) if org_id else None,
        "location_id": str(location_id) if location_id else None,
        "is_super_admin": user.is_super_admin,
    }

    access_token = create_access_token(subject=str(user.id), extra_claims=extra_claims)
    refresh_token = create_refresh_token(subject=str(user.id))

    parsed_role = UserRole(role_val) if role_val else UserRole.PLATFORM_OWNER

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserProfileSummary(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            phone=user.phone,
            role=parsed_role,
            organization_id=org_id,
            location_id=location_id,
            is_super_admin=user.is_super_admin,
        ),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(request: RefreshTokenRequest, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    try:
        payload = decode_token(request.refresh_token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is not a refresh token.",
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing user subject.",
        )

    user = db.get(User, uuid.UUID(user_id_str))
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive or not found.",
        )

    role = UserRole.PLATFORM_OWNER if user.is_super_admin else None
    org_id = None
    location_id = None

    if not user.is_super_admin:
        membership = db.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user.id,
                OrganizationMembership.is_active == True,
            )
        ).scalar_one_or_none()

        if membership:
            role = membership.role
            org_id = membership.organization_id
            location_id = membership.location_id

    role_val = role.value if hasattr(role, "value") else (str(role) if role else None)

    extra_claims = {
        "role": role_val,
        "org_id": str(org_id) if org_id else None,
        "location_id": str(location_id) if location_id else None,
        "is_super_admin": user.is_super_admin,
    }

    new_access_token = create_access_token(subject=str(user.id), extra_claims=extra_claims)
    new_refresh_token = create_refresh_token(subject=str(user.id))

    parsed_role = UserRole(role_val) if role_val else UserRole.PLATFORM_OWNER

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        user=UserProfileSummary(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            phone=user.phone,
            role=parsed_role,
            organization_id=org_id,
            location_id=location_id,
            is_super_admin=user.is_super_admin,
        ),
    )


@router.post("/logout")
def logout(request: LogoutRequest) -> dict[str, str]:
    # In a stateless JWT architecture, tokens expire naturally; if blacklist is enabled, jti can be recorded.
    return {"message": "Logged out successfully."}


@router.post("/password/forgot")
def forgot_password(request: ForgotPasswordRequest) -> dict[str, str]:
    """Safe dev password reset instructions logger without account enumeration."""
    return {
        "message": "If an account exists, password reset instructions have been logged for your organization administrator."
    }


@router.get("/me", response_model=UserMeResponse)
def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> UserMeResponse:
    role = UserRole.PLATFORM_OWNER if current_user.is_super_admin else None
    org_id = None
    location_id = None
    doctor_data = None
    receptionist_data = None

    if not current_user.is_super_admin:
        membership = db.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == current_user.id,
                OrganizationMembership.is_active == True,
            )
        ).scalar_one_or_none()

        if membership:
            role = membership.role
            org_id = membership.organization_id
            location_id = membership.location_id

        if role == UserRole.DOCTOR:
            doc = db.execute(
                select(DoctorProfile).where(DoctorProfile.user_id == current_user.id)
            ).scalar_one_or_none()
            if doc:
                doctor_data = {
                    "specialization": doc.specialization,
                    "qualification": doc.qualification,
                    "registration_number": doc.registration_number,
                    "consultation_room": doc.consultation_room,
                    "languages_spoken": doc.languages_spoken,
                }
        elif role == UserRole.RECEPTIONIST:
            rec = db.execute(
                select(ReceptionistProfile).where(ReceptionistProfile.user_id == current_user.id)
            ).scalar_one_or_none()
            if rec:
                receptionist_data = {
                    "desk_identifier": rec.desk_identifier,
                    "shift_notes": rec.shift_notes,
                }

    parsed_role = UserRole(role) if role else UserRole.PLATFORM_OWNER

    return UserMeResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        phone=current_user.phone,
        is_super_admin=current_user.is_super_admin,
        is_active=current_user.is_active,
        role=parsed_role,
        organization_id=org_id,
        location_id=location_id,
        doctor_profile=doctor_data,
        receptionist_profile=receptionist_data,
    )
