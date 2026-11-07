import os
from typing import Literal
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core Application Settings
    app_name: str = "ArogyaScribe"
    app_env: Literal["development", "testing", "staging", "production"] = "development"
    log_level: str = "INFO"
    api_port: int = 8000

    # Networking & CORS
    allowed_origins: list[str] | str = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
    ]

    # Database (PostgreSQL 16 default, SQLite fallback supported for testing)
    database_url: str = (
        "postgresql+psycopg2://arogyascribe:local_dev_password_change_in_prod@localhost:5432/arogyascribe"
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: str | None) -> str:
        if not v:
            return "sqlite:///demo.db"
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+psycopg2://", 1)
        if v.startswith("postgresql://") and not v.startswith("postgresql+psycopg2://"):
            return v.replace("postgresql://", "postgresql+psycopg2://", 1)
        return v

    # Redis 7 & Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # S3 / MinIO Private Storage
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadminpassword"
    s3_bucket_name: str = "arogyascribe-private"
    s3_region: str = "us-east-1"
    s3_presigned_expiry_seconds: int = 3600

    # JWT Authentication & Cryptography
    secret_key: str = "insecure-local-dev-secret-key-change-in-production-minimum-32-chars"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # AI Pipeline Configuration
    ai_provider_mode: Literal["mock", "gnani"] = "mock"
    gnani_api_key: str = ""
    gnani_base_url: str = "https://api.vachana.ai"
    gnani_stt_model: str = "prisma-v2.5"
    gnani_llm_model: str = "evon-v3.3"
    gnani_tts_model: str = "timbre-v2.5"
    gnani_tts_voice: str = "Nalini"
    gnani_max_live_calls: int = 6
    gnani_cache_dir: str = "./storage/gnani_cache"

    @property
    def AI_PROVIDER(self) -> str:
        return self.ai_provider_mode

    @property
    def GNANI_MAX_LIVE_CALLS(self) -> int:
        return self.gnani_max_live_calls

    @property
    def GNANI_CACHE_DIR(self) -> str:
        return self.gnani_cache_dir

    # Billing & Payments
    payment_mode: Literal["development_manual", "razorpay"] = "development_manual"
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""

    # Clinical Defaults
    default_language: str = "hi-IN"
    demo_doctor_name: str = "Dr. Demo"

    # Super Admin & Demonstration Account Security Credentials
    superadmin_email: str = "superadmin@arogyascribe.in"
    superadmin_initial_password: str = "Admin@12345"
    owner_notification_email: str = "owner@arogyascribe.in"
    demo_org_admin_password: str = "OrgAdmin@123"
    demo_receptionist_password: str = "Reception@123"
    demo_doctor_password: str = "Doctor@123"

    # SMTP Email Notification Service
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@arogyascribe.in"

    @property
    def SUPERADMIN_EMAIL(self) -> str:
        return self.superadmin_email

    @property
    def SUPERADMIN_INITIAL_PASSWORD(self) -> str:
        return self.superadmin_initial_password

    @property
    def OWNER_NOTIFICATION_EMAIL(self) -> str:
        return self.owner_notification_email

    @property
    def DEMO_ORG_ADMIN_PASSWORD(self) -> str:
        return self.demo_org_admin_password

    @property
    def DEMO_RECEPTIONIST_PASSWORD(self) -> str:
        return self.demo_receptionist_password

    @property
    def DEMO_DOCTOR_PASSWORD(self) -> str:
        return self.demo_doctor_password

    @property
    def SMTP_HOST(self) -> str:
        return self.smtp_host

    @property
    def SMTP_PORT(self) -> int:
        return self.smtp_port

    @property
    def SMTP_USER(self) -> str:
        return self.smtp_user

    @property
    def SMTP_PASSWORD(self) -> str:
        return self.smtp_password

    @property
    def SMTP_FROM_EMAIL(self) -> str:
        return self.smtp_from_email

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


settings = Settings()

