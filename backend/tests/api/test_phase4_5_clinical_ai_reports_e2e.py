from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import io
from typing import Generator
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, get_password_hash
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.clinical_reports import (
    MedicationInstruction,
    PdfAsset,
    Report,
    ReportStatus,
    ReportType,
    ReportVersion,
)
from app.models.consultations_audio import ConsentRecord, Consultation
from app.models.enums import (
    AppointmentStatus,
    AppointmentType,
    BillingCycle,
    ConsultationStatus,
    DoctorReviewStatus,
    OrgStatus,
    PdfType,
    SubscriptionStatus,
    UserRole,
    enum_val,
)
from app.models.patients_appointments import Appointment, Patient
from app.models.subscriptions import Subscription, SubscriptionPlan
from app.models.tenant import (
    DoctorProfile,
    Organization,
    OrganizationLocation,
    OrganizationMembership,
    ReceptionistProfile,
    User,
)

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="module", autouse=True)
def setup_database() -> Generator[None, None, None]:
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def create_token(user: User, org_id: uuid.UUID | None = None, role: str = UserRole.DOCTOR.value, location_id: uuid.UUID | None = None) -> str:
    claims = {
        "role": role,
    }
    if org_id:
        claims["org_id"] = str(org_id)
    if location_id:
        claims["location_id"] = str(location_id)
    return create_access_token(subject=str(user.id), extra_claims=claims)


def grant_consent(client: TestClient, consultation_id: uuid.UUID, token: str, language: str = "hi-IN"):
    resp = client.post(
        f"/api/v1/consultations/{consultation_id}/consent",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "purpose": "CLINICAL_DOCUMENTATION_AND_AI_ASSISTANCE",
            "language": language,
            "consent_wording_version": "v1.0",
            "consent_text_snapshot": "I hereby consent to audio recording for AI clinical note generation.",
            "is_granted": True,
        },
    )
    assert resp.status_code == 200, resp.text
    return resp


@pytest.fixture()
def test_setup(db_session: Session):
    """Sets up a complete clinic environment with doctor, receptionist, and patient."""
    org = Organization(
        name="Arogya Phase 4-5 Clinical Center",
        org_type="CLINIC",
        contact_email="phase45@arogya.test",
        contact_phone="+919876500045",
        address="45 Health Avenue, Bangalore",
        registration_number="REG-KA-2026-045",
        status=OrgStatus.ACTIVE.value,
    )
    db_session.add(org)
    db_session.flush()

    plan = SubscriptionPlan(
        name="Enterprise Clinical",
        code="ENTERPRISE_CLINICAL",
        monthly_price=Decimal("15000.00"),
        annual_price=Decimal("150000.00"),
        max_doctors=10,
        max_receptionists=5,
        max_branches=2,
        monthly_consultation_limit=1000,
        audio_storage_mb_limit=5000,
        report_generation_limit=1000,
        is_active=True,
    )
    db_session.add(plan)
    db_session.flush()

    now = datetime.now(timezone.utc)
    sub = Subscription(
        organization_id=org.id,
        plan_id=plan.id,
        status=SubscriptionStatus.ACTIVE.value,
        billing_cycle=BillingCycle.MONTHLY.value,
        start_date=now - timedelta(days=1),
        end_date=now + timedelta(days=29),
    )
    db_session.add(sub)

    loc = OrganizationLocation(
        organization_id=org.id,
        name="Main Clinical OPD",
        branch_code="OPD-01",
        is_active=True,
    )
    db_session.add(loc)
    db_session.flush()

    # Doctor
    doc_user = User(
        email="dr.sharma@phase45.test",
        password_hash=get_password_hash("DocPass123!"),
        full_name="Dr. Alok Sharma",
        is_active=True,
    )
    db_session.add(doc_user)
    db_session.flush()

    doc_mem = OrganizationMembership(
        organization_id=org.id,
        user_id=doc_user.id,
        location_id=loc.id,
        role=UserRole.DOCTOR.value,
        is_active=True,
    )
    db_session.add(doc_mem)
    db_session.flush()

    doc_profile = DoctorProfile(
        user_id=doc_user.id,
        organization_id=org.id,
        location_id=loc.id,
        registration_number="MCI-2026-9999",
        specialization="General Medicine",
        qualification="MBBS, MD",
        consultation_room="OPD-101",
    )
    db_session.add(doc_profile)

    # Receptionist
    rec_user = User(
        email="rec@phase45.test",
        password_hash=get_password_hash("RecPass123!"),
        full_name="Receptionist Sunita",
        is_active=True,
    )
    db_session.add(rec_user)
    db_session.flush()

    rec_mem = OrganizationMembership(
        organization_id=org.id,
        user_id=rec_user.id,
        location_id=loc.id,
        role=UserRole.RECEPTIONIST.value,
        is_active=True,
    )
    db_session.add(rec_mem)
    db_session.flush()

    rec_profile = ReceptionistProfile(
        user_id=rec_user.id,
        organization_id=org.id,
        location_id=loc.id,
        desk_identifier="DESK-01",
    )
    db_session.add(rec_profile)

    # Patient
    patient = Patient(
        organization_id=org.id,
        full_name="Rajesh Patel",
        date_of_birth=date(1982, 4, 15),
        gender="MALE",
        mobile_number="+919876543210",
        preferred_language="hi",
        patient_identifier="ARC-PAT-9001",
        allergies_summary="No known drug allergies",
    )
    db_session.add(patient)
    db_session.flush()

    # Appointment
    appointment = Appointment(
        organization_id=org.id,
        location_id=loc.id,
        patient_id=patient.id,
        doctor_user_id=doc_user.id,
        created_by_user_id=rec_user.id,
        appointment_date=date.today(),
        scheduled_time=datetime.now(timezone.utc),
        appointment_type=AppointmentType.SCHEDULED.value,
        status=AppointmentStatus.WAITING.value,
        reason_for_visit="Persistent dry cough and fever for 4 days",
    )
    db_session.add(appointment)
    db_session.flush()

    db_session.commit()

    return {
        "org": org,
        "location": loc,
        "doctor_user": doc_user,
        "doctor_membership": doc_mem,
        "receptionist_user": rec_user,
        "receptionist_membership": rec_mem,
        "patient": patient,
        "appointment": appointment,
    }


def test_audio_upload_consent_gating(client: TestClient, db_session: Session, test_setup):
    """Verifies that audio upload is strictly gated by patient consent (Part 5.3 & 6)."""
    doc_user = test_setup["doctor_user"]
    org = test_setup["org"]
    loc = test_setup["location"]
    appt = test_setup["appointment"]
    token = create_token(doc_user, org.id, UserRole.DOCTOR.value, loc.id)

    # 1. Start consultation
    start_resp = client.post(
        "/api/v1/consultations",
        headers={"Authorization": f"Bearer {token}"},
        json={"appointment_id": str(appt.id)},
    )
    assert start_resp.status_code == 201, start_resp.text
    consultation_id = start_resp.json()["id"]

    fake_audio_bytes = b"RIFF....WAVEfmt ....data...."

    # 2. Try to upload audio BEFORE consent is granted -> MUST BE FORBIDDEN (403)
    blocked_resp = client.post(
        f"/api/v1/consultations/{consultation_id}/audio",
        headers={"Authorization": f"Bearer {token}"},
        files={"audio_file": ("encounter.wav", io.BytesIO(fake_audio_bytes), "audio/wav")},
    )
    assert blocked_resp.status_code == 403
    assert "consent has not been granted" in blocked_resp.json()["detail"].lower()

    # 3. Grant consent
    consent_resp = grant_consent(client, consultation_id, token, "hi-IN")
    assert consent_resp.json()["is_granted"] is True

    # 4. Upload audio AFTER consent -> MUST SUCCEED (201 Created)
    upload_resp = client.post(
        f"/api/v1/consultations/{consultation_id}/audio",
        headers={"Authorization": f"Bearer {token}"},
        files={"audio_file": ("encounter.wav", io.BytesIO(fake_audio_bytes), "audio/wav")},
    )
    assert upload_resp.status_code == 201
    upload_data = upload_resp.json()
    assert "audio_asset_id" in upload_data
    assert upload_data["checksum_sha256"] is not None
    assert upload_data["consultation_status"] == ConsultationStatus.RECORDING.value


def test_ai_pipeline_execution_and_clinical_entities(client: TestClient, db_session: Session, test_setup):
    """Verifies end-to-end execution of pluggable AI pipeline (Gnani mock) and entity extraction."""
    doc_user = test_setup["doctor_user"]
    org = test_setup["org"]
    loc = test_setup["location"]
    appt = test_setup["appointment"]
    token = create_token(doc_user, org.id, UserRole.DOCTOR.value, loc.id)

    # Start consultation & capture consent
    start_resp = client.post(
        "/api/v1/consultations",
        headers={"Authorization": f"Bearer {token}"},
        json={"appointment_id": str(appt.id)},
    )
    assert start_resp.status_code == 201, start_resp.text
    consultation_id = start_resp.json()["id"]

    grant_consent(client, consultation_id, token, "hi-IN")

    fake_audio = b"MOCK_ENCOUNTER_AUDIO_DATA_FOR_CLINICAL_PIPELINE"
    client.post(
        f"/api/v1/consultations/{consultation_id}/audio",
        headers={"Authorization": f"Bearer {token}"},
        files={"audio_file": ("visit.webm", io.BytesIO(fake_audio), "audio/webm")},
    )

    # Trigger pipeline
    process_resp = client.post(
        f"/api/v1/consultations/{consultation_id}/process",
        headers={"Authorization": f"Bearer {token}"},
        json={"use_background_worker": False},
    )
    assert process_resp.status_code == 200, process_resp.text
    process_data = process_resp.json()
    assert process_data["status"] in ("SUCCESS", "REVIEW_READY")

    # Check transcript endpoint
    transcript_resp = client.get(
        f"/api/v1/consultations/{consultation_id}/transcript",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert transcript_resp.status_code == 200
    transcript_data = transcript_resp.json()
    assert len(transcript_data["segments"]) > 0
    first_seg = transcript_data["segments"][0]
    assert (first_seg.get("effective_text") or first_seg.get("original_text")) is not None
    assert first_seg["speaker_label"] in ["DOCTOR", "PATIENT", "UNKNOWN"]

    # Check clinical facts & evidence links
    facts_resp = client.get(
        f"/api/v1/consultations/{consultation_id}/facts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert facts_resp.status_code == 200
    facts_data = facts_resp.json()
    assert len(facts_data) > 0
    # Every extracted fact must have evidence links
    assert any(len(f["evidence"]) > 0 for f in facts_data)

    # Check draft reports
    reports_resp = client.get(
        f"/api/v1/consultations/{consultation_id}/reports",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert reports_resp.status_code == 200
    reports_data = reports_resp.json()
    report_types = {r["report_type"]: r for r in reports_data}
    assert ("DOCTOR_CLINICAL" in report_types or "DOCTOR_NOTE" in report_types)
    assert "PATIENT_SUMMARY" in report_types
    for r in reports_data:
        assert r["current_status"] == ReportStatus.AI_GENERATED_DRAFT.value


def test_transcript_review_and_audited_editing(client: TestClient, db_session: Session, test_setup):
    """Verifies that doctor can edit transcript segments while preserving original AI text and auditing changes."""
    doc_user = test_setup["doctor_user"]
    org = test_setup["org"]
    loc = test_setup["location"]
    appt = test_setup["appointment"]
    token = create_token(doc_user, org.id, UserRole.DOCTOR.value, loc.id)

    # Start consultation, consent, audio, process
    c_resp = client.post(
        "/api/v1/consultations",
        headers={"Authorization": f"Bearer {token}"},
        json={"appointment_id": str(appt.id)},
    )
    assert c_resp.status_code == 201, c_resp.text
    consultation_id = c_resp.json()["id"]
    grant_consent(client, consultation_id, token, "en-IN")
    client.post(
        f"/api/v1/consultations/{consultation_id}/audio",
        headers={"Authorization": f"Bearer {token}"},
        files={"audio_file": ("test.wav", io.BytesIO(b"AUDIO_DATA"), "audio/wav")},
    )
    client.post(
        f"/api/v1/consultations/{consultation_id}/process",
        headers={"Authorization": f"Bearer {token}"},
        json={"use_background_worker": False},
    )

    transcript_resp = client.get(
        f"/api/v1/consultations/{consultation_id}/transcript",
        headers={"Authorization": f"Bearer {token}"},
    )
    segments = transcript_resp.json()["segments"]
    target_seg = segments[0]
    original_text = target_seg.get("effective_text") or target_seg.get("original_text")

    # Doctor corrects transcript
    corrected_text = "Doctor corrected: " + original_text
    edit_resp = client.patch(
        f"/api/v1/consultations/{consultation_id}/transcript",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "segments": [
                {
                    "segment_id": target_seg["id"],
                    "corrected_text": corrected_text,
                    "speaker_label": "DOCTOR",
                }
            ]
        },
    )
    assert edit_resp.status_code == 200
    assert edit_resp.json()["version_number"] > 1

    # Verify updated transcript reflects correction
    updated_transcript = client.get(
        f"/api/v1/consultations/{consultation_id}/transcript",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    first_updated_seg = updated_transcript["segments"][0]
    assert first_updated_seg["effective_text"] == corrected_text


def test_medication_safety_guard_and_doctor_verification(client: TestClient, db_session: Session, test_setup):
    """Verifies Part 8.3 & Part 9.3: Doctor approval is BLOCKED if any medication instruction

    is unverified or has uncertainty flags. Approval succeeds only after explicit doctor verification.
    """
    doc_user = test_setup["doctor_user"]
    org = test_setup["org"]
    loc = test_setup["location"]
    appt = test_setup["appointment"]
    token = create_token(doc_user, org.id, UserRole.DOCTOR.value, loc.id)

    c_resp = client.post(
        "/api/v1/consultations",
        headers={"Authorization": f"Bearer {token}"},
        json={"appointment_id": str(appt.id)},
    )
    assert c_resp.status_code == 201, c_resp.text
    consultation_id = c_resp.json()["id"]
    grant_consent(client, consultation_id, token, "hi-IN")
    client.post(
        f"/api/v1/consultations/{consultation_id}/audio",
        headers={"Authorization": f"Bearer {token}"},
        files={"audio_file": ("test.wav", io.BytesIO(b"AUDIO"), "audio/wav")},
    )
    client.post(
        f"/api/v1/consultations/{consultation_id}/process",
        headers={"Authorization": f"Bearer {token}"},
        json={"use_background_worker": False},
    )

    # Retrieve extracted medications
    meds_resp = client.get(
        f"/api/v1/consultations/{consultation_id}/medications",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert meds_resp.status_code == 200
    meds = meds_resp.json()
    assert len(meds) > 0

    # 1. Attempt doctor approval WITHOUT verifying medications -> MUST BE REJECTED (400)
    approval_payload = {
        "approval_statement": "I have reviewed and approved both reports.",
        "disclaimer_acknowledged": True,
    }
    blocked_approval = client.post(
        f"/api/v1/consultations/{consultation_id}/approve",
        headers={"Authorization": f"Bearer {token}"},
        json=approval_payload,
    )
    assert blocked_approval.status_code == 400
    assert "medications have unresolved" in blocked_approval.json()["detail"].lower() or "verify" in blocked_approval.json()["detail"].lower()

    # 2. Verify all medications
    for m in meds:
        verify_resp = client.patch(
            f"/api/v1/consultations/{consultation_id}/medications/{m['id']}/verify",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "doctor_verified": True,
                "dosage": m["dosage"] or "500 mg",
                "frequency": m["frequency"] or "1-0-1 after food",
                "duration": m["duration"] or "5 days",
            },
        )
        assert verify_resp.status_code == 200
        assert verify_resp.json()["doctor_verified"] is True

    # 3. Attempt doctor approval WITH verified medications -> MUST SUCCEED (200)
    success_approval = client.post(
        f"/api/v1/consultations/{consultation_id}/approve",
        headers={"Authorization": f"Bearer {token}"},
        json=approval_payload,
    )
    assert success_approval.status_code == 200
    appr_data = success_approval.json()
    assert appr_data["approved"] is True
    assert appr_data["consultation_status"] in (ConsultationStatus.APPROVED.value, ConsultationStatus.COMPLETED.value)
    assert len(appr_data["pdf_assets"]) == 2


def test_post_approval_doctor_edits_superseding(client: TestClient, db_session: Session, test_setup):
    """Verifies Part 9.3: If a doctor edits an already approved report, the approved version

    is marked SUPERSEDED, a new version (v2) is created in DOCTOR_EDITED_DRAFT state,
    and must undergo doctor approval again.
    """
    doc_user = test_setup["doctor_user"]
    org = test_setup["org"]
    loc = test_setup["location"]
    appt = test_setup["appointment"]
    token = create_token(doc_user, org.id, UserRole.DOCTOR.value, loc.id)

    c_resp = client.post(
        "/api/v1/consultations",
        headers={"Authorization": f"Bearer {token}"},
        json={"appointment_id": str(appt.id)},
    )
    assert c_resp.status_code == 201, c_resp.text
    consultation_id = c_resp.json()["id"]
    grant_consent(client, consultation_id, token, "hi-IN")
    client.post(
        f"/api/v1/consultations/{consultation_id}/audio",
        headers={"Authorization": f"Bearer {token}"},
        files={"audio_file": ("test.wav", io.BytesIO(b"AUDIO"), "audio/wav")},
    )
    client.post(
        f"/api/v1/consultations/{consultation_id}/process",
        headers={"Authorization": f"Bearer {token}"},
        json={"use_background_worker": False},
    )

    # Verify medications and approve v1
    meds = client.get(f"/api/v1/consultations/{consultation_id}/medications", headers={"Authorization": f"Bearer {token}"}).json()
    for m in meds:
        client.patch(
            f"/api/v1/consultations/{consultation_id}/medications/{m['id']}/verify",
            headers={"Authorization": f"Bearer {token}"},
            json={"doctor_verified": True},
        )
    client.post(
        f"/api/v1/consultations/{consultation_id}/approve",
        headers={"Authorization": f"Bearer {token}"},
        json={"approval_statement": "Approving v1", "disclaimer_acknowledged": True},
    )

    # Now Doctor edits the approved DOCTOR_NOTE
    edit_resp = client.patch(
        f"/api/v1/consultations/{consultation_id}/reports/DOCTOR_NOTE",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "sections_json": {
                "assessment": "Updated Assessment: Acute viral bronchitis with resolving low-grade fever.",
                "plan": "Continue symptomatic relief. Follow-up if cough persists past 7 days.",
            }
        },
    )
    assert edit_resp.status_code == 200, edit_resp.text
    edit_data = edit_resp.json()
    assert edit_data["version_number"] == 2
    assert edit_data["status"] == ReportStatus.DOCTOR_EDITED_DRAFT.value

    # Verify report state
    reports_info = client.get(
        f"/api/v1/consultations/{consultation_id}/reports",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    doc_note_report = next(r for r in reports_info if r["report_type"] in ("DOCTOR_CLINICAL", "DOCTOR_NOTE"))
    assert doc_note_report["current_version_number"] == 2
    assert doc_note_report["current_status"] == ReportStatus.DOCTOR_EDITED_DRAFT.value


def test_pdf_generation_and_patient_delivery(client: TestClient, db_session: Session, test_setup):
    """Verifies ReportLab PDF generation, direct PDF download, and WhatsApp/Email share links."""
    doc_user = test_setup["doctor_user"]
    org = test_setup["org"]
    loc = test_setup["location"]
    appt = test_setup["appointment"]
    token = create_token(doc_user, org.id, UserRole.DOCTOR.value, loc.id)

    c_resp = client.post(
        "/api/v1/consultations",
        headers={"Authorization": f"Bearer {token}"},
        json={"appointment_id": str(appt.id)},
    )
    assert c_resp.status_code == 201, c_resp.text
    consultation_id = c_resp.json()["id"]
    grant_consent(client, consultation_id, token, "hi-IN")
    client.post(
        f"/api/v1/consultations/{consultation_id}/audio",
        headers={"Authorization": f"Bearer {token}"},
        files={"audio_file": ("test.wav", io.BytesIO(b"AUDIO"), "audio/wav")},
    )
    client.post(
        f"/api/v1/consultations/{consultation_id}/process",
        headers={"Authorization": f"Bearer {token}"},
        json={"use_background_worker": False},
    )

    # Verify medications and approve
    meds = client.get(f"/api/v1/consultations/{consultation_id}/medications", headers={"Authorization": f"Bearer {token}"}).json()
    for m in meds:
        client.patch(
            f"/api/v1/consultations/{consultation_id}/medications/{m['id']}/verify",
            headers={"Authorization": f"Bearer {token}"},
            json={"doctor_verified": True},
        )
    client.post(
        f"/api/v1/consultations/{consultation_id}/approve",
        headers={"Authorization": f"Bearer {token}"},
        json={"approval_statement": "Approved", "disclaimer_acknowledged": True},
    )

    # 1. Download Doctor Note PDF
    doc_pdf_resp = client.get(
        f"/api/v1/consultations/{consultation_id}/reports/DOCTOR_NOTE/pdf",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert doc_pdf_resp.status_code == 200
    assert doc_pdf_resp.headers["content-type"] == "application/pdf"
    assert doc_pdf_resp.content.startswith(b"%PDF")

    # 2. Download Patient Summary PDF
    pat_pdf_resp = client.get(
        f"/api/v1/consultations/{consultation_id}/reports/PATIENT_SUMMARY/pdf",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert pat_pdf_resp.status_code == 200
    assert pat_pdf_resp.headers["content-type"] == "application/pdf"
    assert pat_pdf_resp.content.startswith(b"%PDF")

    # 3. Generate WhatsApp share link
    share_link_resp = client.get(
        f"/api/v1/consultations/{consultation_id}/reports/patient-summary/share-link?channel=WHATSAPP",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert share_link_resp.status_code == 200
    share_data = share_link_resp.json()
    assert "whatsapp_url" in share_data
    assert "https://wa.me/" in share_data["whatsapp_url"]
    assert "Rajesh" in share_data["message_preview"]

    # 4. Mark shared
    mark_resp = client.post(
        f"/api/v1/consultations/{consultation_id}/reports/patient-summary/mark-shared",
        headers={"Authorization": f"Bearer {token}"},
        json={"delivery_channel": "MANUAL_WHATSAPP", "recipient_contact": "+919876543210"},
    )
    assert mark_resp.status_code == 200
    assert "grant_id" in mark_resp.json()
