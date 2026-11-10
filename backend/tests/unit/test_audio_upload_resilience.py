import io
import uuid
import pytest
from starlette.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models.tenant
import app.models.consultations_audio
import app.models.patients_appointments
import app.models.clinical_reports
import app.models.subscriptions
import app.models.system_audit
from app.db.base import Base
from app.db.session import get_db
from app.api.deps import get_current_membership, require_doctor, get_current_tenant_org_id
from app.models.tenant import Organization, User, OrganizationMembership, OrganizationLocation
from app.models.patients_appointments import Patient
from app.models.consultations_audio import Consultation, ConsentRecord
from app.models.enums import ConsultationStatus, OrgType, UserRole
from app.main import app


@pytest.fixture
def test_setup():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()

    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    pat_id = uuid.uuid4()
    cons_id = uuid.uuid4()
    loc_id = uuid.uuid4()

    org = Organization(id=org_id, name="Test Clinic", org_type=OrgType.POLYCLINIC, contact_email="test@clinic.com", contact_phone="9876543210")
    loc = OrganizationLocation(id=loc_id, organization_id=org_id, name="Main", branch_code="M-01")
    user = User(id=user_id, email="doctor@test.com", password_hash="hash", full_name="Dr. Tester")
    mem = OrganizationMembership(id=uuid.uuid4(), organization_id=org_id, user_id=user_id, role=UserRole.DOCTOR)
    patient = Patient(id=pat_id, organization_id=org_id, full_name="Aarav Patient", patient_identifier="P-01", gender="MALE", mobile_number="9876543210")
    cons = Consultation(id=cons_id, organization_id=org_id, location_id=loc_id, patient_id=pat_id, doctor_user_id=user_id, status=ConsultationStatus.RECORDING)
    consent = ConsentRecord(id=uuid.uuid4(), organization_id=org_id, patient_id=pat_id, consultation_id=cons_id, recorded_by_doctor_id=user_id, is_granted=True, consent_text_snapshot="Verbal consent granted.")

    session.add_all([org, loc, user, mem, patient, cons, consent])
    session.commit()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    def override_require_doctor():
        return mem

    def override_org_id():
        return org_id

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_membership] = override_require_doctor
    app.dependency_overrides[require_doctor] = override_require_doctor
    app.dependency_overrides[get_current_tenant_org_id] = override_org_id

    client = TestClient(app)
    yield client, cons_id

    app.dependency_overrides.clear()
    session.close()


def test_audio_upload_with_file_key(test_setup):
    client, cons_id = test_setup
    dummy_wav = b"RIFF" + b"\x00" * 40

    # Test sending under 'file' key with duration_seconds and transcript_text
    response = client.post(
        f"/api/v1/consultations/{cons_id}/audio",
        files={"file": ("recording.wav", io.BytesIO(dummy_wav), "audio/wav")},
        data={"duration_seconds": "5", "transcript_text": "Doctor consultation test note."},
    )
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
    assert response.json()["consultation_status"] == "RECORDING"


def test_audio_upload_with_audio_file_key(test_setup):
    client, cons_id = test_setup
    dummy_wav = b"RIFF" + b"\x00" * 40

    # Test sending under 'audio_file' key
    response = client.post(
        f"/api/v1/consultations/{cons_id}/audio",
        files={"audio_file": ("recording.wav", io.BytesIO(dummy_wav), "audio/wav")},
        data={"transcript_text": "Another test transcript."},
    )
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"


def test_audio_upload_with_json_base64(test_setup):
    import base64
    client, cons_id = test_setup
    dummy_wav = b"RIFF" + b"\x00" * 40
    b64_audio = base64.b64encode(dummy_wav).decode("ascii")

    # Test sending as JSON payload with base64 audio
    response = client.post(
        f"/api/v1/consultations/{cons_id}/audio",
        json={"audio_base64": b64_audio, "transcript_text": "Base64 upload test"},
    )
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
