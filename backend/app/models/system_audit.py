from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base, GUID, TimestampUUIDMixin, utc_now
from app.models.enums import DeliveryChannel, JobStatus, JobType

if TYPE_CHECKING:
    from app.models.tenant import Organization, User
    from app.models.patients_appointments import Patient
    from app.models.consultations_audio import Consultation
    from app.models.clinical_reports import PdfAsset


class ProcessingJob(Base, TimestampUUIDMixin):
    __tablename__ = "processing_jobs"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    consultation_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("consultations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_type: Mapped[JobType] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    celery_task_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    provider_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[JobStatus] = mapped_column(
        String(50),
        nullable=False,
        default=JobStatus.QUEUED,
        index=True,
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization: Mapped[Organization] = relationship("Organization")
    consultation: Mapped[Consultation] = relationship("Consultation")


class AuditEvent(Base, TimestampUUIDMixin):
    __tablename__ = "audit_events"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    actor_role: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    # Relationships
    organization: Mapped[Organization] = relationship("Organization")
    actor_user: Mapped[User | None] = relationship("User")


class SecureShareGrant(Base, TimestampUUIDMixin):
    __tablename__ = "secure_share_grants"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    consultation_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("consultations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pdf_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("pdf_assets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    shared_by_user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    delivery_channel: Mapped[DeliveryChannel] = mapped_column(
        String(50),
        nullable=False,
        default=DeliveryChannel.MANUAL_WHATSAPP,
    )
    recipient_contact: Mapped[str] = mapped_column(String(100), nullable=False)
    manually_confirmed_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    # Relationships
    organization: Mapped[Organization] = relationship("Organization")
    consultation: Mapped[Consultation] = relationship("Consultation")
    patient: Mapped[Patient] = relationship("Patient")
    pdf_asset: Mapped[PdfAsset | None] = relationship("PdfAsset")
    shared_by_user: Mapped[User] = relationship("User")

