import uuid
from starlette.testclient import TestClient

from app.core.config import settings
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.db.base import Base, TimestampUUIDMixin
from app.main import app


def test_argon2id_hashing() -> None:
    raw_secret = "SecureClinicPassword@2026!"
    hashed = hash_password(raw_secret)
    assert hashed.startswith("$argon2id$")
    assert verify_password(raw_secret, hashed) is True
    assert verify_password("WrongPassword123", hashed) is False


def test_jwt_access_token_claims() -> None:
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    role = "DOCTOR"

    token = create_access_token(user_id=user_id, role=role, organization_id=org_id)
    claims = decode_token(token)

    assert claims["sub"] == str(user_id)
    assert claims["role"] == role
    assert claims["org_id"] == str(org_id)
    assert claims["type"] == "access"
    assert "jti" in claims
    assert "exp" in claims
    assert "iat" in claims


def test_jwt_refresh_token_claims() -> None:
    user_id = uuid.uuid4()
    token = create_refresh_token(user_id=user_id)
    claims = decode_token(token)

    assert claims["sub"] == str(user_id)
    assert claims["type"] == "refresh"
    assert "jti" in claims


def test_timestamp_uuid_mixin_definition() -> None:
    class DummyModel(Base, TimestampUUIDMixin):
        __tablename__ = "dummy_test_table"

    assert hasattr(DummyModel, "id")
    assert hasattr(DummyModel, "created_at")
    assert hasattr(DummyModel, "updated_at")


def test_health_check_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == settings.app_name
    assert data["ai_provider_mode"] == settings.ai_provider_mode
    assert data["payment_mode"] == settings.payment_mode
    assert "timestamp" in data

