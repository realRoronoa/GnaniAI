from __future__ import annotations

import uuid
from datetime import date, datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, GUID, TimestampUUIDMixin
from app.models.enums import AppointmentStatus, AppointmentType

if TYPE_CHECKING:
    from app.models.tenant import Organization, OrganizationLocation, User
    from app.models.consultations_audio import Consultation


class Patient(Base, TimestampUUIDMixin):
    __tablename__ = "patients"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    patient_identifier: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    age_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gender: Mapped[str] = mapped_column(String(20), nullable=False)
    mobile_number: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    preferred_language: Mapped[str] = mapped_column(String(20), nullable=False, default="en-IN")
    allergies_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    allergy_verification_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="UNVERIFIED",
    )
    administrative_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    organization: Mapped[Organization] = relationship("Organization")
    appointments: Mapped[list[Appointment]] = relationship(
        "Appointment",
        back_populates="patient",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "patient_identifier", name="uq_org_patient_identifier"),
    )


class DoctorSchedule(Base, TimestampUUIDMixin):
    __tablename__ = "doctor_schedules"

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
    doctor_user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)  # 0 = Monday / 6 = Sunday
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    slot_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    organization: Mapped[Organization] = relationship("Organization")
    location: Mapped[OrganizationLocation] = relationship("OrganizationLocation")
    doctor: Mapped[User] = relationship("User")


class Appointment(Base, TimestampUUIDMixin):
    __tablename__ = "appointments"

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
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    appointment_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    scheduled_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    queue_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    appointment_type: Mapped[AppointmentType] = mapped_column(
        String(50),
        nullable=False,
        default=AppointmentType.SCHEDULED,
    )
    status: Mapped[AppointmentStatus] = mapped_column(
        String(50),
        nullable=False,
        default=AppointmentStatus.SCHEDULED,
        index=True,
    )
    reason_for_visit: Mapped[str | None] = mapped_column(Text, nullable=True)
    administrative_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    arrived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization: Mapped[Organization] = relationship("Organization")
    location: Mapped[OrganizationLocation] = relationship("OrganizationLocation")
    patient: Mapped[Patient] = relationship("Patient", back_populates="appointments")
    doctor: Mapped[User] = relationship("User", foreign_keys=[doctor_user_id])
    created_by: Mapped[User | None] = relationship("User", foreign_keys=[created_by_user_id])

