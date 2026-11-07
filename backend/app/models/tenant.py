from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base, GUID, TimestampUUIDMixin
from app.models.enums import OrgStatus, UserRole

if TYPE_CHECKING:
    from app.models.subscriptions import Subscription, UsageRecord
    from app.models.patients_appointments import Patient, Appointment, DoctorSchedule
    from app.models.consultations_audio import Consultation


class Organization(Base, TimestampUUIDMixin):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    org_type: Mapped[str] = mapped_column(String(100), nullable=False, default="POLYCLINIC")
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(30), nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    registration_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[OrgStatus] = mapped_column(String(50), nullable=False, default=OrgStatus.ACTIVE, index=True)
    settings_json: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )

    # Relationships
    locations: Mapped[list[OrganizationLocation]] = relationship(
        "OrganizationLocation",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    memberships: Mapped[list[OrganizationMembership]] = relationship(
        "OrganizationMembership",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    subscriptions: Mapped[list[Subscription]] = relationship(
        "Subscription",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    usage_records: Mapped[list[UsageRecord]] = relationship(
        "UsageRecord",
        back_populates="organization",
        cascade="all, delete-orphan",
    )


class OrganizationLocation(Base, TimestampUUIDMixin):
    __tablename__ = "organization_locations"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    branch_code: Mapped[str] = mapped_column(String(50), nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    organization: Mapped[Organization] = relationship("Organization", back_populates="locations")

    __table_args__ = (
        UniqueConstraint("organization_id", "branch_code", name="uq_org_location_branch_code"),
    )


class User(Base, TimestampUUIDMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    is_super_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    memberships: Mapped[list[OrganizationMembership]] = relationship(
        "OrganizationMembership",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    doctor_profile: Mapped[DoctorProfile | None] = relationship(
        "DoctorProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    receptionist_profile: Mapped[ReceptionistProfile | None] = relationship(
        "ReceptionistProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )


class OrganizationMembership(Base, TimestampUUIDMixin):
    __tablename__ = "organization_memberships"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("organization_locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    role: Mapped[UserRole] = mapped_column(String(50), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="memberships")
    organization: Mapped[Organization] = relationship("Organization", back_populates="memberships")
    location: Mapped[OrganizationLocation | None] = relationship("OrganizationLocation")

    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_org_membership_user"),
    )


class DoctorProfile(Base, TimestampUUIDMixin):
    __tablename__ = "doctor_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("organization_locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    specialization: Mapped[str] = mapped_column(String(150), nullable=False)
    qualification: Mapped[str] = mapped_column(String(255), nullable=False)
    registration_number: Mapped[str] = mapped_column(String(100), nullable=False)
    consultation_room: Mapped[str | None] = mapped_column(String(50), nullable=True)
    languages_spoken: Mapped[str] = mapped_column(String(255), nullable=False, default="English, Hindi")

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="doctor_profile")
    organization: Mapped[Organization] = relationship("Organization")
    location: Mapped[OrganizationLocation | None] = relationship("OrganizationLocation")


class ReceptionistProfile(Base, TimestampUUIDMixin):
    __tablename__ = "receptionist_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("organization_locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    desk_identifier: Mapped[str | None] = mapped_column(String(50), nullable=True)
    shift_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="receptionist_profile")
    organization: Mapped[Organization] = relationship("Organization")
    location: Mapped[OrganizationLocation | None] = relationship("OrganizationLocation")

