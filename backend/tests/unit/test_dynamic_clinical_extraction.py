import pytest
from app.integrations.ai.contracts import TranscriptSegmentResult
from app.integrations.ai.mock_providers import (
    MockClinicalExtractionProvider,
    MockReportGenerationProvider,
    MockTranslationProvider,
)


@pytest.mark.asyncio
async def test_dynamic_clinical_extraction_custom_spoken_text():
    extractor = MockClinicalExtractionProvider()

    custom_transcript = (
        "Patient: Doctor, I have had terrible lower back pain since yesterday after lifting a heavy box. "
        "Doctor: Does the pain radiate to your legs? "
        "Patient: No, it is strictly in my lumbar region. "
        "Doctor: Understood. I advise gentle stretching exercises, hot fomentation, and adequate bed rest for 3 days."
    )

    segments = [
        TranscriptSegmentResult(
            sequence_number=1,
            speaker_label="PATIENT",
            start_time_ms=0,
            end_time_ms=3000,
            text="Doctor, I have had terrible lower back pain since yesterday after lifting a heavy box.",
            confidence_score=0.98,
        ),
        TranscriptSegmentResult(
            sequence_number=2,
            speaker_label="DOCTOR",
            start_time_ms=3500,
            end_time_ms=5500,
            text="Does the pain radiate to your legs?",
            confidence_score=0.99,
        ),
        TranscriptSegmentResult(
            sequence_number=3,
            speaker_label="PATIENT",
            start_time_ms=6000,
            end_time_ms=8500,
            text="No, it is strictly in my lumbar region.",
            confidence_score=0.97,
        ),
        TranscriptSegmentResult(
            sequence_number=4,
            speaker_label="DOCTOR",
            start_time_ms=9000,
            end_time_ms=13000,
            text="Understood. I advise gentle stretching exercises, hot fomentation, and adequate bed rest for 3 days.",
            confidence_score=0.99,
        ),
    ]

    result = await extractor.extract_clinical_data(custom_transcript, segments)

    # 1. Chief complaint must reflect back pain
    assert "Back Pain" in result.chief_complaint_summary
    assert "fever" not in result.chief_complaint_summary.lower()

    # 2. Extracted facts must ground to user's actual spoken words
    fact_keys = [f.fact_key for f in result.facts]
    assert "back_pain" in fact_keys

    back_fact = next(f for f in result.facts if f.fact_key == "back_pain")
    assert "Doctor, I have had terrible lower back pain" in back_fact.evidence_quotation
    assert back_fact.fact_value.get("name") == "Back Pain"
    assert back_fact.fact_value.get("present") is True

    # 3. Medications/Therapies must NOT invent Paracetamol or Azithromycin
    med_names = [m.medication_name for m in result.medications]
    assert "Paracetamol" not in med_names
    assert "Azithromycin" not in med_names
    assert any("Stretching" in m or "Fomentation" in m or "Rest" in m for m in med_names)

    # 4. Dual report generation must be dynamic and not hardcode pharyngitis
    report_gen = MockReportGenerationProvider()
    reports = await report_gen.generate_dual_reports(
        chief_complaint=result.chief_complaint_summary,
        facts=[f.model_dump() for f in result.facts],
        medications=[m.model_dump() for m in result.medications],
        patient_info={"full_name": "Rohan Gupta", "patient_identifier": "ARC-2026-0099", "age_years": 32, "gender": "MALE"},
        doctor_info={"full_name": "Aman Nautiyal", "specialization": "General Physician"},
        clinic_info={"name": "ArogyaScribe Center", "contact_phone": "+919876543210"},
    )

    doc_report = reports.doctor_clinical_markdown
    assert "Back Pain" in doc_report
    assert "Rohan Gupta" in doc_report
    assert "Streptococcal Pharyngitis" not in doc_report
    assert "Acute Upper Respiratory Tract Infection" not in doc_report


@pytest.mark.asyncio
async def test_sample_demo_audio_fallback_preserved():
    extractor = MockClinicalExtractionProvider()

    sample_transcript = (
        "Doctor sahab, 3 din se bukhar aur gale me dard hai. "
        "I am prescribing Paracetamol 650mg three times a day after meals."
    )

    result = await extractor.extract_clinical_data(sample_transcript, [], is_sample_demo=True)

    # Sample demo fallback preserves fever scenario for testers without mic
    assert "Fever for 3 days, sore throat" in result.chief_complaint_summary
    med_names = [m.medication_name for m in result.medications]
    assert "Paracetamol" in med_names
    assert "Azithromycin" in med_names


@pytest.mark.asyncio
async def test_dynamic_clinical_extraction_therapy_dialogue_zero_fever():
    extractor = MockClinicalExtractionProvider()

    therapy_transcript = (
        "Hello doctor, we are discussing cognitive therapy and sleep schedule improvement today. "
        "No medicines needed, just daily mindfulness and therapy sessions for two weeks."
    )

    result = await extractor.extract_clinical_data(therapy_transcript, [], is_sample_demo=False)

    # 1. Chief Complaint must reflect therapy/sleep, ZERO fever
    assert "Fever" not in result.chief_complaint_summary
    assert "bukhar" not in result.chief_complaint_summary.lower()

    # 2. Facts must extract from therapy sentences
    fact_quotes = [f.evidence_quotation for f in result.facts]
    assert any("cognitive therapy" in q.lower() or "mindfulness" in q.lower() for q in fact_quotes)
    for f in result.facts:
        assert "fever" not in f.fact_key.lower()
        assert "sore_throat" not in f.fact_key.lower()

    # 3. Medications must NOT have Paracetamol or Azithromycin
    med_names = [m.medication_name for m in result.medications]
    assert "Paracetamol" not in med_names
    assert "Azithromycin" not in med_names
    assert any("Mindfulness" in m or "Therapy" in m or "Sleep" in m or "Clinical Care" in m for m in med_names)

    # 4. Dual reports must contain ONLY the therapy discussion
    report_gen = MockReportGenerationProvider()
    reports = await report_gen.generate_dual_reports(
        chief_complaint=result.chief_complaint_summary,
        facts=[f.model_dump() for f in result.facts],
        medications=[m.model_dump() for m in result.medications],
        patient_info={"full_name": "Priya Sharma", "patient_identifier": "ARC-2026-0045", "age_years": 28, "gender": "FEMALE"},
        doctor_info={"full_name": "Aman Nautiyal", "specialization": "General Physician"},
        clinic_info={"name": "ArogyaScribe Center", "contact_phone": "+919876543210"},
        is_sample_demo=False,
    )

    doc_report = reports.doctor_clinical_markdown
    patient_report = reports.patient_summary_markdown

    assert "Priya Sharma" in doc_report
    assert "Streptococcal Pharyngitis" not in doc_report
    assert "Acute Upper Respiratory Tract Infection" not in doc_report
    assert "101.5" not in doc_report
    assert "Paracetamol" not in doc_report
    assert "Azithromycin" not in doc_report

    assert "Priya Sharma" in patient_report
    assert "Paracetamol" not in patient_report
    assert "Azithromycin" not in patient_report

