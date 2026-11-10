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
async def test_sample_demo_audio_fallback_purged_dynamic_only():
    extractor = MockClinicalExtractionProvider()

    sample_transcript = (
        "Doctor, patient presented with mild earache and throat pain. "
        "I am prescribing Paracetamol 650mg three times a day after meals."
    )

    result = await extractor.extract_clinical_data(sample_transcript, [], is_sample_demo=True)

    # Dynamic extraction always runs, zero hardcoded fever template data
    assert "Fever for 3 days, sore throat, and headache" != result.chief_complaint_summary
    med_names = [m.medication_name for m in result.medications]
    assert "Paracetamol" in med_names


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


@pytest.mark.asyncio
async def test_hindi_dysentery_transcript_deduplication_and_clean_english_soap():
    from app.integrations.ai.mock_providers import deduplicate_repeated_phrases, strip_conversational_greetings
    from app.services.pdf_service import PDFService
    from app.models.enums import PdfType
    from datetime import datetime, timezone

    repeated_hindi = (
        "अरे डॉक्टर साहब मेरा नाम आदर्श प्रताप सिंह है और मुझे पेचिश लगे हुए हैं मैं जब भी खाना खाता हूं हर बार बाथरूम चला जाता हूं खाना भी नहीं खा पा रहा हूं भूख भी नहीं लग रही है "
    ) * 10

    # 1. Deduplication must collapse repeated chunks
    deduped = deduplicate_repeated_phrases(repeated_hindi)
    assert len(deduped.split()) <= 45

    # 2. Stripper must remove greetings and introductory names
    stripped = strip_conversational_greetings(deduped)
    assert "अरे डॉक्टर साहब" not in stripped
    assert "मेरा नाम" not in stripped
    assert "पेचिश" in stripped

    # 3. Dynamic Extraction must map to English clinical entities
    extractor = MockClinicalExtractionProvider()
    result = await extractor.extract_clinical_data(repeated_hindi, [], is_sample_demo=False)

    # Chief complaint must have English medical terminology and ZERO greetings
    assert "Acute Dysentery" in result.chief_complaint_summary
    assert "अरे डॉक्टर साहब" not in result.chief_complaint_summary
    assert "मेरा नाम" not in result.chief_complaint_summary

    fact_keys = [f.fact_key for f in result.facts]
    assert "dysentery_gastroenteritis" in fact_keys

    # Must provide ORS and Probiotics
    med_names = [m.medication_name for m in result.medications]
    assert any("Oral Rehydration Salts" in m or "ORS" in m for m in med_names)

    # 4. Generate Dual Reports
    report_gen = MockReportGenerationProvider()
    reports = await report_gen.generate_dual_reports(
        chief_complaint=result.chief_complaint_summary,
        facts=[f.model_dump() for f in result.facts],
        medications=[m.model_dump() for m in result.medications],
        patient_info={"full_name": "आदर्श प्रताप सिंह", "patient_identifier": "ARC-2026-0001", "age_years": 24, "gender": "MALE"},
        doctor_info={"full_name": "Dr. Aman Nautiyal", "specialization": "General Physician"},
        clinic_info={"name": "Guthal Polyclinic", "contact_phone": "+919876543210"},
        is_sample_demo=False,
    )

    doc_report = reports.doctor_clinical_markdown
    assert "Acute Dysentery" in doc_report
    assert "Postprandial Bowel Urgency" in doc_report
    assert "Oral Rehydration Salts" in doc_report
    assert "अरे डॉक्टर साहब मेरा नाम" not in doc_report

    # 5. Generate PDF via PDFService: must succeed and produce non-empty PDF bytes without Helvetica encoding exceptions
    pdf_bytes = PDFService.generate_pdf(
        pdf_type=PdfType.DOCTOR_REPORT_PDF,
        clinic_name="Guthal Polyclinic",
        clinic_phone="+919876543210",
        doctor_name="Dr. Aman Nautiyal",
        doctor_specialization="General Physician",
        patient_name="आदर्श प्रताप सिंह",
        patient_identifier="ARC-2026-0001",
        patient_age="24",
        patient_gender="MALE",
        content_markdown=doc_report,
        signature_hash="abc123hashsignature456",
        approved_at=datetime.now(timezone.utc),
    )
    assert len(pdf_bytes) > 5000


@pytest.mark.asyncio
async def test_user_exact_hindi_consultation_extraction_and_reports():
    """Verifies extraction and dual report generation from the user's exact Hindi clinical recording."""
    user_hindi_transcript = (
        "हेलो नमस्ते डॉक्टर एक्चुअल में मुझे थोड़ी बहुत सी प्रॉब्लम है जैसे कि मुझे खाना खाने के बाद भूख नहीं लगती "
        "सोने के बाद नींद नहीं आते और पानी पीने के बाद प्यास नहीं लगती है। "
        "डॉक्टर: मैं आपको दो गोलियां दूंगा एक गोली का नाम है पेरासिटामोल और दूसरे का नाम है... "
        "सुबह-शाम और दिन में, याद रखें इन तीनों दवाई को खाना खाने के बाद लेना खाली पेट नहीं लेना। "
        "साथ ही साथ आपको एक और डॉक्टर के पास जाना है जिस डॉक्टर का मेंटल के प्रॉब्लम में दिखेगा। "
        "15 दिन बाद मुझे रिपीट करेंगे। "
        "गर्म खाना नहीं खाना है ज्यादा ठंडा खाना भी नहीं खाना है, ज्यादा नमक नहीं खाना है और ज्यादा मीठा भी नहीं खाना एकदम नॉर्मल सादा खाना।"
    )

    extractor = MockClinicalExtractionProvider()
    result = await extractor.extract_clinical_data(user_hindi_transcript, [], is_sample_demo=False)

    # 1. Assert Symptoms: Anorexia, Insomnia, Adipsia
    fact_keys = [f.fact_key for f in result.facts]
    assert "anorexia_reduced_intake" in fact_keys
    assert "insomnia_anxiety" in fact_keys
    assert "adipsia_altered_thirst" in fact_keys

    # 2. Assert Referral, Diet, and Follow-Up Facts
    assert "specialist_referral_psychiatry" in fact_keys
    assert "dietary_lifestyle_restrictions" in fact_keys
    assert "scheduled_followup_plan" in fact_keys

    # 3. Assert Medications: Paracetamol and prescribed tablet with 1-1-1, after meals, 15 days
    med_names = [m.medication_name for m in result.medications]
    assert any("Paracetamol" in m for m in med_names)
    assert any("Prescribed Oral Tablet" in m for m in med_names)

    pcm = next(m for m in result.medications if "Paracetamol" in m.medication_name)
    assert "1-1-1" in pcm.frequency or "Three times" in pcm.frequency
    assert "after meals" in pcm.special_instructions.lower()
    assert "empty stomach" in pcm.special_instructions.lower()
    assert "15 Days" in pcm.duration

    # 4. Assert Chief Complaint is professional medical terminology and NOT truncated
    assert "Namaste, please have a seat" not in result.chief_complaint_summary
    assert "regarding my healt" not in result.chief_complaint_summary
    assert len(result.chief_complaint_summary) > 10

    # 5. Dual Reports Generation
    report_gen = MockReportGenerationProvider()
    reports = await report_gen.generate_dual_reports(
        chief_complaint=result.chief_complaint_summary,
        facts=[f.model_dump() for f in result.facts],
        medications=[m.model_dump() for m in result.medications],
        patient_info={"full_name": "विनय कुमार", "patient_identifier": "ARC-2026-0777", "age_years": 29, "gender": "MALE"},
        doctor_info={"full_name": "Dr. Aman Nautiyal", "specialization": "General Physician"},
        clinic_info={"name": "ArogyaScribe Center", "contact_phone": "+919876543210"},
        is_sample_demo=False,
    )

    doc_md = reports.doctor_clinical_markdown
    pat_md = reports.patient_summary_markdown

    # Assert Specialist Referral, 15-day follow-up, and Dietary Restrictions in reports
    assert "Psychiatry / Mental Health Specialist" in doc_md
    assert "15 days" in doc_md.lower()
    assert "सादा भोजन" in doc_md or "plain, balanced home diet" in doc_md.lower()

    assert "Paracetamol" in pat_md
    assert "15 days" in pat_md.lower() or "15" in pat_md
    assert "सादा भोजन" in pat_md or "plain, light, home-cooked food" in pat_md.lower()

    # Zero dummy text
    assert "Namaste, please have a seat" not in doc_md
    assert "regarding my healt" not in doc_md
    assert "Namaste, please have a seat" not in pat_md
    assert "regarding my healt" not in pat_md


