from datetime import date, datetime, timezone
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import AppointmentStatus, AppointmentType, UserRole, enum_val
from app.models.patients_appointments import Appointment, Patient
from app.models.system_audit import AuditEvent
from app.models.tenant import DoctorProfile, OrganizationLocation, OrganizationMembership, User
from app.schemas.appointments import (
    AppointmentCreate,
    AppointmentResponse,
    DoctorQueueGroup,
    PatientSummaryInAppointment,
    QueueViewResponse,
    ReceptionOverviewResponse,
)

# Valid finite state machine transitions for appointments
VALID_TRANSITIONS: dict[str, set[str]] = {
    "SCHEDULED": {"CONFIRMED", "ARRIVED", "WAITING", "CANCELLED", "NO_SHOW"},
    "CONFIRMED": {"ARRIVED", "WAITING", "CANCELLED", "NO_SHOW"},
    "ARRIVED": {"WAITING", "IN_PROGRESS", "CANCELLED", "NO_SHOW"},
    "WAITING": {"IN_PROGRESS", "CANCELLED", "NO_SHOW"},
    "IN_PROGRESS": {"COMPLETED"},
    "COMPLETED": set(),  # Terminal state
    "CANCELLED": set(),  # Terminal state
    "NO_SHOW": set(),    # Terminal state
}


class AppointmentService:
    @staticmethod
    def create_appointment(
        db: Session,
        organization_id: uuid.UUID,
        created_by_user_id: uuid.UUID,
        data: AppointmentCreate,
    ) -> Appointment:
        # 1. Validate Patient
        patient = db.get(Patient, data.patient_id)
        if not patient or patient.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid patient specified for this organization.",
            )

        # 2. Validate Doctor
        doc_mem = db.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.user_id == data.doctor_user_id,
                OrganizationMembership.role == UserRole.DOCTOR,
                OrganizationMembership.is_active == True,
            ).order_by(OrganizationMembership.created_at.desc())
        ).scalars().first()

        if not doc_mem:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Doctor does not belong to this organization or is inactive.",
            )

        # 3. Validate Location
        loc = None
        if data.location_id:
            loc = db.get(OrganizationLocation, data.location_id)
        if not loc or loc.organization_id != organization_id:
            loc = db.execute(
                select(OrganizationLocation).where(
                    OrganizationLocation.organization_id == organization_id,
                    OrganizationLocation.is_active == True,
                ).limit(1)
            ).scalar_one_or_none()
        if not loc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No clinic branch found for this organization.",
            )
        resolved_location_id = loc.id

        # 4. Calculate queue position for (organization, doctor, appointment_date)
        current_max = db.execute(
            select(func.max(Appointment.queue_position)).where(
                Appointment.organization_id == organization_id,
                Appointment.doctor_user_id == data.doctor_user_id,
                Appointment.appointment_date == data.appointment_date,
            )
        ).scalar() or 0
        queue_pos = current_max + 1

        # Determine initial status
        initial_status = data.initial_status or (
            AppointmentStatus.WAITING if data.appointment_type == AppointmentType.WALK_IN else AppointmentStatus.SCHEDULED
        )

        now = datetime.now(timezone.utc)
        resolved_scheduled_time = data.scheduled_time or now
        if resolved_scheduled_time.tzinfo is None:
            resolved_scheduled_time = resolved_scheduled_time.replace(tzinfo=timezone.utc)
        arrived_at = now if enum_val(initial_status) in ("ARRIVED", "WAITING") else None

        appointment = Appointment(
            organization_id=organization_id,
            location_id=resolved_location_id,
            patient_id=data.patient_id,
            doctor_user_id=data.doctor_user_id,
            created_by_user_id=created_by_user_id,
            appointment_date=data.appointment_date,
            scheduled_time=resolved_scheduled_time,
            queue_position=queue_pos,
            appointment_type=data.appointment_type,
            status=initial_status,
            reason_for_visit=data.reason_for_visit,
            administrative_notes=data.administrative_notes,
            arrived_at=arrived_at,
        )
        db.add(appointment)
        db.flush()

        audit = AuditEvent(
            organization_id=organization_id,
            actor_user_id=created_by_user_id,
            actor_role="RECEPTIONIST",
            event_type="APPOINTMENT_BOOKED",
            resource_type="APPOINTMENT",
            resource_id=appointment.id,
            action="CREATE",
            metadata_json={
                "patient_id": str(data.patient_id),
                "doctor_id": str(data.doctor_user_id),
                "status": enum_val(initial_status),
                "queue_position": queue_pos,
            },
        )
        db.add(audit)

        db.commit()
        db.refresh(appointment)
        return appointment

    @staticmethod
    def update_status(
        db: Session,
        organization_id: uuid.UUID,
        appointment_id: uuid.UUID,
        new_status: AppointmentStatus,
        actor_user_id: uuid.UUID,
        actor_role: str = "STAFF",
    ) -> Appointment:
        """Enforces validated state transitions for appointments."""
        appointment = db.get(Appointment, appointment_id)
        if not appointment or appointment.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found in this organization.",
            )

        current_status_str = enum_val(appointment.status)
        new_status_str = enum_val(new_status)

        if current_status_str == new_status_str:
            return appointment  # No-op

        allowed_next = VALID_TRANSITIONS.get(current_status_str, set())
        if new_status_str not in allowed_next:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid appointment status transition from '{current_status_str}' to '{new_status_str}'.",
            )

        now = datetime.now(timezone.utc)
        appointment.status = new_status

        # Set automatic transition timestamps
        if new_status_str in ("ARRIVED", "WAITING") and not appointment.arrived_at:
            appointment.arrived_at = now
        elif new_status_str == "IN_PROGRESS" and not appointment.started_at:
            appointment.started_at = now
        elif new_status_str == "COMPLETED" and not appointment.completed_at:
            appointment.completed_at = now

        audit = AuditEvent(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            event_type="APPOINTMENT_STATUS_TRANSITION",
            resource_type="APPOINTMENT",
            resource_id=appointment.id,
            action="UPDATE",
            metadata_json={
                "from_status": current_status_str,
                "to_status": new_status_str,
            },
        )
        db.add(audit)

        db.commit()
        db.refresh(appointment)
        return appointment

    @staticmethod
    def assign_doctor(
        db: Session,
        organization_id: uuid.UUID,
        appointment_id: uuid.UUID,
        new_doctor_user_id: uuid.UUID,
        actor_user_id: uuid.UUID,
    ) -> Appointment:
        """Reassigns an appointment to another doctor before completion."""
        appointment = db.get(Appointment, appointment_id)
        if not appointment or appointment.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found in this organization.",
            )

        status_str = enum_val(appointment.status)
        if status_str in ("COMPLETED", "CANCELLED"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot reassign doctor for a {status_str} appointment.",
            )

        doc_mem = db.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.user_id == new_doctor_user_id,
                OrganizationMembership.role == UserRole.DOCTOR,
                OrganizationMembership.is_active == True,
            ).order_by(OrganizationMembership.created_at.desc())
        ).scalars().first()

        if not doc_mem:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Specified doctor does not belong to this organization or is inactive.",
            )

        old_doc = appointment.doctor_user_id
        appointment.doctor_user_id = new_doctor_user_id

        # Recalculate queue position under new doctor
        max_q = db.execute(
            select(func.max(Appointment.queue_position)).where(
                Appointment.organization_id == organization_id,
                Appointment.doctor_user_id == new_doctor_user_id,
                Appointment.appointment_date == appointment.appointment_date,
            )
        ).scalar() or 0
        appointment.queue_position = max_q + 1

        audit = AuditEvent(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            actor_role="RECEPTIONIST",
            event_type="APPOINTMENT_DOCTOR_REASSIGNED",
            resource_type="APPOINTMENT",
            resource_id=appointment.id,
            action="UPDATE",
            metadata_json={
                "previous_doctor_id": str(old_doc),
                "new_doctor_id": str(new_doctor_user_id),
                "new_queue_position": appointment.queue_position,
            },
        )
        db.add(audit)

        db.commit()
        db.refresh(appointment)
        return appointment

    @staticmethod
    def get_reception_overview(
        db: Session,
        organization_id: uuid.UUID,
        target_date: date | None = None,
    ) -> ReceptionOverviewResponse:
        day = target_date or date.today()

        stmt = select(Appointment.status, func.count(Appointment.id)).where(
            Appointment.organization_id == organization_id,
            Appointment.appointment_date == day,
        ).group_by(Appointment.status)

        counts = dict(db.execute(stmt).all())

        return ReceptionOverviewResponse(
            target_date=day,
            total_today=sum(counts.values()),
            waiting=counts.get(AppointmentStatus.WAITING, 0),
            arrived=counts.get(AppointmentStatus.ARRIVED, 0),
            in_progress=counts.get(AppointmentStatus.IN_PROGRESS, 0),
            completed=counts.get(AppointmentStatus.COMPLETED, 0),
            cancelled=counts.get(AppointmentStatus.CANCELLED, 0),
            no_show=counts.get(AppointmentStatus.NO_SHOW, 0),
        )

    @staticmethod
    def get_queue(
        db: Session,
        organization_id: uuid.UUID,
        target_date: date | None = None,
        doctor_user_id: uuid.UUID | None = None,
        location_id: uuid.UUID | None = None,
        status_filter: AppointmentStatus | None = None,
        appointment_type: AppointmentType | None = None,
    ) -> QueueViewResponse:
        stmt = (
            select(Appointment)
            .where(
                Appointment.organization_id == organization_id,
            )
        )

        if target_date is not None:
            stmt = stmt.where(Appointment.appointment_date == target_date)
        if doctor_user_id:
            stmt = stmt.where(Appointment.doctor_user_id == doctor_user_id)
        if location_id:
            stmt = stmt.where(Appointment.location_id == location_id)
        if status_filter:
            stmt = stmt.where(Appointment.status == status_filter)
        if appointment_type:
            stmt = stmt.where(Appointment.appointment_type == appointment_type)

        stmt = stmt.order_by(Appointment.appointment_date.desc(), Appointment.queue_position.asc(), Appointment.scheduled_time.asc())
        appointments = db.execute(stmt).scalars().all()

        # Format all appointments
        all_formatted: list[AppointmentResponse] = []
        doctor_groups_map: dict[uuid.UUID | None, list[AppointmentResponse]] = {}

        for a in appointments:
            doc_user = a.doctor
            formatted = AppointmentResponse(
                id=a.id,
                organization_id=a.organization_id,
                location_id=a.location_id,
                patient_id=a.patient_id,
                doctor_user_id=a.doctor_user_id,
                doctor_name=doc_user.full_name if doc_user else None,
                created_by_user_id=a.created_by_user_id,
                appointment_date=a.appointment_date,
                scheduled_time=a.scheduled_time,
                queue_position=a.queue_position,
                appointment_type=a.appointment_type,
                status=a.status,
                reason_for_visit=a.reason_for_visit,
                administrative_notes=a.administrative_notes,
                arrived_at=a.arrived_at,
                started_at=a.started_at,
                completed_at=a.completed_at,
                created_at=a.created_at,
                patient=PatientSummaryInAppointment.model_validate(a.patient) if a.patient else None,
            )
            all_formatted.append(formatted)
            doctor_groups_map.setdefault(a.doctor_user_id, []).append(formatted)

        doctor_queues: list[DoctorQueueGroup] = []
        for doc_id, apps in doctor_groups_map.items():
            doc_user = db.get(User, doc_id) if doc_id else None
            doc_profile = None
            if doc_id:
                doc_profile = db.execute(
                    select(DoctorProfile).where(DoctorProfile.user_id == doc_id).order_by(DoctorProfile.created_at.desc())
                ).scalars().first()

            waiting_count = sum(1 for a in apps if enum_val(a.status) in ("WAITING", "ARRIVED"))

            doctor_queues.append(
                DoctorQueueGroup(
                    doctor_user_id=doc_id,
                    doctor_name=doc_user.full_name if doc_user else "Doctor",
                    specialization=doc_profile.specialization if doc_profile else "General",
                    consultation_room=doc_profile.consultation_room if doc_profile else None,
                    waiting_count=waiting_count,
                    appointments=apps,
                )
            )

        return QueueViewResponse(
            target_date=target_date,
            total_in_queue=len(all_formatted),
            doctor_queues=doctor_queues,
            queue=all_formatted,
        )

