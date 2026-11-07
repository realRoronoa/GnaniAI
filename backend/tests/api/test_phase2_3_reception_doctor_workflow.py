from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
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
from app.models.enums import BillingCycle, OrgStatus, SubscriptionStatus, UserRole
from app.models.patients_appointments import Appointment, Patient
from app.models.subscriptions import Subscription, SubscriptionPlan
from app.models.tenant import DoctorProfile, Organization, OrganizationLocation, OrganizationMembership, ReceptionistProfile, User

# In-memory SQLite engine
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


@pytest.fixture()
def test_setup_data(db_session: Session) -> dict:
    # 1. Organization & Location
    org = Organization(
        name="Arogya Med Clinic",
        org_type="CLINIC",
        contact_email="care@arogyamed.in",
        contact_phone="+919876543000",
        status=OrgStatus.ACTIVE,
    )
    db_session.add(org)
    db_session.flush()

    loc = OrganizationLocation(
        organization_id=org.id,
        name="Main Facility",
        branch_code="MAIN-01",
        is_active=True,
    )
    db_session.add(loc)
    db_session.flush()

    # 2. Plan & Active Subscription
    plan = SubscriptionPlan(
        name="Standard Plan",
        code="STANDARD",
        monthly_price=Decimal("4999.00"),
        annual_price=Decimal("49990.00"),
        max_doctors=5,
        max_receptionists=2,
        max_branches=2,
        monthly_consultation_limit=500,
        audio_storage_mb_limit=2000,
        report_generation_limit=500,
        is_active=True,
    )
    db_session.add(plan)
    db_session.flush()

    now = datetime.now(timezone.utc)
    sub = Subscription(
        organization_id=org.id,
        plan_id=plan.id,
        status=SubscriptionStatus.ACTIVE,
        billing_cycle=BillingCycle.MONTHLY,
        start_date=now,
        end_date=now + timedelta(days=30),
    )
    db_session.add(sub)
    db_session.flush()

    # 3. Receptionist User
    rec_user = User(
        email="receptionist@arogyamed.in",
        password_hash=get_password_hash("RecPass@123"),
        full_name="Reception Staff",
        is_super_admin=False,
        is_active=True,
    )
    db_session.add(rec_user)
    db_session.flush()

    db_session.add(
        OrganizationMembership(
            user_id=rec_user.id,
            organization_id=org.id,
            location_id=loc.id,
            role=UserRole.RECEPTIONIST,
            is_active=True,
        )
    )

    # 4. Doctor A
    doc_a = User(
        email="doctor.a@arogyamed.in",
        password_hash=get_password_hash("DocPass@123"),
        full_name="Dr. Arvind Kumar",
        is_super_admin=False,
        is_active=True,
    )
    db_session.add(doc_a)
    db_session.flush()

    db_session.add(
        OrganizationMembership(
            user_id=doc_a.id,
            organization_id=org.id,
            location_id=loc.id,
            role=UserRole.DOCTOR,
            is_active=True,
        )
    )
    db_session.add(
        DoctorProfile(
            user_id=doc_a.id,
            organization_id=org.id,
            location_id=loc.id,
            specialization="General Medicine",
            qualification="MBBS, MD",
            registration_number="MED-12345",
            consultation_room="Room 101",
        )
    )

    # 5. Doctor B
    doc_b = User(
        email="doctor.b@arogyamed.in",
        password_hash=get_password_hash("DocPass@123"),
        full_name="Dr. Bhavna Rao",
        is_super_admin=False,
        is_active=True,
    )
    db_session.add(doc_b)
    db_session.flush()

    db_session.add(
        OrganizationMembership(
            user_id=doc_b.id,
            organization_id=org.id,
            location_id=loc.id,
            role=UserRole.DOCTOR,
            is_active=True,
        )
    )
    db_session.add(
        DoctorProfile(
            user_id=doc_b.id,
            organization_id=org.id,
            location_id=loc.id,
            specialization="Cardiology",
            qualification="MBBS, DM",
            registration_number="MED-67890",
            consultation_room="Room 201",
        )
    )

    db_session.commit()

    # JWT Tokens
    rec_token = create_access_token(
        subject=str(rec_user.id),
        extra_claims={"role": "RECEPTIONIST", "org_id": str(org.id), "location_id": str(loc.id)},
    )
    doc_a_token = create_access_token(
        subject=str(doc_a.id),
        extra_claims={"role": "DOCTOR", "org_id": str(org.id), "location_id": str(loc.id)},
    )
    doc_b_token = create_access_token(
        subject=str(doc_b.id),
        extra_claims={"role": "DOCTOR", "org_id": str(org.id), "location_id": str(loc.id)},
    )

    return {
        "org_id": org.id,
        "location_id": loc.id,
        "rec_user": rec_user,
        "doc_a": doc_a,
        "doc_b": doc_b,
        "rec_headers": {"Authorization": f"Bearer {rec_token}"},
        "doc_a_headers": {"Authorization": f"Bearer {doc_a_token}"},
        "doc_b_headers": {"Authorization": f"Bearer {doc_b_token}"},
    }


# -----------------------------------------------------------------------------
# 1. Duplicate Patient Verification & Family Registration
# -----------------------------------------------------------------------------
def test_duplicate_check_and_family_registration(client: TestClient, test_setup_data: dict) -> None:
    headers = test_setup_data["rec_headers"]

    # 1. Register first family member (Father: Rajesh Sharma)
    resp1 = client.post(
        "/api/v1/patients",
        headers=headers,
        json={
            "full_name": "Rajesh Sharma",
            "gender": "MALE",
            "age_years": 52,
            "mobile_number": "+919876543210",
            "preferred_language": "hi-IN",
            "allergies_summary": "No known drug allergies",
        },
    )
    assert resp1.status_code == 201, resp1.text
    p1 = resp1.json()
    assert p1["full_name"] == "Rajesh Sharma"
    assert p1["allergy_verification_status"] == "UNVERIFIED"

    # 2. Check duplicates with identical mobile number for family member (Daughter: Priya Sharma)
    check_resp = client.get(
        "/api/v1/patients/check-duplicates",
        params={"mobile_number": "+919876543210", "full_name": "Priya Sharma"},
        headers=headers,
    )
    assert check_resp.status_code == 200
    check_data = check_resp.json()
    assert check_data["has_matches"] is True
    assert len(check_data["potential_matches"]) == 1
    assert "Identical mobile number" in check_data["potential_matches"][0]["match_reasons"][0]

    # 3. Ensure system allows creating Priya Sharma despite sharing the mobile number (Rule Part 4.3)
    resp2 = client.post(
        "/api/v1/patients",
        headers=headers,
        json={
            "full_name": "Priya Sharma",
            "gender": "FEMALE",
            "age_years": 22,
            "mobile_number": "+919876543210",
            "preferred_language": "en-IN",
            "allergies_summary": "Penicillin",
        },
    )
    assert resp2.status_code == 201
    p2 = resp2.json()
    assert p2["full_name"] == "Priya Sharma"
    assert p2["id"] != p1["id"]

    # 4. Search patients matches both under the phone number
    search_resp = client.get("/api/v1/patients?q=+919876543210", headers=headers)
    assert search_resp.status_code == 200
    assert len(search_resp.json()) == 2


# -----------------------------------------------------------------------------
# 2. Appointment Booking & Validated State Transitions
# -----------------------------------------------------------------------------
def test_appointment_lifecycle_and_state_transitions(client: TestClient, test_setup_data: dict) -> None:
    headers = test_setup_data["rec_headers"]
    doc_a_id = str(test_setup_data["doc_a"].id)
    doc_b_id = str(test_setup_data["doc_b"].id)
    loc_id = str(test_setup_data["location_id"])

    # Register patient
    pat_resp = client.post(
        "/api/v1/patients",
        headers=headers,
        json={
            "full_name": "Sunil Varma",
            "gender": "MALE",
            "age_years": 38,
            "mobile_number": "+919811122334",
        },
    )
    patient_id = pat_resp.json()["id"]

    # Book Scheduled Appointment
    today_str = date.today().isoformat()
    now_iso = datetime.now(timezone.utc).isoformat()
    book_resp = client.post(
        "/api/v1/appointments",
        headers=headers,
        json={
            "patient_id": patient_id,
            "doctor_user_id": doc_a_id,
            "location_id": loc_id,
            "appointment_date": today_str,
            "scheduled_time": now_iso,
            "appointment_type": "SCHEDULED",
            "reason_for_visit": "Persistent headache and eye strain",
        },
    )
    assert book_resp.status_code == 201, book_resp.text
    app_data = book_resp.json()
    app_id = app_data["id"]
    assert app_data["status"] == "SCHEDULED"
    assert app_data["queue_position"] == 1

    # Valid State Transition: SCHEDULED -> ARRIVED -> WAITING
    t1 = client.patch(
        f"/api/v1/appointments/{app_id}/status",
        headers=headers,
        json={"status": "ARRIVED"},
    )
    assert t1.status_code == 200
    assert t1.json()["status"] == "ARRIVED"
    assert t1.json()["arrived_at"] is not None

    t2 = client.patch(
        f"/api/v1/appointments/{app_id}/status",
        headers=headers,
        json={"status": "WAITING"},
    )
    assert t2.status_code == 200
    assert t2.json()["status"] == "WAITING"

    # Reassign Doctor from Doctor A to Doctor B
    reassign_resp = client.patch(
        f"/api/v1/appointments/{app_id}/assign-doctor",
        headers=headers,
        json={"doctor_user_id": doc_b_id},
    )
    assert reassign_resp.status_code == 200
    assert reassign_resp.json()["doctor_user_id"] == doc_b_id

    # Valid transition: WAITING -> IN_PROGRESS -> COMPLETED
    t3 = client.patch(
        f"/api/v1/appointments/{app_id}/status",
        headers=headers,
        json={"status": "IN_PROGRESS"},
    )
    assert t3.status_code == 200
    assert t3.json()["status"] == "IN_PROGRESS"

    t4 = client.patch(
        f"/api/v1/appointments/{app_id}/status",
        headers=headers,
        json={"status": "COMPLETED"},
    )
    assert t4.status_code == 200
    assert t4.json()["status"] == "COMPLETED"

    # Invalid Backward Transition: COMPLETED -> WAITING must fail with 400
    t_invalid = client.patch(
        f"/api/v1/appointments/{app_id}/status",
        headers=headers,
        json={"status": "WAITING"},
    )
    assert t_invalid.status_code == 400
    assert "invalid appointment status transition" in t_invalid.json()["detail"].lower()


# -----------------------------------------------------------------------------
# 3. Doctor Workspace & Queue Isolation
# -----------------------------------------------------------------------------
def test_doctor_workspace_and_queue_isolation(client: TestClient, test_setup_data: dict) -> None:
    rec_headers = test_setup_data["rec_headers"]
    doc_a_headers = test_setup_data["doc_a_headers"]
    doc_b_headers = test_setup_data["doc_b_headers"]
    doc_a_id = str(test_setup_data["doc_a"].id)
    doc_b_id = str(test_setup_data["doc_b"].id)
    loc_id = str(test_setup_data["location_id"])

    # Create Patient & Appointment for Doctor A
    p_resp = client.post(
        "/api/v1/patients",
        headers=rec_headers,
        json={"full_name": "Kavita Rao", "gender": "FEMALE", "mobile_number": "+919877788899"},
    )
    pat_id = p_resp.json()["id"]

    today_str = date.today().isoformat()
    now_iso = datetime.now(timezone.utc).isoformat()

    client.post(
        "/api/v1/appointments",
        headers=rec_headers,
        json={
            "patient_id": pat_id,
            "doctor_user_id": doc_a_id,
            "location_id": loc_id,
            "appointment_date": today_str,
            "scheduled_time": now_iso,
            "appointment_type": "WALK_IN",
            "initial_status": "WAITING",
            "reason_for_visit": "Seasonal allergies",
        },
    )

    # Doctor A Workspace: should see Kavita Rao in waiting_patients
    dash_a = client.get("/api/v1/doctor/dashboard", headers=doc_a_headers)
    assert dash_a.status_code == 200
    data_a = dash_a.json()
    assert len(data_a["waiting_patients"]) == 1
    assert data_a["waiting_patients"][0]["appointment"]["patient"]["full_name"] == "Kavita Rao"

    # Doctor B Workspace: isolated queue, should have 0 waiting patients
    dash_b = client.get("/api/v1/doctor/dashboard", headers=doc_b_headers)
    assert dash_b.status_code == 200
    data_b = dash_b.json()
    assert len(data_b["waiting_patients"]) == 0

    # Role Isolation: Receptionist cannot access doctor dashboard
    rec_access = client.get("/api/v1/doctor/dashboard", headers=rec_headers)
    assert rec_access.status_code == 403


# -----------------------------------------------------------------------------
# 4. Consultation Start, Mandatory Consent Capture & Withdrawal
# -----------------------------------------------------------------------------
def test_consultation_consent_gate_and_withdrawal(client: TestClient, test_setup_data: dict) -> None:
    rec_headers = test_setup_data["rec_headers"]
    doc_a_headers = test_setup_data["doc_a_headers"]
    doc_a_id = str(test_setup_data["doc_a"].id)
    loc_id = str(test_setup_data["location_id"])

    # Register patient & create appointment
    p_resp = client.post(
        "/api/v1/patients",
        headers=rec_headers,
        json={"full_name": "Meera Patel", "gender": "FEMALE", "mobile_number": "+919822233344"},
    )
    pat_id = p_resp.json()["id"]

    today_str = date.today().isoformat()
    now_iso = datetime.now(timezone.utc).isoformat()

    app_resp = client.post(
        "/api/v1/appointments",
        headers=rec_headers,
        json={
            "patient_id": pat_id,
            "doctor_user_id": doc_a_id,
            "location_id": loc_id,
            "appointment_date": today_str,
            "scheduled_time": now_iso,
            "appointment_type": "WALK_IN",
            "initial_status": "WAITING",
            "reason_for_visit": "Severe throat infection and cough",
        },
    )
    app_id = app_resp.json()["id"]

    # 1. Doctor starts consultation -> enters SETUP state
    start_resp = client.post(
        "/api/v1/consultations",
        headers=doc_a_headers,
        json={"appointment_id": app_id},
    )
    assert start_resp.status_code == 201, start_resp.text
    cons_data = start_resp.json()
    cons_id = cons_data["id"]
    assert cons_data["status"] == "SETUP"
    assert cons_data["consent"] is None

    # Verify appointment transitioned to IN_PROGRESS
    app_check = client.get(f"/api/v1/consultations/{cons_id}", headers=doc_a_headers)
    assert app_check.status_code == 200

    # 2. Capture Mandatory Specific Consent
    consent_resp = client.post(
        f"/api/v1/consultations/{cons_id}/consent",
        headers=doc_a_headers,
        json={
            "purpose": "CLINICAL_DOCUMENTATION_AND_AI_ASSISTANCE",
            "language": "hi-IN",
            "consent_wording_version": "v1.0-2026",
            "consent_text_snapshot": "I hereby consent to audio recording for AI clinical note generation.",
            "is_granted": True,
        },
    )
    assert consent_resp.status_code == 200, consent_resp.text
    consent_data = consent_resp.json()
    assert consent_data["is_granted"] is True
    assert consent_data["language"] == "hi-IN"

    # Consultation status should now be CONSENT_RECORDED
    cons_after_consent = client.get(f"/api/v1/consultations/{cons_id}", headers=doc_a_headers)
    assert cons_after_consent.json()["status"] == "CONSENT_RECORDED"

    # 3. Withdraw Consent
    withdraw_resp = client.post(
        f"/api/v1/consultations/{cons_id}/consent/withdraw",
        headers=doc_a_headers,
        json={"withdrawal_reason": "Patient requested recording stop immediately."},
    )
    assert withdraw_resp.status_code == 200, withdraw_resp.text
    w_data = withdraw_resp.json()
    assert w_data["is_granted"] is False
    assert w_data["withdrawal_reason"] == "Patient requested recording stop immediately."
    assert w_data["withdrawn_at"] is not None

    # Consultation status must revert to SETUP, blocking any audio recording
    cons_after_withdraw = client.get(f"/api/v1/consultations/{cons_id}", headers=doc_a_headers)
    assert cons_after_withdraw.json()["status"] == "SETUP"


# -----------------------------------------------------------------------------
# 5. Longitudinal Patient History & Historical Medications
# -----------------------------------------------------------------------------
def test_longitudinal_patient_history(client: TestClient, test_setup_data: dict, db_session: Session) -> None:
    rec_headers = test_setup_data["rec_headers"]
    doc_a_headers = test_setup_data["doc_a_headers"]
    doc_a_id = test_setup_data["doc_a"].id
    org_id = test_setup_data["org_id"]
    loc_id = test_setup_data["location_id"]

    # 1. Register Patient with allergy
    p_resp = client.post(
        "/api/v1/patients",
        headers=rec_headers,
        json={
            "full_name": "Deepak Joshi",
            "gender": "MALE",
            "age_years": 45,
            "mobile_number": "+919855566677",
            "allergies_summary": "Sulfa drugs",
        },
    )
    pat_id = uuid.UUID(p_resp.json()["id"])

    # 2. Add historical consultation and medication directly
    from app.models.clinical_reports import MedicationInstruction, Report, ReportStatus, ReportType
    from app.models.consultations_audio import Consultation
    from app.models.enums import ConsultationStatus

    cons = Consultation(
        organization_id=org_id,
        location_id=loc_id,
        patient_id=pat_id,
        doctor_user_id=doc_a_id,
        status=ConsultationStatus.COMPLETED,
        started_at=datetime.now(timezone.utc) - timedelta(days=15),
        ended_at=datetime.now(timezone.utc) - timedelta(days=15, minutes=-20),
        chief_complaint_summary="Chronic allergic rhinitis",
    )
    db_session.add(cons)
    db_session.flush()

    # Add historical medication
    med = MedicationInstruction(
        organization_id=org_id,
        consultation_id=cons.id,
        medication_name="Cetirizine 10mg",
        dosage="1 tablet",
        frequency="Once daily at bedtime",
        duration="10 days",
        route="ORAL",
        is_historical=False,  # Was active during that visit
        doctor_verified=True,
    )
    db_session.add(med)

    # Add approved report
    rep = Report(
        organization_id=org_id,
        consultation_id=cons.id,
        report_type=ReportType.DOCTOR_CLINICAL,
        current_status=ReportStatus.APPROVED,
        current_version_number=1,
    )
    db_session.add(rep)
    db_session.commit()

    # 3. Doctor queries longitudinal history
    hist_resp = client.get(
        f"/api/v1/patients/{pat_id}/longitudinal-history",
        headers=doc_a_headers,
    )
    assert hist_resp.status_code == 200, hist_resp.text
    history = hist_resp.json()

    assert history["patient"]["full_name"] == "Deepak Joshi"
    assert history["total_consultations"] == 1
    assert history["allergy_state"]["allergies_summary"] == "Sulfa drugs"
    assert len(history["past_consultations"]) == 1
    assert history["past_consultations"][0]["has_approved_report"] is True
    assert history["past_consultations"][0]["chief_complaint_summary"] == "Chronic allergic rhinitis"

    # Historical medication must have is_historical=True
    assert len(history["historical_medications"]) == 1
    assert history["historical_medications"][0]["medication_name"] == "Cetirizine 10mg"
    assert history["historical_medications"][0]["is_historical"] is True

