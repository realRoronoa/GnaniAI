from datetime import datetime, timezone
import hashlib
import urllib.parse
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_membership,
    get_current_tenant_org_id,
    require_doctor,
)
from app.db.session import get_db
from app.integrations.storage.s3_service import storage_service
from app.models.clinical_reports import (
    MedicationInstruction,
    PdfAsset,
    Report,
    ReportApproval,
    ReportStatus,
    ReportType,
    ReportVersion,
)
from app.models.consultations_audio import Consultation
from app.models.enums import AppointmentStatus, ConsultationStatus, DeliveryChannel, PdfType, UserRole, enum_val
from app.models.patients_appointments import Appointment, Patient
from app.models.system_audit import AuditEvent, SecureShareGrant
from app.models.tenant import DoctorProfile, Organization, OrganizationMembership, User
from app.services.pdf_service import PDFService

router = APIRouter(prefix="/consultations/{consultation_id}", tags=["Clinical Reports, Approvals & Delivery"])


class ReportEditRequest(BaseModel):
    rendered_markdown: str | None = None
    structured_content_json: dict[str, Any] | None = None
    sections_json: dict[str, Any] | None = None


def normalize_report_types(rt: ReportType | str) -> list[ReportType]:
    val = enum_val(rt)
    if val in ("DOCTOR_CLINICAL", "DOCTOR_NOTE"):
        return [ReportType.DOCTOR_CLINICAL, ReportType.DOCTOR_NOTE]
    return [ReportType.PATIENT_SUMMARY]


class MarkSharedRequest(BaseModel):
    delivery_channel: DeliveryChannel = DeliveryChannel.MANUAL_WHATSAPP
    recipient_contact: str = Field(..., min_length=5, max_length=100)


def compute_sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


# -----------------------------------------------------------------------------
# 1. Get & Edit Dual Reports
# -----------------------------------------------------------------------------
@router.get("/reports")
def get_consultation_reports(
    consultation_id: uuid.UUID,
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    membership: Annotated[OrganizationMembership, Depends(get_current_membership)],
    db: Annotated[Session, Depends(get_db)],
) -> list[dict[str, Any]]:
    consultation = db.get(Consultation, consultation_id)
    if not consultation or consultation.organization_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation session not found.")

    reports = db.execute(
        select(Report).where(Report.consultation_id == consultation_id).order_by(Report.created_at.asc())
    ).scalars().all()

    result = []
    for r in reports:
        # Receptionist access rule: can only view approved patient summaries
        is_rec = enum_val(membership.role) == "RECEPTIONIST"
        if is_rec and (enum_val(r.report_type) != "PATIENT_SUMMARY" or enum_val(r.current_status) != "APPROVED"):
            continue

        versions = db.execute(
            select(ReportVersion).where(ReportVersion.report_id == r.id).order_by(ReportVersion.version_number.desc())
        ).scalars().all()

        current_ver = versions[0] if versions else None

        result.append({
            "report_id": str(r.id),
            "report_type": enum_val(r.report_type),
            "current_status": enum_val(r.current_status),
            "current_version_number": r.current_version_number,
            "target_language": r.target_language,
            "content_markdown": current_ver.rendered_markdown if current_ver else "",
            "content_sha256": current_ver.content_sha256 if current_ver else "",
            "all_versions": [
                {
                    "id": str(v.id),
                    "version_number": v.version_number,
                    "status": enum_val(v.status),
                    "created_at": v.created_at.isoformat(),
                    "content_sha256": v.content_sha256,
                }
                for v in versions
            ],
        })

    return result


@router.put("/reports/{report_type}")
@router.patch("/reports/{report_type}")
def edit_report(
    consultation_id: uuid.UUID,
    report_type: ReportType,
    data: ReportEditRequest,
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    membership: Annotated[OrganizationMembership, Depends(require_doctor)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Doctor clinical edit to a report.
    Rule (Part 9.3): If previously APPROVED, the existing approved version is marked SUPERSEDED,
    and a new version is created in DOCTOR_EDITED_DRAFT status, requiring re-approval.
    """
    consultation = db.get(Consultation, consultation_id)
    if not consultation or consultation.organization_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation session not found.")

    report = db.execute(
        select(Report).where(
            Report.consultation_id == consultation_id,
            Report.report_type.in_(normalize_report_types(report_type)),
        ).order_by(Report.created_at.desc())
    ).scalars().first()

    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found for this encounter.")

    current_ver = db.execute(
        select(ReportVersion)
        .where(
            ReportVersion.report_id == report.id,
            ReportVersion.version_number == report.current_version_number,
        ).order_by(ReportVersion.version_number.desc())
    ).scalars().first()

    markdown_content = data.rendered_markdown
    if not markdown_content:
        struct = data.sections_json or data.structured_content_json or {}
        markdown_content = "\n\n".join(f"## {k.title()}\n{v}" for k, v in struct.items())
    if not markdown_content:
        markdown_content = "# Clinical Report\n\nNo content provided."

    new_sha256 = compute_sha256(markdown_content)
    new_version_num = report.current_version_number

    if current_ver and enum_val(current_ver.status) == "APPROVED":
        # Supersede approved version and create new version requiring sign-off
        current_ver.status = ReportStatus.SUPERSEDED
        new_version_num += 1
        report.current_version_number = new_version_num
        report.current_status = ReportStatus.DOCTOR_EDITED_DRAFT

        new_ver = ReportVersion(
            report_id=report.id,
            consultation_id=consultation_id,
            version_number=new_version_num,
            status=ReportStatus.DOCTOR_EDITED_DRAFT,
            rendered_markdown=markdown_content,
            structured_content_json=data.structured_content_json or data.sections_json or current_ver.structured_content_json,
            created_by_user_id=membership.user_id,
            content_sha256=new_sha256,
        )
        db.add(new_ver)
    elif current_ver:
        # Update existing unapproved draft
        current_ver.rendered_markdown = markdown_content
        current_ver.content_sha256 = new_sha256
        current_ver.status = ReportStatus.DOCTOR_EDITED_DRAFT
        report.current_status = ReportStatus.DOCTOR_EDITED_DRAFT
        if data.structured_content_json:
            current_ver.structured_content_json = data.structured_content_json
    else:
        new_ver = ReportVersion(
            report_id=report.id,
            consultation_id=consultation_id,
            version_number=1,
            status=ReportStatus.DOCTOR_EDITED_DRAFT,
            rendered_markdown=data.rendered_markdown,
            structured_content_json=data.structured_content_json or {},
            created_by_user_id=membership.user_id,
            content_sha256=new_sha256,
        )
        db.add(new_ver)
        report.current_status = ReportStatus.DOCTOR_EDITED_DRAFT

    audit = AuditEvent(
        organization_id=org_id,
        actor_user_id=membership.user_id,
        actor_role="DOCTOR",
        event_type="REPORT_EDITED_BY_DOCTOR",
        resource_type="REPORT",
        resource_id=report.id,
        action="UPDATE",
        metadata_json={
            "report_type": enum_val(report.report_type),
            "version_number": new_version_num,
            "status": enum_val(report.current_status),
        },
    )
    db.add(audit)

    db.commit()
    return {
        "message": "Report updated successfully.",
        "report_id": str(report.id),
        "version_number": new_version_num,
        "status": enum_val(report.current_status),
    }


# -----------------------------------------------------------------------------
# 2. Doctor-Only Digital Report Approval & PDF Generation
# -----------------------------------------------------------------------------
@router.post("/approve")
def approve_consultation_reports(
    consultation_id: uuid.UUID,
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    membership: Annotated[OrganizationMembership, Depends(require_doctor)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Doctor-Only Final Sign-Off:
    Rules:
    - Strictly DOCTOR role only.
    - Verified that all active medication instructions have doctor_verified=True and no unresolved flags.
    - Digitally signs both reports, generates PDFs with ReportLab, and stores them privately in S3.
    """
    consultation = db.get(Consultation, consultation_id)
    if not consultation or consultation.organization_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation session not found.")

    if consultation.doctor_user_id != membership.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the attending doctor can digitally approve encounter notes.",
        )

    # 1. Safety Check: Verify all medications are explicitly verified and have no unresolved missing dosage flags
    unverified_meds = db.execute(
        select(MedicationInstruction).where(
            MedicationInstruction.consultation_id == consultation_id,
            MedicationInstruction.is_historical == False,
            (MedicationInstruction.doctor_verified == False) | (MedicationInstruction.uncertainty_flags_json != []),
        )
    ).scalars().all()

    if unverified_meds:
        med_names = [m.medication_name for m in unverified_meds]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve: Medications have unresolved dosage/duration uncertainty: {', '.join(med_names)}. Please verify all prescriptions first.",
        )

    # Fetch context
    reports = db.execute(
        select(Report).where(Report.consultation_id == consultation_id)
    ).scalars().all()

    if not reports:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No reports exist to approve.")

    patient = db.get(Patient, consultation.patient_id)
    doctor = db.get(User, consultation.doctor_user_id)
    doc_prof = db.execute(select(DoctorProfile).where(DoctorProfile.user_id == doctor.id)).scalars().first()
    org = db.get(Organization, org_id)

    now = datetime.now(timezone.utc)
    approved_assets = []

    for r in reports:
        current_ver = db.execute(
            select(ReportVersion).where(
                ReportVersion.report_id == r.id,
                ReportVersion.version_number == r.current_version_number,
            ).order_by(ReportVersion.version_number.desc())
        ).scalars().first()

        if not current_ver:
            continue

        # Set status to APPROVED
        current_ver.status = ReportStatus.APPROVED
        r.current_status = ReportStatus.APPROVED

        # Cryptographic Signature Hash
        sig_hash = compute_sha256(f"{current_ver.content_sha256}:{doctor.id}:{now.isoformat()}")

        approval = ReportApproval(
            organization_id=org_id,
            consultation_id=consultation.id,
            report_id=r.id,
            report_version_id=current_ver.id,
            approved_by_doctor_id=doctor.id,
            approval_notes="Approved via Doctor Clinical Sign-Off.",
            signature_hash=sig_hash,
            approved_at=now,
        )
        db.add(approval)

        # Generate PDF using ReportLab
        pdf_type = PdfType.DOCTOR_REPORT_PDF if enum_val(r.report_type) == "DOCTOR_CLINICAL" else PdfType.PATIENT_SUMMARY_PDF
        pdf_bytes = PDFService.generate_pdf(
            pdf_type=pdf_type,
            clinic_name=org.name if org else "ArogyaScribe Clinic",
            clinic_phone=org.contact_phone if org else "",
            doctor_name=doctor.full_name,
            doctor_specialization=doc_prof.specialization if doc_prof else "General Medicine",
            patient_name=patient.full_name if patient else "Patient",
            patient_identifier=patient.patient_identifier if patient else "",
            patient_age=str(patient.age_years) if (patient and patient.age_years) else "N/A",
            patient_gender=patient.gender if patient else "N/A",
            content_markdown=current_ver.rendered_markdown,
            signature_hash=sig_hash,
            approved_at=now,
        )

        pdf_sha256 = hashlib.sha256(pdf_bytes).hexdigest()
        pdf_asset_id = uuid.uuid4()
        storage_key = f"orgs/{org_id}/consultations/{consultation.id}/pdfs/{pdf_asset_id}.pdf"
        storage_service.put_object(storage_key, pdf_bytes, "application/pdf")

        pdf_asset = PdfAsset(
            id=pdf_asset_id,
            organization_id=org_id,
            consultation_id=consultation.id,
            report_id=r.id,
            report_version_id=current_ver.id,
            pdf_type=pdf_type,
            storage_key=storage_key,
            file_size_bytes=len(pdf_bytes),
            checksum_sha256=pdf_sha256,
            generated_at=now,
        )
        db.add(pdf_asset)

        approved_assets.append({
            "report_type": enum_val(r.report_type),
            "pdf_type": enum_val(pdf_type),
            "pdf_asset_id": str(pdf_asset.id),
            "signature_hash": sig_hash,
        })

    # Conclude Consultation & Linked Appointment
    consultation.status = ConsultationStatus.APPROVED
    consultation.ended_at = now

    if consultation.appointment_id:
        appointment = db.get(Appointment, consultation.appointment_id)
        if appointment:
            appointment.status = AppointmentStatus.COMPLETED
            appointment.completed_at = now

    audit = AuditEvent(
        organization_id=org_id,
        actor_user_id=doctor.id,
        actor_role="DOCTOR",
        event_type="CONSULTATION_APPROVED",
        resource_type="CONSULTATION",
        resource_id=consultation.id,
        action="APPROVE",
        metadata_json={"approved_assets": approved_assets},
    )
    db.add(audit)

    db.commit()

    return {
        "approved": True,
        "message": "Consultation and clinical reports successfully approved and signed.",
        "consultation_status": enum_val(consultation.status),
        "approved_reports": approved_assets,
        "pdf_assets": approved_assets,
    }


# -----------------------------------------------------------------------------
# 3. PDF Download & Delivery
# -----------------------------------------------------------------------------
@router.get("/pdfs/{pdf_type}/download")
def download_pdf(
    consultation_id: uuid.UUID,
    pdf_type: PdfType,
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    membership: Annotated[OrganizationMembership, Depends(get_current_membership)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    consultation = db.get(Consultation, consultation_id)
    if not consultation or consultation.organization_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation session not found.")

    # Role enforcement: Receptionists can only download PATIENT_SUMMARY_PDF
    if enum_val(membership.role) == "RECEPTIONIST" and pdf_type != PdfType.PATIENT_SUMMARY_PDF:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Receptionists are permitted to download Patient Summary PDFs only.",
        )

    pdf_bytes = None
    pdf_asset = db.execute(
        select(PdfAsset).where(
            PdfAsset.consultation_id == consultation_id,
            PdfAsset.pdf_type == pdf_type,
        ).order_by(PdfAsset.generated_at.desc())
    ).scalars().first()

    if pdf_asset:
        try:
            pdf_bytes = storage_service.get_object_bytes(pdf_asset.storage_key)
        except Exception:
            pdf_bytes = None

    # Resilient fallback: Dynamically generate PDF on the fly using ReportLab!
    if not pdf_bytes:
        org = db.get(Organization, org_id)
        doctor = db.get(User, consultation.doctor_user_id) if consultation.doctor_user_id else None
        doc_prof = (
            db.execute(select(DoctorProfile).where(DoctorProfile.user_id == consultation.doctor_user_id)).scalars().first()
            if consultation.doctor_user_id
            else None
        )
        patient = db.get(Patient, consultation.patient_id) if consultation.patient_id else None

        target_report_type = (
            ReportType.DOCTOR_CLINICAL if pdf_type == PdfType.DOCTOR_REPORT_PDF else ReportType.PATIENT_SUMMARY
        )
        rep = db.execute(
            select(Report).where(
                Report.consultation_id == consultation_id,
                Report.report_type == target_report_type,
            ).order_by(Report.created_at.desc())
        ).scalars().first()

        current_ver = None
        if rep:
            current_ver = db.execute(
                select(ReportVersion).where(
                    ReportVersion.report_id == rep.id,
                    ReportVersion.version_number == rep.current_version_number,
                ).order_by(ReportVersion.version_number.desc())
            ).scalars().first()

        content_markdown = (
            current_ver.rendered_markdown
            if current_ver
            else f"# Clinical Documentation\nEncounter recorded for {patient.full_name if patient else 'Patient'}."
        )
        now = datetime.now(timezone.utc)
        sig_hash = compute_sha256(f"{content_markdown}:{doctor.id if doctor else 'doc'}:{now.isoformat()}")

        pdf_bytes = PDFService.generate_pdf(
            pdf_type=pdf_type,
            clinic_name=org.name if org else "ArogyaScribe Clinic",
            clinic_phone=org.contact_phone if org else "",
            doctor_name=doctor.full_name if doctor else "Attending Doctor",
            doctor_specialization=doc_prof.specialization if doc_prof else "General Medicine",
            patient_name=patient.full_name if patient else "Patient",
            patient_identifier=patient.patient_identifier if patient else "",
            patient_age=str(patient.age_years) if (patient and patient.age_years) else "N/A",
            patient_gender=patient.gender if patient else "N/A",
            content_markdown=content_markdown,
            signature_hash=sig_hash,
            approved_at=now,
        )

    filename = f"{enum_val(pdf_type).lower()}_{consultation_id}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/reports/{report_type}/pdf")
def download_report_pdf(
    consultation_id: uuid.UUID,
    report_type: ReportType,
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    membership: Annotated[OrganizationMembership, Depends(get_current_membership)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    pdf_type = PdfType.DOCTOR_REPORT_PDF if report_type in (ReportType.DOCTOR_NOTE, ReportType.DOCTOR_CLINICAL) else PdfType.PATIENT_SUMMARY_PDF
    return download_pdf(
        consultation_id=consultation_id,
        pdf_type=pdf_type,
        org_id=org_id,
        membership=membership,
        db=db,
    )


@router.get("/delivery-options")
@router.get("/reports/patient-summary/share-link")
def get_delivery_options(
    consultation_id: uuid.UUID,
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    _: Annotated[OrganizationMembership, Depends(get_current_membership)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    consultation = db.get(Consultation, consultation_id)
    if not consultation or consultation.organization_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation session not found.")

    patient = db.get(Patient, consultation.patient_id)
    doctor = db.get(User, consultation.doctor_user_id)
    org = db.get(Organization, org_id)

    # Clean phone digits for wa.me
    phone_digits = "".join(c for c in (patient.mobile_number if patient else "") if c.isdigit())
    if len(phone_digits) == 10:
        phone_digits = "91" + phone_digits

    message_text = (
        f"Namaste {patient.full_name if patient else ''},\n\n"
        f"Your visit summary from Dr. {doctor.full_name if doctor else ''} at {org.name if org else ''} is ready.\n\n"
        f"Please contact us if your symptoms worsen."
    )
    encoded_msg = urllib.parse.quote(message_text)
    whatsapp_url = f"https://wa.me/{phone_digits}?text={encoded_msg}" if phone_digits else None
    email_url = f"mailto:{patient.email}?subject=Your Visit Summary&body={encoded_msg}" if (patient and patient.email) else None

    return {
        "patient_name": patient.full_name if patient else "",
        "mobile_number": patient.mobile_number if patient else "",
        "email": patient.email if patient else None,
        "whatsapp_url": whatsapp_url,
        "email_url": email_url,
        "message_preview": message_text,
    }


@router.post("/mark-shared")
@router.post("/reports/patient-summary/mark-shared")
def mark_delivery_shared(
    consultation_id: uuid.UUID,
    data: MarkSharedRequest,
    org_id: Annotated[uuid.UUID, Depends(get_current_tenant_org_id)],
    membership: Annotated[OrganizationMembership, Depends(get_current_membership)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    consultation = db.get(Consultation, consultation_id)
    if not consultation or consultation.organization_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation session not found.")

    pdf_asset = db.execute(
        select(PdfAsset).where(
            PdfAsset.consultation_id == consultation_id,
            PdfAsset.pdf_type == PdfType.PATIENT_SUMMARY_PDF,
        ).order_by(PdfAsset.generated_at.desc())
    ).scalar_one_or_none()

    grant = SecureShareGrant(
        organization_id=org_id,
        consultation_id=consultation.id,
        patient_id=consultation.patient_id,
        pdf_asset_id=pdf_asset.id if pdf_asset else None,
        shared_by_user_id=membership.user_id,
        delivery_channel=data.delivery_channel,
        recipient_contact=data.recipient_contact,
        manually_confirmed_sent=True,
        confirmed_at=datetime.now(timezone.utc),
    )
    db.add(grant)
    db.flush()

    audit = AuditEvent(
        organization_id=org_id,
        actor_user_id=membership.user_id,
        actor_role=enum_val(membership.role),
        event_type="PATIENT_SUMMARY_SHARED_MANUALLY",
        resource_type="SECURE_SHARE_GRANT",
        resource_id=grant.id,
        action="CREATE",
        metadata_json={
            "channel": enum_val(data.delivery_channel),
            "recipient_contact": data.recipient_contact,
        },
    )
    db.add(audit)

    db.commit()
    return {
        "status": "MARKED_SHARED",
        "message": "Delivery logged successfully.",
        "grant_id": str(grant.id),
        "delivery_channel": enum_val(grant.delivery_channel),
        "confirmed_at": grant.confirmed_at.isoformat(),
    }
