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
    ClinicalFact,
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
    DeliveryChannel,
    DoctorReviewStatus,
    OrgStatus,
    PaymentMode,
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


def test_24_step_complete_clinical_and_saas_lifecycle_e2e(client: TestClient, db_session: Session):
    """
    Executes the full 24-step master scenario from Part 19 of the ArogyaScribe specification.
    Covers the entire lifecycle from SaaS platform onboarding to clinical voice scribing and WhatsApp dispatch.
    """

    # -------------------------------------------------------------------------
    # STEP 0: Seed Super Admin & Core Subscription Plan in DB
    # -------------------------------------------------------------------------
    super_admin = User(
        email="superadmin@master.e2e",
        password_hash=get_password_hash("AdminMaster@123"),
        full_name="Platform Super Administrator",
        is_super_admin=True,
        is_active=True,
    )
    db_session.add(super_admin)

    starter_plan = SubscriptionPlan(
        name="Master Professional Tier",
        code="MASTER_PRO_24",
        monthly_price=Decimal("7999.00"),
        annual_price=Decimal("79990.00"),
        max_doctors=5,
        max_receptionists=3,
        max_branches=2,
        monthly_consultation_limit=500,
        audio_storage_mb_limit=2000,
        report_generation_limit=500,
        is_active=True,
    )
    db_session.add(starter_plan)
    db_session.commit()

    # Step 0 Login: Platform Owner gets token
    login_super = client.post(
        "/api/v1/auth/login",
        json={"email": "superadmin@master.e2e", "password": "AdminMaster@123"},
    )
    assert login_super.status_code == 200
    super_token = login_super.json()["access_token"]
    super_headers = {"Authorization": f"Bearer {super_token}"}

    # -------------------------------------------------------------------------
    # STEP 1: Platform Owner creates an Organization
    # -------------------------------------------------------------------------
    create_org_resp = client.post(
        "/api/v1/platform/organizations",
        headers=super_headers,
        json={
            "name": "Narayana Hrudayalaya E2E Clinic",
            "org_type": "POLYCLINIC",
            "contact_email": "orgadmin@narayana.e2e",
            "contact_phone": "+919876540001",
            "address": "Electronic City Phase 1, Bangalore",
            "admin_full_name": "Dr. Devi Prasad Shetty",
            "admin_email": "orgadmin@narayana.e2e",
            "admin_password": "OrgPassword@123",
        },
    )
    assert create_org_resp.status_code == 201, create_org_resp.text
    org_id = create_org_resp.json()["id"]

    # -------------------------------------------------------------------------
    # STEP 2: Platform Owner activates subscription for the organization
    # -------------------------------------------------------------------------
    activate_sub_resp = client.post(
        "/api/v1/platform/subscriptions/activate",
        headers=super_headers,
        json={
            "organization_id": org_id,
            "plan_id": str(starter_plan.id),
            "billing_cycle": "MONTHLY",
            "payment_mode": "DEVELOPMENT_MANUAL",
            "duration_days": 30,
        },
    )
    assert activate_sub_resp.status_code == 200, activate_sub_resp.text
    assert activate_sub_resp.json()["status"] == "ACTIVE"

    # -------------------------------------------------------------------------
    # STEP 3: Org Admin logs in & accesses organization dashboard
    # -------------------------------------------------------------------------
    login_org_admin = client.post(
        "/api/v1/auth/login",
        json={"email": "orgadmin@narayana.e2e", "password": "OrgPassword@123"},
    )
    assert login_org_admin.status_code == 200
    admin_token = login_org_admin.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    dash_resp = client.get("/api/v1/org/dashboard", headers=admin_headers)
    assert dash_resp.status_code == 200
    assert dash_resp.json()["subscription_status"] == "ACTIVE"

    # Fetch main branch location id
    branches_resp = client.get("/api/v1/org/branches", headers=admin_headers)
    assert branches_resp.status_code == 200
    location_id = branches_resp.json()[0]["id"]

    # -------------------------------------------------------------------------
    # STEP 4: Org Admin creates/invites Doctor and Receptionist
    # -------------------------------------------------------------------------
    create_doc_resp = client.post(
        "/api/v1/org/staff/doctors",
        headers=admin_headers,
        json={
            "email": "dr.kavita@narayana.e2e",
            "password": "DoctorPass@123",
            "full_name": "Dr. Kavita Rao",
            "phone": "+919876540002",
            "location_id": location_id,
            "specialization": "Cardiology & General Medicine",
            "qualification": "MBBS, MD (General Medicine), DM",
            "registration_number": "KMC-78901",
            "consultation_room": "Room 104",
        },
    )
    assert create_doc_resp.status_code == 201, create_doc_resp.text
    doctor_id = create_doc_resp.json()["id"]

    create_rec_resp = client.post(
        "/api/v1/org/staff/receptionists",
        headers=admin_headers,
        json={
            "email": "reception@narayana.e2e",
            "password": "ReceptionPass@123",
            "full_name": "Deepa Sundaram",
            "phone": "+919876540003",
            "location_id": location_id,
            "desk_identifier": "Desk 01",
        },
    )
    assert create_rec_resp.status_code == 201, create_rec_resp.text

    # -------------------------------------------------------------------------
    # STEP 5: Receptionist logs in & acquires scoped session
    # -------------------------------------------------------------------------
    login_rec = client.post(
        "/api/v1/auth/login",
        json={"email": "reception@narayana.e2e", "password": "ReceptionPass@123"},
    )
    assert login_rec.status_code == 200
    rec_token = login_rec.json()["access_token"]
    rec_headers = {"Authorization": f"Bearer {rec_token}"}

    # -------------------------------------------------------------------------
    # STEP 6: Receptionist checks duplicates & registers synthetic patient
    # -------------------------------------------------------------------------
    dup_check = client.get(
        "/api/v1/patients/check-duplicates",
        headers=rec_headers,
        params={"mobile_number": "+919811122233", "full_name": "Ananya Sen"},
    )
    assert dup_check.status_code == 200
    assert dup_check.json()["has_matches"] is False

    create_patient_resp = client.post(
        "/api/v1/patients",
        headers=rec_headers,
        json={
            "full_name": "Ananya Sen",
            "date_of_birth": "1991-08-20",
            "gender": "FEMALE",
            "mobile_number": "+919811122233",
            "email": "ananya.sen@example.com",
            "preferred_language": "hi",
            "allergies_summary": "Penicillin (Moderate rash)",
            "administrative_notes": "Referred by Dr. Mukherjee",
        },
    )
    assert create_patient_resp.status_code == 201, create_patient_resp.text
    patient_id = create_patient_resp.json()["id"]
    uhid = create_patient_resp.json()["patient_identifier"]
    assert len(uhid) > 5

    # -------------------------------------------------------------------------
    # STEP 7: Receptionist creates outpatient appointment
    # -------------------------------------------------------------------------
    book_appt_resp = client.post(
        "/api/v1/appointments",
        headers=rec_headers,
        json={
            "patient_id": patient_id,
            "doctor_user_id": doctor_id,
            "location_id": location_id,
            "appointment_date": str(date.today()),
            "scheduled_time": datetime.now(timezone.utc).isoformat(),
            "appointment_type": "SCHEDULED",
            "reason_for_visit": "Chest tightness and palpitations after exertion",
        },
    )
    assert book_appt_resp.status_code == 201, book_appt_resp.text
    appt_id = book_appt_resp.json()["id"]

    # -------------------------------------------------------------------------
    # STEP 8: Assign / reassign doctor verification
    # -------------------------------------------------------------------------
    reassign_resp = client.patch(
        f"/api/v1/appointments/{appt_id}/assign-doctor",
        headers=rec_headers,
        json={"doctor_user_id": doctor_id},
    )
    assert reassign_resp.status_code == 200

    # -------------------------------------------------------------------------
    # STEP 9: Patient arrives at reception desk
    # -------------------------------------------------------------------------
    arrive_resp = client.patch(
        f"/api/v1/appointments/{appt_id}/status",
        headers=rec_headers,
        json={"status": "ARRIVED", "notes": "Patient checked in at OPD Desk 01"},
    )
    assert arrive_resp.status_code == 200
    assert arrive_resp.json()["status"] == "ARRIVED"

    # -------------------------------------------------------------------------
    # STEP 10: Receptionist updates status to WAITING in room
    # -------------------------------------------------------------------------
    waiting_resp = client.patch(
        f"/api/v1/appointments/{appt_id}/status",
        headers=rec_headers,
        json={"status": "WAITING", "notes": "Patient sent to Waiting Area B"},
    )
    assert waiting_resp.status_code == 200
    assert waiting_resp.json()["status"] == "WAITING"

    # -------------------------------------------------------------------------
    # STEP 11: Doctor logs in & acquires scoped session
    # -------------------------------------------------------------------------
    login_doc = client.post(
        "/api/v1/auth/login",
        json={"email": "dr.kavita@narayana.e2e", "password": "DoctorPass@123"},
    )
    assert login_doc.status_code == 200
    doc_token = login_doc.json()["access_token"]
    doc_headers = {"Authorization": f"Bearer {doc_token}"}

    # -------------------------------------------------------------------------
    # STEP 12: Doctor sees assigned queue on Doctor Dashboard
    # -------------------------------------------------------------------------
    doc_dash_resp = client.get("/api/v1/doctor/dashboard", headers=doc_headers)
    assert doc_dash_resp.status_code == 200
    waiting_queue = doc_dash_resp.json()["waiting_patients"]
    assert any(item["appointment"]["id"] == appt_id for item in waiting_queue)

    # -------------------------------------------------------------------------
    # STEP 13: Doctor opens patient & checks longitudinal history
    # -------------------------------------------------------------------------
    history_resp = client.get(
        f"/api/v1/patients/{patient_id}/longitudinal-history",
        headers=doc_headers,
    )
    assert history_resp.status_code == 200
    hist_data = history_resp.json()
    assert hist_data["patient"]["allergies_summary"] == "Penicillin (Moderate rash)"

    # -------------------------------------------------------------------------
    # STEP 14: Doctor starts consultation & records informed consent
    # -------------------------------------------------------------------------
    start_cons_resp = client.post(
        "/api/v1/consultations",
        headers=doc_headers,
        json={"appointment_id": appt_id},
    )
    assert start_cons_resp.status_code == 201
    consultation_id = start_cons_resp.json()["id"]

    consent_resp = client.post(
        f"/api/v1/consultations/{consultation_id}/consent",
        headers=doc_headers,
        json={
            "language": "hi",
            "consent_wording_version": "1.0",
            "consent_text_snapshot": "Patient Ananya Sen explicitly granted verbal informed consent for clinical recording.",
            "is_granted": True,
        },
    )
    assert consent_resp.status_code == 200
    assert consent_resp.json()["is_granted"] is True

    # -------------------------------------------------------------------------
    # STEP 15: Doctor records/uploads consultation audio
    # -------------------------------------------------------------------------
    mock_audio = b"OPUS_HEADER_MOCK_SIMULATED_CONSULTATION_AUDIO_PAYLOAD"
    upload_audio_resp = client.post(
        f"/api/v1/consultations/{consultation_id}/audio",
        headers=doc_headers,
        files={"audio_file": ("visit_recording.webm", io.BytesIO(mock_audio), "audio/webm")},
    )
    assert upload_audio_resp.status_code in (200, 201), upload_audio_resp.text

    # -------------------------------------------------------------------------
    # STEP 16: Audio validated & stored in private storage with SHA-256
    # -------------------------------------------------------------------------
    upload_json = upload_audio_resp.json()
    assert "audio_asset_id" in upload_json
    assert upload_json["checksum_sha256"] is not None

    # -------------------------------------------------------------------------
    # STEP 17: Runs AI pipeline & inspects multi-speaker transcript
    # -------------------------------------------------------------------------
    process_resp = client.post(
        f"/api/v1/consultations/{consultation_id}/process",
        headers=doc_headers,
        json={"use_background_worker": False},
    )
    assert process_resp.status_code == 200

    transcript_resp = client.get(
        f"/api/v1/consultations/{consultation_id}/transcript",
        headers=doc_headers,
    )
    assert transcript_resp.status_code == 200
    segments = transcript_resp.json()["segments"]
    assert len(segments) > 0

    # -------------------------------------------------------------------------
    # STEP 18: Reviews & accepts clinical facts with grounded transcript citations
    # -------------------------------------------------------------------------
    facts_resp = client.get(
        f"/api/v1/consultations/{consultation_id}/clinical-facts",
        headers=doc_headers,
    )
    assert facts_resp.status_code == 200
    facts_list = facts_resp.json()
    assert len(facts_list) > 0

    fact_to_review = facts_list[0]
    review_resp = client.patch(
        f"/api/v1/consultations/{consultation_id}/clinical-facts/{fact_to_review['id']}",
        headers=doc_headers,
        json={"doctor_review_status": "ACCEPTED"},
    )
    assert review_resp.status_code == 200

    # -------------------------------------------------------------------------
    # STEP 19: Dual report drafts created & doctor verifies medications
    # -------------------------------------------------------------------------
    meds_resp = client.get(
        f"/api/v1/consultations/{consultation_id}/medications",
        headers=doc_headers,
    )
    assert meds_resp.status_code == 200
    meds_list = meds_resp.json()
    assert len(meds_list) > 0

    # Complete & verify all extracted medications to clear safety gate
    for med in meds_list:
        verify_med_resp = client.patch(
            f"/api/v1/consultations/{consultation_id}/medications/{med['id']}/verify",
            headers=doc_headers,
            json={
                "medication_name": med["medication_name"],
                "dosage": "50mg",
                "frequency": "Once daily after meals",
                "duration": "14 days",
                "doctor_verified": True,
            },
        )
        assert verify_med_resp.status_code == 200

    # -------------------------------------------------------------------------
    # STEP 20: Doctor edits clinical report draft & approves encounter
    # -------------------------------------------------------------------------
    edit_report_resp = client.put(
        f"/api/v1/consultations/{consultation_id}/reports/DOCTOR_CLINICAL",
        headers=doc_headers,
        json={
            "rendered_markdown": "# Clinical SOAP Note\n\n**Assessment:** Sinus tachycardia, stress-induced.\n**Plan:** Metoprolol 50mg, ECG follow-up in 2 weeks."
        },
    )
    assert edit_report_resp.status_code == 200

    # Cryptographic approval
    approve_resp = client.post(
        f"/api/v1/consultations/{consultation_id}/approve",
        headers=doc_headers,
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["approved"] is True
    assert approve_resp.json()["consultation_status"] == "APPROVED"

    # -------------------------------------------------------------------------
    # STEP 21: Dual PDFs generated and stored
    # -------------------------------------------------------------------------
    reports_after_approve = client.get(
        f"/api/v1/consultations/{consultation_id}/reports",
        headers=doc_headers,
    )
    assert reports_after_approve.status_code == 200
    for r in reports_after_approve.json():
        assert r.get("current_status") == "APPROVED" or r.get("status") == "APPROVED"

    # -------------------------------------------------------------------------
    # STEP 22: Authorized staff downloads Patient Summary PDF
    # -------------------------------------------------------------------------
    pdf_resp = client.get(
        f"/api/v1/consultations/{consultation_id}/pdfs/PATIENT_SUMMARY_PDF/download",
        headers=rec_headers,  # Receptionist can download approved patient summary
    )
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert len(pdf_resp.content) > 100

    # -------------------------------------------------------------------------
    # STEP 23: PDF manually shared via WhatsApp/email & marked sent
    # -------------------------------------------------------------------------
    delivery_opts_resp = client.get(
        f"/api/v1/consultations/{consultation_id}/delivery-options",
        headers=rec_headers,
    )
    assert delivery_opts_resp.status_code == 200
    assert "whatsapp_url" in delivery_opts_resp.json()

    mark_shared_resp = client.post(
        f"/api/v1/consultations/{consultation_id}/mark-shared",
        headers=rec_headers,
        json={
            "delivery_channel": "MANUAL_WHATSAPP",
            "recipient_contact": "+919811122233",
        },
    )
    assert mark_shared_resp.status_code == 200
    assert mark_shared_resp.json()["status"] == "MARKED_SHARED"

    # -------------------------------------------------------------------------
    # STEP 24: Longitudinal history displays completed approved visit
    # -------------------------------------------------------------------------
    final_hist_resp = client.get(
        f"/api/v1/patients/{patient_id}/longitudinal-history",
        headers=doc_headers,
    )
    assert final_hist_resp.status_code == 200
    final_hist = final_hist_resp.json()
    assert len(final_hist["past_consultations"]) >= 1
    latest_visit = final_hist["past_consultations"][0]
    assert latest_visit["id"] == consultation_id
    assert latest_visit["status"] == "APPROVED"
