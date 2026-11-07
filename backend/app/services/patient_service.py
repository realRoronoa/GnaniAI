from datetime import datetime, timezone
import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.clinical_reports import MedicationInstruction, Report, ReportStatus, ReportType
from app.models.consultations_audio import Consultation
from app.models.enums import enum_val
from app.models.patients_appointments import Patient
from app.schemas.patients import (
    DuplicateCheckResponse,
    DuplicateMatchSummary,
    HistoricalMedicationItem,
    LongitudinalPatientHistoryResponse,
    PastConsultationSummary,
    PatientCreate,
    PatientResponse,
    PatientUpdate,
)


class PatientService:
    @staticmethod
    def check_duplicates(
        db: Session,
        organization_id: uuid.UUID,
        mobile_number: str | None = None,
        full_name: str | None = None,
    ) -> DuplicateCheckResponse:
        """Finds potential duplicate patient records within the organization.
        Rule (Part 4.3): Families often share mobile numbers in India; never auto-merge.
        """
        conditions = []
        if mobile_number and mobile_number.strip():
            raw_phone = mobile_number.strip()
            # Handle URL decoded space from unencoded '+'
            if raw_phone.startswith(" ") or not raw_phone.startswith("+"):
                alt_phone = "+" + raw_phone.lstrip()
            else:
                alt_phone = raw_phone

            digits = "".join(c for c in raw_phone if c.isdigit())
            if len(digits) >= 10:
                last_10 = digits[-10:]
                conditions.append(
                    or_(
                        Patient.mobile_number == raw_phone,
                        Patient.mobile_number == alt_phone,
                        Patient.mobile_number.like(f"%{last_10}"),
                    )
                )
            else:
                conditions.append(
                    or_(
                        Patient.mobile_number == raw_phone,
                        Patient.mobile_number == alt_phone,
                    )
                )

        if full_name and full_name.strip():
            clean_name = full_name.strip().lower()
            conditions.append(func.lower(Patient.full_name) == clean_name)

        if not conditions:
            return DuplicateCheckResponse(
                has_matches=False,
                potential_matches=[],
                recommendation="No duplicate check criteria provided.",
            )

        stmt = (
            select(Patient)
            .where(
                Patient.organization_id == organization_id,
                or_(*conditions),
            )
            .limit(10)
        )
        matches = db.execute(stmt).scalars().all()

        match_summaries: list[DuplicateMatchSummary] = []
        for p in matches:
            reasons = []
            if mobile_number:
                m_digits = "".join(c for c in mobile_number if c.isdigit())
                p_digits = "".join(c for c in p.mobile_number if c.isdigit())
                if (len(m_digits) >= 10 and len(p_digits) >= 10 and m_digits[-10:] == p_digits[-10:]) or p.mobile_number == mobile_number.strip():
                    reasons.append("Identical mobile number (may be family member)")
            if full_name and p.full_name.strip().lower() == full_name.strip().lower():
                reasons.append("Exact name match")

            match_summaries.append(
                DuplicateMatchSummary(
                    id=p.id,
                    patient_identifier=p.patient_identifier,
                    full_name=p.full_name,
                    gender=p.gender,
                    age_years=p.age_years,
                    mobile_number=p.mobile_number,
                    match_reasons=reasons,
                )
            )

        rec = (
            "Found matching records. Verify whether this is a returning patient or a family member sharing the mobile number."
            if match_summaries
            else "No existing duplicate records found."
        )

        return DuplicateCheckResponse(
            has_matches=len(match_summaries) > 0,
            potential_matches=match_summaries,
            recommendation=rec,
        )

    @staticmethod
    def create_patient(
        db: Session,
        organization_id: uuid.UUID,
        data: PatientCreate,
    ) -> Patient:
        """Registers a new patient record scoped strictly to the organization."""
        identifier = data.patient_identifier
        if not identifier or not identifier.strip():
            # Auto-generate unique identifier: P-{year}-{count+1:04d}
            year = datetime.now(timezone.utc).year
            count = (
                db.execute(
                    select(func.count(Patient.id)).where(Patient.organization_id == organization_id)
                ).scalar()
                or 0
            )
            identifier = f"ARC-{year}-{count + 1:04d}"

        # Check unique constraint on organization_id + patient_identifier
        existing = db.execute(
            select(Patient).where(
                Patient.organization_id == organization_id,
                Patient.patient_identifier == identifier,
            )
        ).scalar_one_or_none()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Patient with identifier {identifier} already exists in this organization.",
            )

        patient = Patient(
            organization_id=organization_id,
            patient_identifier=identifier,
            full_name=data.full_name.strip(),
            date_of_birth=data.date_of_birth,
            age_years=data.age_years,
            gender=data.gender.upper(),
            mobile_number=data.mobile_number.strip(),
            email=data.email,
            preferred_language=data.preferred_language,
            allergies_summary=data.allergies_summary,
            allergy_verification_status=data.allergy_verification_status or "UNVERIFIED",
            administrative_notes=data.administrative_notes,
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)
        return patient

    @staticmethod
    def search_patients(
        db: Session,
        organization_id: uuid.UUID,
        query: str | None = None,
        limit: int = 50,
    ) -> list[Patient]:
        """Searches patients within the organization by name, identifier, or mobile."""
        stmt = select(Patient).where(Patient.organization_id == organization_id)
        if query and query.strip():
            term = f"%{query.strip()}%"
            stmt = stmt.where(
                or_(
                    Patient.full_name.ilike(term),
                    Patient.patient_identifier.ilike(term),
                    Patient.mobile_number.ilike(term),
                )
            )

        stmt = stmt.order_by(Patient.created_at.desc()).limit(limit)
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def get_patient(
        db: Session,
        organization_id: uuid.UUID,
        patient_id: uuid.UUID,
    ) -> Patient:
        patient = db.get(Patient, patient_id)
        if not patient or patient.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient record not found in this organization.",
            )
        return patient

    @staticmethod
    def update_patient(
        db: Session,
        organization_id: uuid.UUID,
        patient_id: uuid.UUID,
        data: PatientUpdate,
    ) -> Patient:
        patient = PatientService.get_patient(db, organization_id, patient_id)

        for field, val in data.model_dump(exclude_unset=True).items():
            if val is not None:
                if field == "gender":
                    val = str(val).upper()
                setattr(patient, field, val)

        db.commit()
        db.refresh(patient)
        return patient

    @staticmethod
    def get_longitudinal_history(
        db: Session,
        organization_id: uuid.UUID,
        patient_id: uuid.UUID,
    ) -> LongitudinalPatientHistoryResponse:
        """Constructs longitudinal medical record:
        Past visits, approved reports, and past medications (explicitly is_historical=True).
        """
        patient = PatientService.get_patient(db, organization_id, patient_id)

        # Consultations
        stmt = (
            select(Consultation)
            .where(
                Consultation.organization_id == organization_id,
                Consultation.patient_id == patient_id,
            )
            .order_by(Consultation.started_at.desc())
        )
        consultations = db.execute(stmt).scalars().all()

        past_consultations: list[PastConsultationSummary] = []
        historical_medications: list[HistoricalMedicationItem] = []
        longitudinal_symptoms: list[dict[str, Any]] = []

        for c in consultations:
            # Check for approved report
            approved_report = db.execute(
                select(Report).where(
                    Report.consultation_id == c.id,
                    Report.report_type == ReportType.DOCTOR_CLINICAL,
                    Report.current_status == ReportStatus.APPROVED,
                )
            ).scalar_one_or_none()

            doc_name = c.doctor.full_name if c.doctor else "Attending Clinician"

            past_consultations.append(
                PastConsultationSummary(
                    id=c.id,
                    appointment_id=c.appointment_id,
                    started_at=c.started_at,
                    ended_at=c.ended_at,
                    doctor_name=doc_name,
                    chief_complaint_summary=c.chief_complaint_summary,
                    status=enum_val(c.status),
                    has_approved_report=approved_report is not None,
                )
            )

            # Retrieve medications
            meds = db.execute(
                select(MedicationInstruction).where(MedicationInstruction.consultation_id == c.id)
            ).scalars().all()

            for m in meds:
                historical_medications.append(
                    HistoricalMedicationItem(
                        id=m.id,
                        consultation_id=c.id,
                        consultation_date=c.started_at,
                        medication_name=m.medication_name,
                        dosage=m.dosage,
                        frequency=m.frequency,
                        duration=m.duration,
                        route=m.route,
                        is_historical=True,
                        special_instructions=m.special_instructions,
                    )
                )

            if c.chief_complaint_summary:
                longitudinal_symptoms.append({
                    "date": c.started_at.isoformat(),
                    "chief_complaint": c.chief_complaint_summary,
                })

        return LongitudinalPatientHistoryResponse(
            patient=PatientResponse.model_validate(patient),
            total_consultations=len(consultations),
            allergy_state={
                "allergies_summary": patient.allergies_summary or "No known drug allergies (NKDA)",
                "verification_status": patient.allergy_verification_status,
            },
            past_consultations=past_consultations,
            historical_medications=historical_medications,
            longitudinal_symptoms=longitudinal_symptoms,
        )
