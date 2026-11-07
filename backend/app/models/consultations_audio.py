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
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base, GUID, TimestampUUIDMixin, utc_now
from app.models.enums import (
    AudioUploadStatus,
    ConsultationStatus,
    SpeakerLabel,
    TranscriptSourceType,
)

if TYPE_CHECKING:
    from app.models.tenant import Organization, OrganizationLocation, User
    from app.models.patients_appointments import Patient, Appointment
    from app.models.clinical_reports import (
        ClinicalFact,
        MedicationInstruction,
        Report,
        PdfAsset,
    )


class ConsentRecord(Base, TimestampUUIDMixin):
    __tablename__ = "consent_records"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    consultation_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("consultations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    recorded_by_doctor_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    purpose: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="CLINICAL_DOCUMENTATION_AND_AI_ASSISTANCE",
    )
    language: Mapped[str] = mapped_column(String(20), nullable=False, default="en-IN")
    consent_wording_version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0")
    consent_text_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    is_granted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    withdrawal_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    organization: Mapped[Organization] = relationship("Organization")
    patient: Mapped[Patient] = relationship("Patient")
    recorded_by_doctor: Mapped[User] = relationship("User")


class Consultation(Base, TimestampUUIDMixin):
    __tablename__ = "consultations"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("organization_locations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("appointments.id", ondelete="SET NULL"),
        unique=True,
        nullable=True,
        index=True,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    doctor_user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[ConsultationStatus] = mapped_column(
        String(50),
        nullable=False,
        default=ConsultationStatus.SETUP,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    chief_complaint_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    longitudinal_comparison_json: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )

    # Relationships
    organization: Mapped[Organization] = relationship("Organization")
    location: Mapped[OrganizationLocation] = relationship("OrganizationLocation")
    appointment: Mapped[Appointment | None] = relationship("Appointment")
    patient: Mapped[Patient] = relationship("Patient")
    doctor: Mapped[User] = relationship("User")

    audio_assets: Mapped[list[AudioAsset]] = relationship(
        "AudioAsset",
        back_populates="consultation",
        cascade="all, delete-orphan",
    )
    transcript_versions: Mapped[list[TranscriptVersion]] = relationship(
        "TranscriptVersion",
        back_populates="consultation",
        cascade="all, delete-orphan",
    )
    clinical_facts: Mapped[list[ClinicalFact]] = relationship(
        "ClinicalFact",
        back_populates="consultation",
        cascade="all, delete-orphan",
    )
    medication_instructions: Mapped[list[MedicationInstruction]] = relationship(
        "MedicationInstruction",
        back_populates="consultation",
        cascade="all, delete-orphan",
    )
    reports: Mapped[list[Report]] = relationship(
        "Report",
        back_populates="consultation",
        cascade="all, delete-orphan",
    )


class AudioAsset(Base, TimestampUUIDMixin):
    __tablename__ = "audio_assets"

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
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False, default="audio/wav")
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    duration_seconds: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    upload_status: Mapped[AudioUploadStatus] = mapped_column(
        String(50),
        nullable=False,
        default=AudioUploadStatus.PENDING,
        index=True,
    )

    # Relationships
    organization: Mapped[Organization] = relationship("Organization")
    consultation: Mapped[Consultation] = relationship("Consultation", back_populates="audio_assets")


class TranscriptVersion(Base, TimestampUUIDMixin):
    __tablename__ = "transcript_versions"

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
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    source_type: Mapped[TranscriptSourceType] = mapped_column(
        String(50),
        nullable=False,
        default=TranscriptSourceType.AI_PRISMA,
    )
    full_text: Mapped[str] = mapped_column(Text, nullable=False)
    original_ai_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    language_detected: Mapped[str] = mapped_column(String(20), nullable=False, default="en-IN")
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    organization: Mapped[Organization] = relationship("Organization")
    consultation: Mapped[Consultation] = relationship("Consultation", back_populates="transcript_versions")
    segments: Mapped[list[TranscriptSegment]] = relationship(
        "TranscriptSegment",
        back_populates="transcript_version",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("consultation_id", "version_number", name="uq_consultation_transcript_version"),
    )


class TranscriptSegment(Base, TimestampUUIDMixin):
    __tablename__ = "transcript_segments"

    transcript_version_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("transcript_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    consultation_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("consultations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    speaker_label: Mapped[SpeakerLabel] = mapped_column(
        String(50),
        nullable=False,
        default=SpeakerLabel.UNKNOWN,
    )
    start_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    end_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    corrected_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False, default=Decimal("1.000"))

    # Relationships
    transcript_version: Mapped[TranscriptVersion] = relationship("TranscriptVersion", back_populates="segments")

