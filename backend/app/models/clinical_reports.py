from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base, GUID, TimestampUUIDMixin, utc_now
from app.models.enums import (
    CertaintyStatus,
    DoctorReviewStatus,
    PdfType,
    ProvenanceType,
    ReportStatus,
    ReportType,
)

if TYPE_CHECKING:
    from app.models.tenant import Organization, User
    from app.models.consultations_audio import Consultation, TranscriptSegment


class ClinicalFact(Base, TimestampUUIDMixin):
    __tablename__ = "clinical_facts"

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
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    fact_key: Mapped[str] = mapped_column(String(150), nullable=False)
    fact_value: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )
    source_speaker: Mapped[str] = mapped_column(String(50), nullable=False, default="PATIENT")
    provenance_type: Mapped[ProvenanceType] = mapped_column(
        String(50),
        nullable=False,
        default=ProvenanceType.AI_EXTRACTED,
    )
    certainty_status: Mapped[CertaintyStatus] = mapped_column(
        String(50),
        nullable=False,
        default=CertaintyStatus.VERIFIED,
    )
    ai_extraction_status: Mapped[str] = mapped_column(String(50), nullable=False, default="SUCCESS")
    doctor_review_status: Mapped[DoctorReviewStatus] = mapped_column(
        String(50),
        nullable=False,
        default=DoctorReviewStatus.PENDING,
        index=True,
    )
    validation_flags_json: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=list,
    )

    # Relationships
    organization: Mapped[Organization] = relationship("Organization")
    consultation: Mapped[Consultation] = relationship("Consultation", back_populates="clinical_facts")
    evidence_links: Mapped[list[ClinicalFactEvidence]] = relationship(
        "ClinicalFactEvidence",
        back_populates="clinical_fact",
        cascade="all, delete-orphan",
    )


class ClinicalFactEvidence(Base, TimestampUUIDMixin):
    __tablename__ = "clinical_fact_evidence"

    clinical_fact_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("clinical_facts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    transcript_segment_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("transcript_segments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    evidence_quotation: Mapped[str] = mapped_column(Text, nullable=False)
    start_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    end_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    clinical_fact: Mapped[ClinicalFact] = relationship("ClinicalFact", back_populates="evidence_links")
    transcript_segment: Mapped[TranscriptSegment] = relationship("TranscriptSegment")


class MedicationInstruction(Base, TimestampUUIDMixin):
    __tablename__ = "medication_instructions"

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
    medication_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    strength: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dosage: Mapped[str | None] = mapped_column(String(100), nullable=True)
    route: Mapped[str] = mapped_column(String(50), nullable=False, default="ORAL")
    frequency: Mapped[str | None] = mapped_column(String(100), nullable=True)
    duration: Mapped[str | None] = mapped_column(String(100), nullable=True)
    special_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_historical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    uncertainty_flags_json: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=list,
    )
    doctor_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verified_by_doctor_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    organization: Mapped[Organization] = relationship("Organization")
    consultation: Mapped[Consultation] = relationship("Consultation", back_populates="medication_instructions")
    verified_by_doctor: Mapped[User | None] = relationship("User")


class Report(Base, TimestampUUIDMixin):
    __tablename__ = "reports"

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
    report_type: Mapped[ReportType] = mapped_column(
        String(50),
        nullable=False,
        default=ReportType.DOCTOR_CLINICAL,
        index=True,
    )
    current_status: Mapped[ReportStatus] = mapped_column(
        String(50),
        nullable=False,
        default=ReportStatus.AI_GENERATED_DRAFT,
        index=True,
    )
    current_version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    target_language: Mapped[str] = mapped_column(String(20), nullable=False, default="en-IN")

    # Relationships
    organization: Mapped[Organization] = relationship("Organization")
    consultation: Mapped[Consultation] = relationship("Consultation", back_populates="reports")
    versions: Mapped[list[ReportVersion]] = relationship(
        "ReportVersion",
        back_populates="report",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("consultation_id", "report_type", name="uq_consultation_report_type"),
    )


class ReportVersion(Base, TimestampUUIDMixin):
    __tablename__ = "report_versions"

    report_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    consultation_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("consultations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ReportStatus] = mapped_column(
        String(50),
        nullable=False,
        default=ReportStatus.AI_GENERATED_DRAFT,
        index=True,
    )
    structured_content_json: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )
    rendered_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)

    # Relationships
    report: Mapped[Report] = relationship("Report", back_populates="versions")
    created_by_user: Mapped[User | None] = relationship("User")

    __table_args__ = (
        UniqueConstraint("report_id", "version_number", name="uq_report_version_number"),
    )


class ReportApproval(Base, TimestampUUIDMixin):
    __tablename__ = "report_approvals"

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
    report_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    report_version_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("report_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    approved_by_doctor_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    approval_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    signature_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    # Relationships
    organization: Mapped[Organization] = relationship("Organization")
    report: Mapped[Report] = relationship("Report")
    report_version: Mapped[ReportVersion] = relationship("ReportVersion")
    approved_by_doctor: Mapped[User] = relationship("User")


class PdfAsset(Base, TimestampUUIDMixin):
    __tablename__ = "pdf_assets"

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
    report_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("reports.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    report_version_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("report_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    pdf_type: Mapped[PdfType] = mapped_column(
        String(50),
        nullable=False,
        default=PdfType.DOCTOR_REPORT_PDF,
        index=True,
    )
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    # Relationships
    organization: Mapped[Organization] = relationship("Organization")

