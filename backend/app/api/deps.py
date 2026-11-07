import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db
from app.models.enums import OrgStatus, UserRole
from app.models.tenant import Organization, OrganizationMembership, User

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type for API access.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token subject missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID format in token.",
        )

    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated or not found.",
        )

    return user


def require_platform_owner(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Restricts access strictly to Platform Owners (Super Admins)."""
    if not current_user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform Owner access required.",
        )
    return current_user


def get_current_membership(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> OrganizationMembership:
    """Resolves the user's active organization membership and verifies tenant status."""
    stmt = (
        select(OrganizationMembership)
        .where(
            OrganizationMembership.user_id == current_user.id,
            OrganizationMembership.is_active == True,
        )
        .limit(1)
    )
    membership = db.execute(stmt).scalar_one_or_none()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have an active organization membership.",
        )

    # Verify organization status
    org = db.get(Organization, membership.organization_id)
    if not org or org.status != OrgStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization account is inactive, suspended, or deactivated.",
        )

    return membership


def get_current_tenant_org_id(
    membership: Annotated[OrganizationMembership, Depends(get_current_membership)],
) -> uuid.UUID:
    """Returns the authenticated user's organization_id for multi-tenant isolation."""
    return membership.organization_id


def require_org_admin(
    current_user: Annotated[User, Depends(get_current_user)],
    membership: Annotated[OrganizationMembership, Depends(get_current_membership)],
) -> OrganizationMembership:
    """Ensures caller has ORG_ADMIN role within their tenant organization."""
    if membership.role != UserRole.ORG_ADMIN and not current_user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization Administrator privileges required.",
        )
    return membership


def require_receptionist(
    membership: Annotated[OrganizationMembership, Depends(get_current_membership)],
) -> OrganizationMembership:
    """Ensures caller has RECEPTIONIST or ORG_ADMIN role."""
    if membership.role not in (UserRole.RECEPTIONIST, UserRole.ORG_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Receptionist or Organization Administrator privileges required.",
        )
    return membership


def require_doctor(
    membership: Annotated[OrganizationMembership, Depends(get_current_membership)],
) -> OrganizationMembership:
    """Ensures caller has DOCTOR role."""
    if membership.role != UserRole.DOCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Doctor privileges required.",
        )
    return membership


def require_org_member(
    membership: Annotated[OrganizationMembership, Depends(get_current_membership)],
) -> OrganizationMembership:
    """Allows any active staff member (ORG_ADMIN, RECEPTIONIST, DOCTOR) within the tenant organization."""
    return membership


