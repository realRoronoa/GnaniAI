from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant_org_id, require_doctor
from app.db.session import get_db
from app.integrations.storage.s3_service import storage_service
from app.models.clinical_reports import (
    ClinicalFact,
    ClinicalFactEvidence,
    MedicationInstruction,
    PdfAsset,
    Report,
    ReportApproval,
    ReportVersion,
)
from app.models.consultations_audio import (
    AudioAsset,
    ConsentRecord,
    Consultation,
    TranscriptSegment,
    TranscriptVersion,
)
from app.models.enums import AudioUploadStatus, ConsultationStatus, enum_val
from app.models.subscriptions import UsageRecord
from app.models.system_audit import AuditEvent
from app.models.tenant import OrganizationMembership
from app.workers.tasks import process_consultation_pipeline

router = APIRouter(tags=["Audio Recording & Processing Pipeline"])

ALLOWED_AUDIO_TYPES = {
    "audio/webm",
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/mp4",
    "audio/mpeg",
    "audio/ogg",
    "application/octet-stream",  # Raw PCM
}
MAX_AUDIO_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB


@router.post("/consultations/{consultation_id}/audio", status_code=status.HTTP_201_CREATED)
async def upload_consultation_audio(
    consultation_id: uuid.UUID,
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    membership: Annotated[OrganizationMembership, Depends(require_doctor)],
    db: Annotated[Session, Depends(get_db)],
    audio_file: UploadFile = File(...),
    transcript_text: str | None = Form(default=None),
) -> dict[str, Any]:
    """Uploads recorded encounter audio.
    Rule (Part 5.3 & 6): Strictly blocked unless specific patient consent has been captured and not withdrawn.
    """
    consultation = db.get(Consultation, consultation_id)
    if not consultation or consultation.organization_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation session not found.")

    if consultation.doctor_user_id != membership.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the attending doctor can upload encounter recordings.",
        )

    # 1. Mandatory Consent Gate Verification
    consent = db.execute(
        select(ConsentRecord).where(
            ConsentRecord.consultation_id == consultation_id,
            ConsentRecord.is_granted.is_(True),
            ConsentRecord.withdrawn_at.is_(None),
        )
    ).scalar_one_or_none()

    if not consent:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Audio recording forbidden: Informed patient consent has not been granted or has been withdrawn.",
        )

    # 2. Content-Type and payload validation
    content_type = audio_file.content_type or "audio/wav"
    if content_type.lower() not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported audio format '{content_type}'. Allowed: webm, wav, mp4, mpeg, ogg.",
        )

    data = await audio_file.read()
    if not data or len(data) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio file payload is empty.",
        )

    if len(data) > MAX_AUDIO_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Audio file exceeds {MAX_AUDIO_SIZE_BYTES // (1024 * 1024)} MB limit.",
        )

    # 3. Store securely in private S3/MinIO
    sha256_checksum = hashlib.sha256(data).hexdigest()
    asset_id = uuid.uuid4()
    ext = "webm" if "webm" in content_type else "wav"
    storage_key = f"orgs/{org_id}/consultations/{consultation_id}/audio/{asset_id}.{ext}"

    storage_service.put_object(storage_key, data, content_type)

    if transcript_text and transcript_text.strip():
        storage_service.put_object(
            f"orgs/{org_id}/consultations/{consultation_id}/audio/live_transcript.txt",
            transcript_text.strip().encode("utf-8"),
            "text/plain",
        )

    # 4. Save metadata in database
    duration_approx = Decimal(str(round(len(data) / 32000.0, 2)))  # Rough estimate ~ 16kHz 16-bit mono
    if duration_approx <= Decimal("0.0"):
        duration_approx = Decimal("1.0")

    audio_asset = AudioAsset(
        id=asset_id,
        organization_id=org_id,
        consultation_id=consultation.id,
        storage_key=storage_key,
        content_type=content_type,
        file_size_bytes=len(data),
        duration_seconds=duration_approx,
        checksum_sha256=sha256_checksum,
        upload_status=AudioUploadStatus.UPLOADED,
    )
    db.add(audio_asset)

    consultation.status = ConsultationStatus.RECORDING

    # Update usage record
    month_str = datetime.now(timezone.utc).strftime("%Y-%m")
    usage = db.execute(
        select(UsageRecord).where(
            UsageRecord.organization_id == org_id,
            UsageRecord.period_month == month_str,
        )
    ).scalar_one_or_none()
    if usage:
        usage.audio_storage_bytes_used += len(data)

    audit = AuditEvent(
        organization_id=org_id,
        actor_user_id=membership.user_id,
        actor_role="DOCTOR",
        event_type="AUDIO_ENCOUNTER_UPLOADED",
        resource_type="AUDIO_ASSET",
        resource_id=audio_asset.id,
        action="CREATE",
        metadata_json={
            "file_size_bytes": len(data),
            "checksum_sha256": sha256_checksum,
            "duration_seconds": float(duration_approx),
        },
    )
    db.add(audit)

    db.commit()

    return {
        "message": "Audio asset uploaded successfully.",
        "audio_asset_id": str(audio_asset.id),
        "checksum_sha256": sha256_checksum,
        "consultation_status": enum_val(consultation.status),
    }


class ProcessConsultationRequest(BaseModel):
    transcript_text: str | None = None
    is_sample_demo: bool = False


@router.post("/consultations/{consultation_id}/process")
def trigger_consultation_processing(
    consultation_id: uuid.UUID,
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    membership: Annotated[OrganizationMembership, Depends(require_doctor)],
    db: Annotated[Session, Depends(get_db)],
    payload: ProcessConsultationRequest | None = None,
) -> dict[str, Any]:
    """Runs the clinical AI pipeline (transcription, fact extraction, dual report generation)."""
    consultation = db.get(Consultation, consultation_id)
    if not consultation or consultation.organization_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation session not found.")

    if consultation.doctor_user_id != membership.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized access to consultation.")

    live_text = payload.transcript_text.strip() if (payload and payload.transcript_text) else None
    if live_text:
        try:
            storage_service.put_object(
                f"orgs/{org_id}/consultations/{consultation_id}/audio/live_transcript.txt",
                live_text.encode("utf-8"),
                "text/plain",
            )
        except Exception:
            pass

    is_sample = payload.is_sample_demo if payload else False
    updated_cons = process_consultation_pipeline(
        db, consultation_id, transcript_text=live_text, is_sample_demo=is_sample
    )

    return {
        "message": "Consultation processed successfully.",
        "consultation_id": str(consultation_id),
        "status": enum_val(updated_cons.status),
        "chief_complaint": updated_cons.chief_complaint_summary,
    }


@router.delete("/consultations/{consultation_id}/reset")
def reset_consultation_data(
    consultation_id: uuid.UUID,
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    membership: Annotated[OrganizationMembership, Depends(require_doctor)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Wipes all transcripts, clinical facts, medications, reports, and audio assets for this consultation."""
    consultation = db.get(Consultation, consultation_id)
    if not consultation or consultation.organization_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation session not found.")

    if consultation.doctor_user_id != membership.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized access to consultation.")

    db.execute(delete(PdfAsset).where(PdfAsset.consultation_id == consultation_id))
    db.execute(delete(ReportApproval).where(ReportApproval.consultation_id == consultation_id))
    db.execute(delete(ReportVersion).where(ReportVersion.consultation_id == consultation_id))
    db.execute(delete(Report).where(Report.consultation_id == consultation_id))
    db.execute(delete(MedicationInstruction).where(MedicationInstruction.consultation_id == consultation_id))
    fact_ids_subq = select(ClinicalFact.id).where(ClinicalFact.consultation_id == consultation_id)
    db.execute(delete(ClinicalFactEvidence).where(ClinicalFactEvidence.clinical_fact_id.in_(fact_ids_subq)))
    db.execute(delete(ClinicalFact).where(ClinicalFact.consultation_id == consultation_id))
    db.execute(delete(TranscriptSegment).where(TranscriptSegment.consultation_id == consultation_id))
    db.execute(delete(TranscriptVersion).where(TranscriptVersion.consultation_id == consultation_id))
    db.execute(delete(AudioAsset).where(AudioAsset.consultation_id == consultation_id))

    consultation.chief_complaint_summary = None
    consultation.status = ConsultationStatus.IN_PROGRESS
    db.commit()

    return {
        "message": "Consultation documentation wiped and reset successfully.",
        "consultation_id": str(consultation_id),
    }
