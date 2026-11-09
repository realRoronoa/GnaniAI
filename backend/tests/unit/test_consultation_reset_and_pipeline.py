import uuid
from decimal import Decimal
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.tenant import Organization, User, OrganizationMembership, DoctorProfile, OrganizationLocation
from app.models.patients_appointments import Patient, Appointment
from app.models.consultations_audio import Consultation, ConsentRecord, AudioAsset
from app.models.clinical_reports import ClinicalFact, MedicationInstruction, Report, ReportType, ReportStatus
from app.models.enums import ConsultationStatus, AudioUploadStatus, CertaintyStatus, DoctorReviewStatus, OrgType, UserRole
from app.workers.tasks import process_consultation_pipeline


@pytest.fixture
def sqlite_db():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_pipeline_with_custom_spoken_text_zero_fever(sqlite_db):
    org_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    pat_id = uuid.uuid4()
    cons_id = uuid.uuid4()
    loc_id = uuid.uuid4()

    # 1. Setup tenant & doctor & patient
    org = Organization(id=org_id, name="Test Clinic", org_type=OrgType.POLYCLINIC, contact_email="test@clinic.com", contact_phone="9876543210")
    loc = OrganizationLocation(id=loc_id, organization_id=org_id, name="Main Branch", branch_code="MAIN-01")
    doc_user = User(id=doc_id, email="doc@test.com", password_hash="hash", full_name="Dr. Test")
    doc_prof = DoctorProfile(id=uuid.uuid4(), user_id=doc_id, organization_id=org_id, specialization="Physician", qualification="MBBS", registration_number="LIC123")
    doc_mem = OrganizationMembership(id=uuid.uuid4(), organization_id=org_id, user_id=doc_id, role=UserRole.DOCTOR)
    patient = Patient(id=pat_id, organization_id=org_id, full_name="Aarav Singh", patient_identifier="ARC-001", gender="MALE", mobile_number="9876543210")
    consultation = Consultation(
        id=cons_id,
        organization_id=org_id,
        location_id=loc_id,
        patient_id=pat_id,
        doctor_user_id=doc_id,
        status=ConsultationStatus.RECORDING,
    )
    consent = ConsentRecord(
        id=uuid.uuid4(),
        organization_id=org_id,
        patient_id=pat_id,
        consultation_id=cons_id,
        recorded_by_doctor_id=doc_id,
        is_granted=True,
        consent_text_snapshot="Verbal consent granted.",
    )
    audio = AudioAsset(
        id=uuid.uuid4(),
        organization_id=org_id,
        consultation_id=cons_id,
        storage_key="test.webm",
        content_type="audio/webm",
        file_size_bytes=100,
        duration_seconds=Decimal("5.0"),
        checksum_sha256="fake",
        upload_status=AudioUploadStatus.UPLOADED,
    )

    sqlite_db.add_all([org, loc, doc_user, doc_prof, doc_mem, patient, consultation, consent, audio])
    sqlite_db.commit()

    # Seed some stale fever data on this consultation
    old_fact = ClinicalFact(
        id=uuid.uuid4(),
        organization_id=org_id,
        consultation_id=cons_id,
        category="symptom",
        fact_key="fever",
        fact_value={"name": "Fever", "severity": "Moderate"},
        source_speaker="PATIENT",
        certainty_status=CertaintyStatus.VERIFIED,
        doctor_review_status=DoctorReviewStatus.PENDING,
    )
    old_med = MedicationInstruction(
        id=uuid.uuid4(),
        organization_id=org_id,
        consultation_id=cons_id,
        medication_name="Paracetamol",
        strength="650mg",
    )
    sqlite_db.add_all([old_fact, old_med])
    sqlite_db.commit()

    # Run pipeline with custom spoken text (therapy & sleep) and is_sample_demo=False
    # Mock storage_service get_object_bytes to match audio.checksum_sha256
    import app.workers.tasks as tasks_mod
    tasks_mod.storage_service.get_object_bytes = lambda key: b"test"
    audio.checksum_sha256 = tasks_mod.hashlib.sha256(b"test").hexdigest()
    sqlite_db.commit()

    custom_text = (
        "Doctor: Hello, we are reviewing your sleep counseling and cognitive wellness routine. "
        "Patient: Yes doctor, my sleep has improved with mindfulness and daily walking. "
        "Doctor: Excellent. Continue the daily mindfulness practice and 30-minute walks for two weeks."
    )

    res = process_consultation_pipeline(
        sqlite_db, cons_id, transcript_text=custom_text, is_sample_demo=False
    )

    # Stale fever data MUST have been purged
    assert "Fever" not in res.chief_complaint_summary
    assert any(term in res.chief_complaint_summary for term in ["Sleep", "Mindfulness", "Encounter", "Therapy", "Counseling"])

    # Facts in DB must belong to the new conversation
    facts = sqlite_db.query(ClinicalFact).filter(ClinicalFact.consultation_id == cons_id).all()
    assert len(facts) > 0
    for f in facts:
        assert f.fact_key != "fever"
        assert "Paracetamol" not in str(f.fact_value)

    # Medications in DB must NOT contain Paracetamol or Azithromycin
    meds = sqlite_db.query(MedicationInstruction).filter(MedicationInstruction.consultation_id == cons_id).all()
    for m in meds:
        assert m.medication_name != "Paracetamol"
        assert m.medication_name != "Azithromycin"

    # Reports in DB must reflect the custom dialogue
    reports = sqlite_db.query(Report).filter(Report.consultation_id == cons_id).all()
    assert len(reports) == 2
