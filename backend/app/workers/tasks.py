import asyncio
from datetime import datetime, timezone
import hashlib
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.integrations.ai import (
    get_clinical_extraction_provider,
    get_report_generation_provider,
    get_transcription_provider,
    get_translation_provider,
)
from app.integrations.storage.s3_service import storage_service
from app.models.clinical_reports import (
    ClinicalFact,
    ClinicalFactEvidence,
    MedicationInstruction,
    Report,
    ReportStatus,
    ReportType,
    ReportVersion,
)
from app.models.consultations_audio import (
    AudioAsset,
    ConsentRecord,
    Consultation,
    TranscriptSegment,
    TranscriptVersion,
)
from app.models.enums import (
    CertaintyStatus,
    ConsultationStatus,
    DoctorReviewStatus,
    JobStatus,
    JobType,
    ProvenanceType,
    SpeakerLabel,
    TranscriptSourceType,
    enum_val,
)
from app.models.patients_appointments import Patient
from app.models.system_audit import AuditEvent, ProcessingJob
from app.models.tenant import DoctorProfile, Organization, User
from app.workers.celery_app import celery_app


def compute_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def process_consultation_pipeline(db: Session, consultation_id: uuid.UUID) -> Consultation:
    """Core synchronous pipeline orchestrating the AI documentation workflow:
    1. Audio validation
    2. Transcription (Gnani Prisma/Mock)
    3. Clinical fact extraction & evidence grounding (Gnani Evon/Mock)
    4. Dual report generation (SOAP clinical & patient summary)
    5. Vernacular translation
    Status moves to REVIEW_READY upon completion.
    """
    consultation = db.get(Consultation, consultation_id)
    if not consultation:
        raise ValueError(f"Consultation {consultation_id} not found.")

    # Rule (Part 5.3): Reject unless active granted consent exists
    consent = db.execute(
        select(ConsentRecord).where(
            ConsentRecord.consultation_id == consultation_id,
            ConsentRecord.is_granted.is_(True),
            ConsentRecord.withdrawn_at.is_(None),
        )
    ).scalar_one_or_none()

    if not consent:
        raise PermissionError("Cannot process consultation audio: Patient consent has not been granted or was withdrawn.")

    audio_asset = db.execute(
        select(AudioAsset).where(AudioAsset.consultation_id == consultation_id).order_by(AudioAsset.created_at.desc())
    ).scalar_one_or_none()

    if not audio_asset:
        raise ValueError("No audio asset uploaded for this consultation.")

    org_id = consultation.organization_id
    now = datetime.now(timezone.utc)
    consultation.status = ConsultationStatus.PROCESSING
    db.commit()

    # -------------------------------------------------------------------------
    # Stage 1: AUDIO_VALIDATION
    # -------------------------------------------------------------------------
    val_job = ProcessingJob(
        organization_id=org_id,
        consultation_id=consultation.id,
        job_type=JobType.AUDIO_VALIDATION,
        status=JobStatus.RUNNING,
        started_at=now,
    )
    db.add(val_job)
    db.flush()

    audio_bytes = storage_service.get_object_bytes(audio_asset.storage_key)
    calc_sha = hashlib.sha256(audio_bytes).hexdigest()
    if calc_sha != audio_asset.checksum_sha256:
        val_job.status = JobStatus.FAILED
        val_job.error_message = "Audio checksum mismatch."
        db.commit()
        raise ValueError("Audio asset integrity check failed.")

    val_job.status = JobStatus.COMPLETED
    val_job.completed_at = datetime.now(timezone.utc)
    db.commit()

    # -------------------------------------------------------------------------
    # Stage 2: TRANSCRIPTION
    # -------------------------------------------------------------------------
    stt_job = ProcessingJob(
        organization_id=org_id,
        consultation_id=consultation.id,
        job_type=JobType.TRANSCRIPTION,
        status=JobStatus.RUNNING,
        started_at=datetime.now(timezone.utc),
    )
    db.add(stt_job)
    db.flush()

    stt_provider = get_transcription_provider()
    transcription_result = asyncio.run(
        stt_provider.transcribe(audio_bytes, consent.language or "en-IN")
    )

    transcript_ver = TranscriptVersion(
        organization_id=org_id,
        consultation_id=consultation.id,
        version_number=1,
        source_type=TranscriptSourceType.AI_PRISMA,
        full_text=transcription_result.full_text,
        original_ai_text=transcription_result.full_text,
        language_detected=transcription_result.language_detected,
        created_by_user_id=consultation.doctor_user_id,
        is_current=True,
    )
    db.add(transcript_ver)
    db.flush()

    segment_records: list[TranscriptSegment] = []
    for seg in transcription_result.segments:
        s_record = TranscriptSegment(
            transcript_version_id=transcript_ver.id,
            consultation_id=consultation.id,
            sequence_number=seg.sequence_number,
            speaker_label=SpeakerLabel(seg.speaker_label) if seg.speaker_label in SpeakerLabel.__members__ else SpeakerLabel.UNKNOWN,
            start_time_ms=seg.start_time_ms,
            end_time_ms=seg.end_time_ms,
            original_text=seg.text,
            corrected_text=None,
            confidence_score=seg.confidence_score,
        )
        db.add(s_record)
        segment_records.append(s_record)

    db.flush()
    stt_job.status = JobStatus.COMPLETED
    stt_job.completed_at = datetime.now(timezone.utc)
    db.commit()

    # -------------------------------------------------------------------------
    # Stage 3: CLINICAL_EXTRACTION & PROVENANCE GROUNDING
    # -------------------------------------------------------------------------
    extract_job = ProcessingJob(
        organization_id=org_id,
        consultation_id=consultation.id,
        job_type=JobType.CLINICAL_EXTRACTION,
        status=JobStatus.RUNNING,
        started_at=datetime.now(timezone.utc),
    )
    db.add(extract_job)
    db.flush()

    extractor = get_clinical_extraction_provider()
    extraction_result = asyncio.run(
        extractor.extract_clinical_data(
            transcript_text=transcription_result.full_text,
            segments=transcription_result.segments,
        )
    )

    consultation.chief_complaint_summary = extraction_result.chief_complaint_summary
    consultation.longitudinal_comparison_json = extraction_result.longitudinal_comparison_json

    # Save extracted facts and evidence links
    saved_facts_data = []
    for fact in extraction_result.facts:
        c_fact = ClinicalFact(
            organization_id=org_id,
            consultation_id=consultation.id,
            category=fact.category,
            fact_key=fact.fact_key,
            fact_value=fact.fact_value,
            source_speaker=fact.source_speaker,
            provenance_type=ProvenanceType(fact.provenance_type) if fact.provenance_type in ProvenanceType.__members__ else ProvenanceType.AI_EXTRACTED,
            certainty_status=CertaintyStatus(fact.certainty_status) if fact.certainty_status in CertaintyStatus.__members__ else CertaintyStatus.VERIFIED,
            ai_extraction_status="SUCCESS",
            doctor_review_status=DoctorReviewStatus.PENDING,
            validation_flags_json=fact.validation_flags,
        )
        db.add(c_fact)
        db.flush()

        # Link evidence to transcript segment
        target_seg = segment_records[fact.segment_indices[0]] if fact.segment_indices and fact.segment_indices[0] < len(segment_records) else (segment_records[0] if segment_records else None)
        if target_seg:
            evidence = ClinicalFactEvidence(
                clinical_fact_id=c_fact.id,
                transcript_segment_id=target_seg.id,
                evidence_quotation=fact.evidence_quotation or target_seg.original_text,
                start_time_ms=target_seg.start_time_ms,
                end_time_ms=target_seg.end_time_ms,
            )
            db.add(evidence)

        saved_facts_data.append({
            "category": fact.category,
            "fact_key": fact.fact_key,
            "fact_value": fact.fact_value,
        })

    # Save medications
    saved_meds_data = []
    for med in extraction_result.medications:
        m_rec = MedicationInstruction(
            organization_id=org_id,
            consultation_id=consultation.id,
            medication_name=med.medication_name,
            strength=med.strength,
            dosage=med.dosage,
            route=med.route,
            frequency=med.frequency,
            duration=med.duration,
            special_instructions=med.special_instructions,
            uncertainty_flags_json=med.uncertainty_flags,
            is_historical=med.is_historical,
            doctor_verified=False,  # Strict: Doctor must explicitly verify!
        )
        db.add(m_rec)
        saved_meds_data.append({
            "medication_name": med.medication_name,
            "strength": med.strength,
            "dosage": med.dosage,
            "frequency": med.frequency,
            "duration": med.duration,
            "special_instructions": med.special_instructions,
        })

    db.flush()
    extract_job.status = JobStatus.COMPLETED
    extract_job.completed_at = datetime.now(timezone.utc)
    db.commit()

    # -------------------------------------------------------------------------
    # Stage 4: DUAL REPORT GENERATION
    # -------------------------------------------------------------------------
    report_job = ProcessingJob(
        organization_id=org_id,
        consultation_id=consultation.id,
        job_type=JobType.REPORT_GENERATION,
        status=JobStatus.RUNNING,
        started_at=datetime.now(timezone.utc),
    )
    db.add(report_job)
    db.flush()

    patient = db.get(Patient, consultation.patient_id)
    doctor = db.get(User, consultation.doctor_user_id)
    doc_prof = db.execute(select(DoctorProfile).where(DoctorProfile.user_id == doctor.id)).scalar_one_or_none()
    org = db.get(Organization, org_id)

    patient_dict = {
        "full_name": patient.full_name if patient else "Patient",
        "patient_identifier": patient.patient_identifier if patient else "",
        "age_years": patient.age_years if patient else "N/A",
        "gender": patient.gender if patient else "",
        "allergies_summary": patient.allergies_summary if patient else None,
    }
    doctor_dict = {
        "full_name": doctor.full_name if doctor else "Doctor",
        "specialization": doc_prof.specialization if doc_prof else "General Medicine",
    }
    clinic_dict = {
        "name": org.name if org else "ArogyaScribe Clinic",
        "contact_phone": org.contact_phone if org else "",
    }

    report_gen = get_report_generation_provider()
    dual_reports = asyncio.run(
        report_gen.generate_dual_reports(
            chief_complaint=extraction_result.chief_complaint_summary,
            facts=saved_facts_data,
            medications=saved_meds_data,
            patient_info=patient_dict,
            doctor_info=doctor_dict,
            clinic_info=clinic_dict,
        )
    )

    # 1. Doctor Clinical Report
    doc_report = Report(
        organization_id=org_id,
        consultation_id=consultation.id,
        report_type=ReportType.DOCTOR_CLINICAL,
        current_status=ReportStatus.AI_GENERATED_DRAFT,
        current_version_number=1,
        target_language="en-IN",
    )
    db.add(doc_report)
    db.flush()

    doc_ver = ReportVersion(
        report_id=doc_report.id,
        consultation_id=consultation.id,
        version_number=1,
        status=ReportStatus.AI_GENERATED_DRAFT,
        structured_content_json=dual_reports.doctor_structured_json,
        rendered_markdown=dual_reports.doctor_clinical_markdown,
        created_by_user_id=consultation.doctor_user_id,
        content_sha256=compute_sha256(dual_reports.doctor_clinical_markdown),
    )
    db.add(doc_ver)

    # 2. Patient Summary Report
    pat_report = Report(
        organization_id=org_id,
        consultation_id=consultation.id,
        report_type=ReportType.PATIENT_SUMMARY,
        current_status=ReportStatus.AI_GENERATED_DRAFT,
        current_version_number=1,
        target_language=patient.preferred_language if patient else "en-IN",
    )
    db.add(pat_report)
    db.flush()

    pat_ver = ReportVersion(
        report_id=pat_report.id,
        consultation_id=consultation.id,
        version_number=1,
        status=ReportStatus.AI_GENERATED_DRAFT,
        structured_content_json=dual_reports.patient_structured_json,
        rendered_markdown=dual_reports.patient_summary_markdown,
        created_by_user_id=consultation.doctor_user_id,
        content_sha256=compute_sha256(dual_reports.patient_summary_markdown),
    )
    db.add(pat_ver)

    db.flush()
    report_job.status = JobStatus.COMPLETED
    report_job.completed_at = datetime.now(timezone.utc)
    db.commit()

    # -------------------------------------------------------------------------
    # Stage 5: TRANSLATION (if vernacular preferred)
    # -------------------------------------------------------------------------
    trans_job = ProcessingJob(
        organization_id=org_id,
        consultation_id=consultation.id,
        job_type=JobType.TRANSLATION,
        status=JobStatus.RUNNING,
        started_at=datetime.now(timezone.utc),
    )
    db.add(trans_job)
    db.flush()

    pref_lang = patient.preferred_language if patient else "en-IN"
    if pref_lang != "en-IN":
        translator = get_translation_provider()
        trans_md, trans_json = asyncio.run(
            translator.translate_patient_summary(
                summary_markdown=pat_ver.rendered_markdown,
                structured_json=pat_ver.structured_content_json,
                target_language=pref_lang,
            )
        )
        pat_ver.rendered_markdown = trans_md
        pat_ver.content_sha256 = compute_sha256(trans_md)
        pat_ver.structured_content_json = trans_json

    trans_job.status = JobStatus.COMPLETED
    trans_job.completed_at = datetime.now(timezone.utc)

    # Transition consultation to REVIEW_READY
    consultation.status = ConsultationStatus.REVIEW_READY
    db.commit()
    db.refresh(consultation)
    return consultation


@celery_app.task(name="process_consultation_audio_task")
def process_consultation_audio_task(consultation_id_str: str) -> str:
    """Asynchronous Celery task entrypoint."""
    consultation_id = uuid.UUID(consultation_id_str)
    with SessionLocal() as db:
        process_consultation_pipeline(db, consultation_id)
    return f"Consultation {consultation_id_str} processed successfully."
