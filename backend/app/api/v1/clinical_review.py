import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_membership, get_current_tenant_org_id, require_doctor
from app.db.session import get_db
from app.models.clinical_reports import ClinicalFact, ClinicalFactEvidence, MedicationInstruction
from app.models.consultations_audio import Consultation, TranscriptSegment, TranscriptVersion
from app.models.enums import DoctorReviewStatus, SpeakerLabel, TranscriptSourceType, enum_val
from app.models.system_audit import AuditEvent
from app.models.tenant import OrganizationMembership

router = APIRouter(prefix="/consultations/{consultation_id}", tags=["Transcript & Clinical Review"])


class SegmentCorrectionItem(BaseModel):
    segment_id: uuid.UUID
    corrected_text: str = Field(..., min_length=1)
    speaker_label: str | None = None


class TranscriptEditRequest(BaseModel):
    segments: list[SegmentCorrectionItem]


class FactReviewUpdate(BaseModel):
    doctor_review_status: DoctorReviewStatus
    edited_fact_value: dict[str, Any] | None = None


class MedicationUpdate(BaseModel):
    medication_name: str | None = None
    strength: str | None = None
    dosage: str | None = None
    route: str | None = None
    frequency: str | None = None
    duration: str | None = None
    special_instructions: str | None = None
    doctor_verified: bool = True


# -----------------------------------------------------------------------------
# 1. Transcript Review & Editing
# -----------------------------------------------------------------------------
@router.get("/transcript")
def get_transcript(
    consultation_id: uuid.UUID,
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    _: Annotated[OrganizationMembership, Depends(get_current_membership)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    consultation = db.get(Consultation, consultation_id)
    if not consultation or consultation.organization_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation session not found.")

    version = db.execute(
        select(TranscriptVersion).where(
            TranscriptVersion.consultation_id == consultation_id,
            TranscriptVersion.is_current == True,
        )
    ).scalar_one_or_none()

    if not version:
        return {"version_number": 0, "full_text": "", "segments": []}

    segments = db.execute(
        select(TranscriptSegment)
        .where(TranscriptSegment.transcript_version_id == version.id)
        .order_by(TranscriptSegment.sequence_number.asc())
    ).scalars().all()

    return {
        "transcript_version_id": str(version.id),
        "version_number": version.version_number,
        "source_type": enum_val(version.source_type),
        "language_detected": version.language_detected,
        "full_text": version.full_text,
        "segments": [
            {
                "id": str(s.id),
                "sequence_number": s.sequence_number,
                "speaker_label": enum_val(s.speaker_label),
                "start_time_ms": s.start_time_ms,
                "end_time_ms": s.end_time_ms,
                "original_text": s.original_text,
                "corrected_text": s.corrected_text,
                "effective_text": s.corrected_text or s.original_text,
                "confidence_score": float(s.confidence_score),
            }
            for s in segments
        ],
    }


@router.put("/transcript")
@router.patch("/transcript")
def edit_transcript(
    consultation_id: uuid.UUID,
    data: TranscriptEditRequest,
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    membership: Annotated[OrganizationMembership, Depends(require_doctor)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Doctor corrections to transcript: preserves original AI text while recording corrected text."""
    consultation = db.get(Consultation, consultation_id)
    if not consultation or consultation.organization_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation session not found.")

    current_ver = db.execute(
        select(TranscriptVersion).where(
            TranscriptVersion.consultation_id == consultation_id,
            TranscriptVersion.is_current == True,
        )
    ).scalar_one_or_none()

    if not current_ver:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No transcript exists to edit.")

    corrections_map = {item.segment_id: item for item in data.segments}
    segments = db.execute(
        select(TranscriptSegment)
        .where(TranscriptSegment.transcript_version_id == current_ver.id)
        .order_by(TranscriptSegment.sequence_number.asc())
    ).scalars().all()

    # Create new DOCTOR_EDITED version
    current_ver.is_current = False
    new_ver = TranscriptVersion(
        organization_id=org_id,
        consultation_id=consultation_id,
        version_number=current_ver.version_number + 1,
        source_type=TranscriptSourceType.DOCTOR_EDITED,
        full_text="",
        original_ai_text=current_ver.original_ai_text,
        language_detected=current_ver.language_detected,
        created_by_user_id=membership.user_id,
        is_current=True,
    )
    db.add(new_ver)
    db.flush()

    new_segments_text = []
    for s in segments:
        corr = corrections_map.get(s.id)
        corrected_txt = corr.corrected_text if corr else s.corrected_text
        speaker = SpeakerLabel(corr.speaker_label) if (corr and corr.speaker_label in SpeakerLabel.__members__) else s.speaker_label

        new_seg = TranscriptSegment(
            transcript_version_id=new_ver.id,
            consultation_id=consultation_id,
            sequence_number=s.sequence_number,
            speaker_label=speaker,
            start_time_ms=s.start_time_ms,
            end_time_ms=s.end_time_ms,
            original_text=s.original_text,  # Immutable AI text
            corrected_text=corrected_txt,
            confidence_score=s.confidence_score,
        )
        db.add(new_seg)
        new_segments_text.append(corrected_txt or s.original_text)

    new_ver.full_text = " ".join(new_segments_text)

    audit = AuditEvent(
        organization_id=org_id,
        actor_user_id=membership.user_id,
        actor_role="DOCTOR",
        event_type="TRANSCRIPT_EDITED_BY_DOCTOR",
        resource_type="TRANSCRIPT_VERSION",
        resource_id=new_ver.id,
        action="UPDATE",
        metadata_json={"version_number": new_ver.version_number},
    )
    db.add(audit)

    db.commit()

    return {
        "message": "Transcript updated successfully.",
        "version_number": new_ver.version_number,
        "source_type": enum_val(new_ver.source_type),
        "full_text": new_ver.full_text,
    }


# -----------------------------------------------------------------------------
# 2. Clinical Facts & Evidence Grounding Review
# -----------------------------------------------------------------------------
@router.get("/clinical-facts")
@router.get("/facts")
def get_clinical_facts(
    consultation_id: uuid.UUID,
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    _: Annotated[OrganizationMembership, Depends(get_current_membership)],
    db: Annotated[Session, Depends(get_db)],
) -> list[dict[str, Any]]:
    consultation = db.get(Consultation, consultation_id)
    if not consultation or consultation.organization_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation session not found.")

    facts = db.execute(
        select(ClinicalFact).where(ClinicalFact.consultation_id == consultation_id).order_by(ClinicalFact.created_at.asc())
    ).scalars().all()

    result = []
    for f in facts:
        # Load evidence grounding
        evidence_rows = db.execute(
            select(ClinicalFactEvidence).where(ClinicalFactEvidence.clinical_fact_id == f.id)
        ).scalars().all()

        result.append({
            "id": str(f.id),
            "category": f.category,
            "fact_key": f.fact_key,
            "fact_value": f.fact_value,
            "source_speaker": f.source_speaker,
            "provenance_type": enum_val(f.provenance_type),
            "certainty_status": enum_val(f.certainty_status),
            "doctor_review_status": enum_val(f.doctor_review_status),
            "validation_flags": f.validation_flags_json,
            "evidence": [
                {
                    "transcript_segment_id": str(ev.transcript_segment_id),
                    "evidence_quotation": ev.evidence_quotation,
                    "start_time_ms": ev.start_time_ms,
                    "end_time_ms": ev.end_time_ms,
                }
                for ev in evidence_rows
            ],
        })

    return result


@router.patch("/clinical-facts/{fact_id}")
def review_clinical_fact(
    consultation_id: uuid.UUID,
    fact_id: uuid.UUID,
    data: FactReviewUpdate,
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    membership: Annotated[OrganizationMembership, Depends(require_doctor)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    fact = db.get(ClinicalFact, fact_id)
    if not fact or fact.consultation_id != consultation_id or fact.organization_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinical fact not found.")

    fact.doctor_review_status = data.doctor_review_status
    if data.edited_fact_value is not None:
        fact.fact_value = data.edited_fact_value

    db.commit()
    db.refresh(fact)

    return {
        "id": str(fact.id),
        "doctor_review_status": enum_val(fact.doctor_review_status),
        "fact_value": fact.fact_value,
    }


# -----------------------------------------------------------------------------
# 3. Medications Verification
# -----------------------------------------------------------------------------
@router.get("/medications")
def list_medications(
    consultation_id: uuid.UUID,
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    _: Annotated[OrganizationMembership, Depends(get_current_membership)],
    db: Annotated[Session, Depends(get_db)],
) -> list[dict[str, Any]]:
    consultation = db.get(Consultation, consultation_id)
    if not consultation or consultation.organization_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation session not found.")

    meds = db.execute(
        select(MedicationInstruction).where(MedicationInstruction.consultation_id == consultation_id)
    ).scalars().all()

    return [
        {
            "id": str(m.id),
            "medication_name": m.medication_name,
            "strength": m.strength,
            "dosage": m.dosage,
            "route": m.route,
            "frequency": m.frequency,
            "duration": m.duration,
            "special_instructions": m.special_instructions,
            "uncertainty_flags": m.uncertainty_flags_json,
            "doctor_verified": m.doctor_verified,
            "is_historical": m.is_historical,
        }
        for m in meds
    ]


@router.put("/medications/{med_id}")
@router.patch("/medications/{med_id}")
@router.patch("/medications/{med_id}/verify")
def update_medication(
    consultation_id: uuid.UUID,
    med_id: uuid.UUID,
    data: MedicationUpdate,
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    membership: Annotated[OrganizationMembership, Depends(require_doctor)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Doctor verifies and updates medication instruction before sign-off."""
    med = db.get(MedicationInstruction, med_id)
    if not med or med.consultation_id != consultation_id or med.organization_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medication instruction not found.")

    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(med, field, val)

    # If doctor explicitly verified and supplied required fields, clear uncertainty flags
    if med.dosage and med.frequency and med.duration:
        med.uncertainty_flags_json = []

    med.doctor_verified = data.doctor_verified
    med.verified_by_doctor_id = membership.user_id

    db.commit()
    db.refresh(med)

    return {
        "id": str(med.id),
        "medication_name": med.medication_name,
        "strength": med.strength,
        "dosage": med.dosage,
        "frequency": med.frequency,
        "duration": med.duration,
        "uncertainty_flags": med.uncertainty_flags_json,
        "doctor_verified": med.doctor_verified,
    }
