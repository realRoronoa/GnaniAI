import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from jose import JWTError, jwt

from app.core.config import settings

# Initialize Argon2id password hasher with secure defaults
_password_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64 MB
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return _password_hasher.hash(password)


# Alias for backward/forward compatibility
get_password_hash = hash_password


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against an Argon2id hash."""
    try:
        return _password_hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def create_access_token(
    user_id: str | uuid.UUID | None = None,
    role: str | None = None,
    organization_id: str | uuid.UUID | None = None,
    expires_delta: timedelta | None = None,
    custom_claims: dict[str, Any] | None = None,
    *,
    subject: str | uuid.UUID | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """
    Generate an authenticated JWT access token.
    Enforces claims: sub, role, org_id, type="access", jti, iat, exp.
    """
    sub_val = str(subject) if subject is not None else (str(user_id) if user_id is not None else "")
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.access_token_expire_minutes)

    payload: dict[str, Any] = {
        "sub": sub_val,
        "role": role,
        "org_id": str(organization_id) if organization_id else None,
        "type": "access",
        "jti": str(uuid.uuid4()),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    if custom_claims:
        payload.update(custom_claims)
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(
    user_id: str | uuid.UUID | None = None,
    expires_delta: timedelta | None = None,
    *,
    subject: str | uuid.UUID | None = None,
) -> str:
    """
    Generate a long-lived JWT refresh token.
    Enforces claims: sub, type="refresh", jti, iat, exp.
    """
    sub_val = str(subject) if subject is not None else (str(user_id) if user_id is not None else "")
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.refresh_token_expire_days)

    payload: dict[str, Any] = {
        "sub": sub_val,
        "type": "refresh",
        "jti": str(uuid.uuid4()),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }

    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and validate signature and expiry of a JWT token.
    """
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],
    )
