from datetime import date, datetime, timezone
import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.clinical_reports import Report, ReportStatus
from app.models.consultations_audio import ConsentRecord, Consultation
from app.models.enums import AppointmentStatus, ConsultationStatus, UserRole, enum_val
from app.models.patients_appointments import Appointment
from app.models.subscriptions import UsageRecord
from app.models.system_audit import AuditEvent
from app.models.tenant import DoctorProfile, OrganizationMembership, User
from app.schemas.appointments import AppointmentResponse, PatientSummaryInAppointment
from app.schemas.consultations import (
    ConsentRecordResponse,
    ConsultationConsentRequest,
    ConsultationConsentWithdrawRequest,
    ConsultationResponse,
    DoctorDashboardQueueItem,
    DoctorDashboardResponse,
)
from app.services.entitlement_service import EntitlementService


class ConsultationService:
    @staticmethod
    def get_doctor_dashboard(
        db: Session,
        organization_id: uuid.UUID,
        doctor_user_id: uuid.UUID,
        target_date: date | None = None,
    ) -> DoctorDashboardResponse:
        day = target_date or date.today()

        # Doctor profile
        doc_user = db.get(User, doctor_user_id)
        if not doc_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found.")

        doc_profile = db.execute(
            select(DoctorProfile).where(DoctorProfile.user_id == doctor_user_id)
        ).scalar_one_or_none()

        # Fetch all appointments for this doctor in this organization (excluding cancelled)
        stmt = (
            select(Appointment)
            .where(
                Appointment.organization_id == organization_id,
                Appointment.doctor_user_id == doctor_user_id,
                Appointment.status != AppointmentStatus.CANCELLED,
            )
            .order_by(Appointment.queue_position.asc(), Appointment.scheduled_time.asc())
        )
        appointments = db.execute(stmt).scalars().all()

        current_item: DoctorDashboardQueueItem | None = None
        waiting_list: list[DoctorDashboardQueueItem] = []
        upcoming_list: list[DoctorDashboardQueueItem] = []
        completed_list: list[DoctorDashboardQueueItem] = []

        for app in appointments:
            # Check previous history
            prior_count = db.execute(
                select(func.count(Consultation.id)).where(
                    Consultation.organization_id == organization_id,
                    Consultation.patient_id == app.patient_id,
                )
            ).scalar() or 0

            # Check existing consultation & consent
            consultation = db.execute(
                select(Consultation).where(Consultation.appointment_id == app.id)
            ).scalar_one_or_none()

            consent_status = "NOT_RECORDED"
            cons_id = None
            if consultation:
                cons_id = consultation.id
                consent = db.execute(
                    select(ConsentRecord).where(ConsentRecord.consultation_id == consultation.id)
                ).scalar_one_or_none()
                if consent:
                    consent_status = "WITHDRAWN" if consent.withdrawn_at else ("GRANTED" if consent.is_granted else "DENIED")

            app_resp = AppointmentResponse(
                id=app.id,
                organization_id=app.organization_id,
                location_id=app.location_id,
                patient_id=app.patient_id,
                doctor_user_id=app.doctor_user_id,
                doctor_name=doc_user.full_name,
                created_by_user_id=app.created_by_user_id,
                appointment_date=app.appointment_date,
                scheduled_time=app.scheduled_time,
                queue_position=app.queue_position,
                appointment_type=app.appointment_type,
                status=app.status,
                reason_for_visit=app.reason_for_visit,
                administrative_notes=app.administrative_notes,
                arrived_at=app.arrived_at,
                started_at=app.started_at,
                completed_at=app.completed_at,
                created_at=app.created_at,
                patient=PatientSummaryInAppointment.model_validate(app.patient) if app.patient else None,
            )

            item = DoctorDashboardQueueItem(
                appointment=app_resp,
                consultation_id=cons_id,
                has_previous_history=prior_count > 0,
                consent_status=consent_status,
            )

            status_str = enum_val(app.status)
            if status_str in ("IN_PROGRESS", "IN_CONSULTATION") and not current_item:
                current_item = item
            elif status_str in ("WAITING", "ARRIVED", "SCHEDULED", "CONFIRMED"):
                waiting_list.append(item)
                if status_str in ("SCHEDULED", "CONFIRMED"):
                    upcoming_list.append(item)
            elif status_str == "COMPLETED":
                completed_list.append(item)

        # Active consultation summary
        active_consultation_dict = None
        if current_item and current_item.consultation_id:
            active_consultation_dict = {
                "id": str(current_item.consultation_id),
                "patient_id": str(current_item.appointment.patient_id),
                "patient_name": current_item.appointment.patient.full_name if current_item.appointment.patient else "Patient",
                "patient_identifier": current_item.appointment.patient.patient_identifier if current_item.appointment.patient else "",
                "started_at": current_item.appointment.started_at.isoformat() if current_item.appointment.started_at else datetime.now(timezone.utc).isoformat(),
                "status": enum_val(current_item.appointment.status),
            }

        # Pending reports awaiting approval
        pending_reports_stmt = (
            select(Report, Consultation)
            .join(Consultation, Consultation.id == Report.consultation_id)
            .where(
                Report.organization_id == organization_id,
                Consultation.doctor_user_id == doctor_user_id,
                Report.current_status.in_([ReportStatus.AI_GENERATED_DRAFT, ReportStatus.AWAITING_APPROVAL]),
            )
            .order_by(Report.created_at.desc())
        )
        pending_rows = db.execute(pending_reports_stmt).all()
        pending_reports = [
            {
                "report_id": str(r.id),
                "consultation_id": str(c.id),
                "report_type": enum_val(r.report_type),
                "current_status": enum_val(r.current_status),
                "version_number": r.current_version_number,
                "created_at": r.created_at.isoformat(),
            }
            for r, c in pending_rows
        ]

        return DoctorDashboardResponse(
            doctor_name=doc_user.full_name,
            specialization=doc_profile.specialization if doc_profile else "General Medicine",
            consultation_room=doc_profile.consultation_room if doc_profile else None,
            today_date=day.isoformat(),
            target_date=day,
            current_patient=current_item,
            active_consultation=active_consultation_dict,
            waiting_queue=[item.appointment for item in waiting_list],
            waiting_patients=waiting_list,
            upcoming_appointments=[item.appointment for item in upcoming_list],
            upcoming_patients=upcoming_list,
            completed_today_count=len(completed_list),
            completed_patients=completed_list,
            reports_pending_approval=pending_reports,
        )

    @staticmethod
    def start_consultation(
        db: Session,
        organization_id: uuid.UUID,
        doctor_user_id: uuid.UUID,
        appointment_id: uuid.UUID,
    ) -> Consultation:
        """Starts or resumes a clinical consultation session for an assigned appointment.
        Enforces plan consultation quota and updates appointment to IN_PROGRESS.
        """
        EntitlementService.ensure_active_subscription_write_allowed(db, organization_id)

        appointment = db.get(Appointment, appointment_id)
        if not appointment or appointment.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found in this organization.",
            )

        if appointment.doctor_user_id != doctor_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Appointment is assigned to another clinician.",
            )

        # Resume existing consultation if present
        existing_cons = db.execute(
            select(Consultation).where(Consultation.appointment_id == appointment_id)
        ).scalar_one_or_none()

        now = datetime.now(timezone.utc)

        if existing_cons:
            if enum_val(appointment.status) != "IN_PROGRESS":
                appointment.status = AppointmentStatus.IN_PROGRESS
                if not appointment.started_at:
                    appointment.started_at = now
                db.commit()
            return existing_cons

        # Check plan consultation limit
        sub = EntitlementService.get_active_subscription(db, organization_id)
        month_str = now.strftime("%Y-%m")
        usage = db.execute(
            select(UsageRecord).where(
                UsageRecord.organization_id == organization_id,
                UsageRecord.period_month == month_str,
            )
        ).scalar_one_or_none()

        if not usage and sub:
            usage = UsageRecord(
                organization_id=organization_id,
                subscription_id=sub.id,
                period_month=month_str,
                consultations_count=0,
            )
            db.add(usage)
            db.flush()

        if usage and sub and sub.plan:
            if usage.consultations_count >= sub.plan.monthly_consultation_limit:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Monthly consultation quota reached ({usage.consultations_count}/{sub.plan.monthly_consultation_limit}).",
                )
            usage.consultations_count += 1

        # Create new Consultation
        consultation = Consultation(
            organization_id=organization_id,
            location_id=appointment.location_id,
            appointment_id=appointment.id,
            patient_id=appointment.patient_id,
            doctor_user_id=doctor_user_id,
            status=ConsultationStatus.SETUP,
            started_at=now,
            chief_complaint_summary=appointment.reason_for_visit,
        )
        db.add(consultation)
        db.flush()

        # Update appointment status to IN_PROGRESS
        appointment.status = AppointmentStatus.IN_PROGRESS
        if not appointment.started_at:
            appointment.started_at = now

        audit = AuditEvent(
            organization_id=organization_id,
            actor_user_id=doctor_user_id,
            actor_role="DOCTOR",
            event_type="CONSULTATION_STARTED",
            resource_type="CONSULTATION",
            resource_id=consultation.id,
            action="CREATE",
            metadata_json={
                "appointment_id": str(appointment.id),
                "patient_id": str(appointment.patient_id),
            },
        )
        db.add(audit)

        db.commit()
        db.refresh(consultation)
        return consultation

    @staticmethod
    def record_consent(
        db: Session,
        organization_id: uuid.UUID,
        doctor_user_id: uuid.UUID,
        consultation_id: uuid.UUID,
        data: ConsultationConsentRequest,
    ) -> ConsentRecord:
        """Captures mandatory informed patient consent before any audio recording can proceed.
        Rule (Part 5.3): Recording is strictly forbidden merely because an appointment exists.
        """
        consultation = db.get(Consultation, consultation_id)
        if not consultation or consultation.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Consultation session not found in this organization.",
            )

        if consultation.doctor_user_id != doctor_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Consent must be recorded by the attending doctor.",
            )

        now = datetime.now(timezone.utc)

        # Existing consent
        consent = db.execute(
            select(ConsentRecord).where(ConsentRecord.consultation_id == consultation_id)
        ).scalar_one_or_none()

        if consent:
            consent.purpose = data.purpose
            consent.language = data.language
            consent.consent_wording_version = data.consent_wording_version
            consent.consent_text_snapshot = data.consent_text_snapshot
            consent.is_granted = data.is_granted
            consent.granted_at = now
            consent.withdrawn_at = None
            consent.withdrawal_reason = None
        else:
            consent = ConsentRecord(
                organization_id=organization_id,
                patient_id=consultation.patient_id,
                consultation_id=consultation.id,
                recorded_by_doctor_id=doctor_user_id,
                purpose=data.purpose,
                language=data.language,
                consent_wording_version=data.consent_wording_version,
                consent_text_snapshot=data.consent_text_snapshot,
                is_granted=data.is_granted,
                granted_at=now,
            )
            db.add(consent)

        db.flush()

        if data.is_granted:
            consultation.status = ConsultationStatus.CONSENT_RECORDED

        audit = AuditEvent(
            organization_id=organization_id,
            actor_user_id=doctor_user_id,
            actor_role="DOCTOR",
            event_type="PATIENT_CONSENT_RECORDED",
            resource_type="CONSENT_RECORD",
            resource_id=consent.id,
            action="CREATE" if not consent else "UPDATE",
            metadata_json={
                "consultation_id": str(consultation_id),
                "is_granted": data.is_granted,
                "language": data.language,
            },
        )
        db.add(audit)

        db.commit()
        db.refresh(consent)
        return consent

    @staticmethod
    def withdraw_consent(
        db: Session,
        organization_id: uuid.UUID,
        doctor_user_id: uuid.UUID,
        consultation_id: uuid.UUID,
        data: ConsultationConsentWithdrawRequest,
    ) -> ConsentRecord:
        """Immediately withdraws previously granted consent and blocks recording/AI pipeline."""
        consultation = db.get(Consultation, consultation_id)
        if not consultation or consultation.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Consultation not found.",
            )

        consent = db.execute(
            select(ConsentRecord).where(ConsentRecord.consultation_id == consultation_id)
        ).scalar_one_or_none()

        if not consent or not consent.is_granted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active granted consent to withdraw for this consultation.",
            )

        now = datetime.now(timezone.utc)
        consent.is_granted = False
        consent.withdrawn_at = now
        consent.withdrawal_reason = data.withdrawal_reason

        # Revert consultation status to SETUP if it was in CONSENT_RECORDED
        if enum_val(consultation.status) in ("CONSENT_RECORDED", "RECORDING"):
            consultation.status = ConsultationStatus.SETUP

        audit = AuditEvent(
            organization_id=organization_id,
            actor_user_id=doctor_user_id,
            actor_role="DOCTOR",
            event_type="PATIENT_CONSENT_WITHDRAWN",
            resource_type="CONSENT_RECORD",
            resource_id=consent.id,
            action="UPDATE",
            metadata_json={
                "consultation_id": str(consultation_id),
                "withdrawal_reason": data.withdrawal_reason,
            },
        )
        db.add(audit)

        db.commit()
        db.refresh(consent)
        return consent

