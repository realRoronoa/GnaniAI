from typing import Any

from app.integrations.ai.contracts import (
    ClinicalExtractionResult,
    DualReportResult,
    ExtractedClinicalFact,
    ExtractedMedicationInstruction,
    TranscriptSegmentResult,
    TranscriptionResult,
)


class MockTranscriptionProvider:
    """Deterministic Speech-to-Text mock representing Gnani Prisma v2.5 output."""

    async def transcribe(self, audio_bytes: bytes, language_code: str = "en-IN") -> TranscriptionResult:
        segments = [
            TranscriptSegmentResult(
                sequence_number=1,
                speaker_label="DOCTOR",
                start_time_ms=0,
                end_time_ms=3200,
                text="Namaste, please sit down. What seems to be the trouble today?",
                confidence_score=0.98,
            ),
            TranscriptSegmentResult(
                sequence_number=2,
                speaker_label="PATIENT",
                start_time_ms=3500,
                end_time_ms=9800,
                text="Doctor sahab, 3 din se bukhar aur gale me dard hai. Khasi bhi ho rahi hai.",
                confidence_score=0.96,
            ),
            TranscriptSegmentResult(
                sequence_number=3,
                speaker_label="DOCTOR",
                start_time_ms=10100,
                end_time_ms=14500,
                text="Any breathing difficulty or chest pain? Did you check your temperature?",
                confidence_score=0.99,
            ),
            TranscriptSegmentResult(
                sequence_number=4,
                speaker_label="PATIENT",
                start_time_ms=15000,
                end_time_ms=21000,
                text="No chest pain. Temperature was 101.5 yesterday night. Sar me bhi bohot dard hai.",
                confidence_score=0.97,
            ),
            TranscriptSegmentResult(
                sequence_number=5,
                speaker_label="DOCTOR",
                start_time_ms=21500,
                end_time_ms=29000,
                text="Alright. Your throat is inflamed. I am prescribing Paracetamol 650mg three times a day after meals, and Azithromycin 500mg once daily for 3 days. Drink warm water.",
                confidence_score=0.98,
            ),
            TranscriptSegmentResult(
                sequence_number=6,
                speaker_label="PATIENT",
                start_time_ms=29500,
                end_time_ms=33000,
                text="Thank you doctor. Any allergy tests needed?",
                confidence_score=0.95,
            ),
            TranscriptSegmentResult(
                sequence_number=7,
                speaker_label="DOCTOR",
                start_time_ms=33500,
                end_time_ms=39000,
                text="No immediate test needed. If fever persists after 3 days, come back for a complete blood count.",
                confidence_score=0.98,
            ),
        ]

        full_text = " ".join(s.text for s in segments)
        return TranscriptionResult(
            full_text=full_text,
            language_detected="hi-IN" if "hi" in language_code else "en-IN",
            segments=segments,
        )


class MockClinicalExtractionProvider:
    """Deterministic Clinical Fact Extractor representing Gnani Evon v3.3 output."""

    async def extract_clinical_data(
        self,
        transcript_text: str,
        segments: list[TranscriptSegmentResult],
        previous_consultation_facts: list[dict[str, Any]] | None = None,
    ) -> ClinicalExtractionResult:
        facts = [
            ExtractedClinicalFact(
                category="symptom",
                fact_key="fever",
                fact_value={"name": "Fever", "severity": "Moderate", "temperature_f": 101.5, "duration_days": 3},
                source_speaker="PATIENT",
                provenance_type="PATIENT_REPORTED",
                certainty_status="VERIFIED",
                evidence_quotation="Temperature was 101.5 yesterday night.",
                segment_indices=[1, 3],
            ),
            ExtractedClinicalFact(
                category="symptom",
                fact_key="sore_throat",
                fact_value={"name": "Sore throat and pharyngeal pain", "severity": "Moderate"},
                source_speaker="PATIENT",
                provenance_type="PATIENT_REPORTED",
                certainty_status="VERIFIED",
                evidence_quotation="gale me dard hai. Khasi bhi ho rahi hai.",
                segment_indices=[1],
            ),
            ExtractedClinicalFact(
                category="symptom",
                fact_key="headache",
                fact_value={"name": "Headache", "severity": "Significant"},
                source_speaker="PATIENT",
                provenance_type="PATIENT_REPORTED",
                certainty_status="VERIFIED",
                evidence_quotation="Sar me bhi bohot dard hai.",
                segment_indices=[3],
            ),
            ExtractedClinicalFact(
                category="symptom",
                fact_key="chest_pain",
                fact_value={"name": "Chest pain", "present": False},
                source_speaker="PATIENT",
                provenance_type="PATIENT_REPORTED",
                certainty_status="PATIENT_DENIED",
                evidence_quotation="No chest pain.",
                segment_indices=[3],
            ),
            ExtractedClinicalFact(
                category="examination",
                fact_key="pharyngeal_erythema",
                fact_value={"finding": "Pharyngeal inflammation and erythema"},
                source_speaker="DOCTOR",
                provenance_type="CLINICIAN_OBSERVED",
                certainty_status="VERIFIED",
                evidence_quotation="Your throat is inflamed.",
                segment_indices=[4],
            ),
            ExtractedClinicalFact(
                category="diagnosis",
                fact_key="acute_pharyngitis",
                fact_value={"condition": "Acute Upper Respiratory Tract Infection / Pharyngitis"},
                source_speaker="DOCTOR",
                provenance_type="AI_EXTRACTED",
                certainty_status="VERIFIED",
                evidence_quotation="Your throat is inflamed. I am prescribing...",
                segment_indices=[4],
            ),
        ]

        # Medications extracted from encounter
        medications = [
            ExtractedMedicationInstruction(
                medication_name="Paracetamol",
                strength="650mg",
                dosage="1 tablet",
                route="ORAL",
                frequency="Three times a day",
                duration="3 days",
                special_instructions="Take after food",
                uncertainty_flags=[],  # Fully verified
                is_historical=False,
                evidence_quotation="Paracetamol 650mg three times a day after meals",
            ),
            ExtractedMedicationInstruction(
                medication_name="Azithromycin",
                strength="500mg",
                dosage="1 tablet",
                route="ORAL",
                frequency="Once daily",
                duration="3 days",
                special_instructions="Take in the morning",
                uncertainty_flags=[],  # Fully verified
                is_historical=False,
                evidence_quotation="Azithromycin 500mg once daily for 3 days",
            ),
        ]

        # Longitudinal comparison against prior visit
        longitudinal_comparison: dict[str, Any] = {
            "prior_visits_analyzed": len(previous_consultation_facts) if previous_consultation_facts else 0,
            "status": "No chronic conditions identified from previous encounters.",
            "recurrent_symptoms": [],
        }

        return ClinicalExtractionResult(
            chief_complaint_summary="Fever for 3 days, sore throat, and headache",
            facts=facts,
            medications=medications,
            unresolved_questions=[],
            longitudinal_comparison_json=longitudinal_comparison,
        )


class MockReportGenerationProvider:
    """Generates dual clinical drafts: DOCTOR_CLINICAL (14 sections) and PATIENT_SUMMARY (10 sections)."""

    async def generate_dual_reports(
        self,
        chief_complaint: str,
        facts: list[dict[str, Any]],
        medications: list[dict[str, Any]],
        patient_info: dict[str, Any],
        doctor_info: dict[str, Any],
        clinic_info: dict[str, Any],
    ) -> DualReportResult:
        # 1. Doctor Clinical Report Markdown (All 14 Sections from Part 9.1)
        meds_lines = "\n".join(
            f"- **{m.get('medication_name')}** ({m.get('strength', '')}): {m.get('dosage', '')} {m.get('frequency', '')} for {m.get('duration', '')}. Note: {m.get('special_instructions', 'None')}"
            for m in medications
        )

        doctor_md = f"""# Clinical Encounter Note (SOAP)

### 1. Patient Demographics & Encounter Metadata
- **Patient Name:** {patient_info.get('full_name')} (ID: {patient_info.get('patient_identifier')})
- **Age / Gender:** {patient_info.get('age_years', 'N/A')} / {patient_info.get('gender')}
- **Attending Doctor:** {doctor_info.get('full_name')} ({doctor_info.get('specialization')})
- **Facility:** {clinic_info.get('name')}

### 2. Chief Complaint
{chief_complaint}

### 3. History of Present Illness (HPI)
Patient reports fever and severe sore throat for 3 days accompanied by moderate headache. Denies chest pain or shortness of breath.

### 4. Vitals & Physical Examination
- Temp: 101.5°F (patient reported)
- Throat: Mild-to-moderate erythema over posterior pharyngeal wall. Tonsils non-hypertrophied.

### 5. Systemic Review
Respiratory: Bilateral breath sounds clear. Cardiovascular: S1, S2 heard normally.

### 6. Current Assessment & Clinical Impression
Acute Upper Respiratory Tract Infection (Probable viral with secondary pharyngitis).

### 7. Differential Diagnoses
- Streptococcal Pharyngitis
- Seasonal Viral Influenza

### 8. Allergies
{patient_info.get('allergies_summary') or 'No known drug allergies (NKDA)'}

### 9. Active Medication Instructions
{meds_lines}

### 10. Investigations Ordered
None at present. CBC if fever persists beyond 72 hours.

### 11. Follow-Up Plan
Follow-up in outpatient clinic after 3 days if symptomatic relief is inadequate.

### 12. Emergency Warning Signs
Patient advised to report immediately to emergency if experiencing high persistent fever (>103°F), difficulty breathing, or severe lethargy.

### 13. Doctor Attestation & Approval Notice
*Pending Final Clinician Review and Digital Approval.*

### 14. Audit Verification
*Report Version 1 (AI Draft Generated).*
"""

        # 2. Patient Vernacular Summary Markdown (All 10 Sections from Part 9.2)
        patient_meds_lines = "\n".join(
            f"- **{m.get('medication_name')} {m.get('strength', '')}:** Take {m.get('dosage', '1 tablet')} {m.get('frequency', '')} for {m.get('duration', '')}. ({m.get('special_instructions', '')})"
            for m in medications
        )

        patient_md = f"""# Your Visit Summary & Care Plan

### 1. Greeting & Visit Overview
Namaste **{patient_info.get('full_name')}**, thank you for visiting {clinic_info.get('name')}.

### 2. Reason for Your Visit
You consulted Dr. {doctor_info.get('full_name')} today regarding your fever and throat discomfort.

### 3. What the Doctor Found
The examination showed swelling and redness in your throat causing the throat irritation and fever.

### 4. Prescribed Medicines & How to Take Them
{patient_meds_lines}

### 5. Tests Ordered
No blood tests are needed right now. Keep resting and monitoring your temperature.

### 6. Diet & Home Care Recommendations
- Drink warm water and soothing herbal fluids.
- Eat light, soft meals.
- Rest adequately and avoid chilled beverages.

### 7. Warning Signs to Watch For
Please contact us or visit urgent care immediately if:
- You develop difficulty breathing or swallowing.
- Your fever stays above 102°F despite taking medicine.

### 8. When to Return
Please return for a follow-up visit after 3 days if you do not feel significantly better.

### 9. Doctor's Contact
**Dr. {doctor_info.get('full_name')}**, {clinic_info.get('name')}. Phone: {clinic_info.get('contact_phone', 'N/A')}.

### 10. Disclaimer
*This document is a simplified patient summary generated by ArogyaScribe AI and reviewed by your doctor. It does not replace full formal medical records.*
"""

        return DualReportResult(
            doctor_clinical_markdown=doctor_md.strip(),
            doctor_structured_json={
                "chief_complaint": chief_complaint,
                "facts": facts,
                "medications": medications,
            },
            patient_summary_markdown=patient_md.strip(),
            patient_structured_json={
                "greeting": f"Namaste {patient_info.get('full_name')}",
                "medications": medications,
                "instructions": ["Warm water", "Adequate rest"],
            },
        )


class MockTranslationProvider:
    """Translates patient summary narrative into Indian languages while keeping medical terms and dosages intact."""

    INDIC_TEMPLATES: dict[str, dict[str, str]] = {
        "hi": {
            "title": "आपके डॉक्टर परामर्श का सारांश और देखभाल योजना",
            "lang_name": "हिंदी अनुवाद (Hindi)",
            "greeting": "नमस्ते, हमारे क्लिनिक में आने के लिए धन्यवाद।",
            "reason": "बुखार, गले में खराश और शारीरिक अस्वस्थता के लिए परामर्श।",
            "findings": "जांच में गले में सूजन और वायरल संक्रमण के लक्षण पाए गए हैं।",
            "diet": "- गुनगुना पानी पिएं और पर्याप्त आराम करें।\n- ठंडा पानी और तले-भुने खाने से बचें।",
            "warning": "यदि सांस लेने में कठिनाई हो या तेज बुखार (102°F से अधिक) बना रहे, तो तुरंत संपर्क करें।",
            "followup": "3 दिन बाद पुनः जांच के लिए आएं यदि आराम न मिले।",
            "disclaimer": "यह सारांश आपके डॉक्टर द्वारा स्वीकृत और आरोग्यस्क्राइब एआई द्वारा तैयार किया गया है।",
        },
        "ta": {
            "title": "உங்கள் மருத்துவ ஆலோசனை சுருக்கம் மற்றும் பராமரிப்பு திட்டம்",
            "lang_name": "தமிழ் மொழிபெயர்ப்பு (Tamil)",
            "greeting": "வணக்கம், எங்கள் மருத்துவமனைக்கு வருகை தந்ததற்கு நன்றி.",
            "reason": "காய்ச்சல், தொண்டை வலி மற்றும் உடல் சோர்வுக்கான ஆலோசனை.",
            "findings": "பரிசோதனையில் தொண்டை வீக்கம் மற்றும் வைரஸ் தொற்று இருப்பது கண்டறியப்பட்டது.",
            "diet": "- வெதுவெதுப்பான நீர் அருந்தவும், போதுமான ஓய்வு எடுக்கவும்.\n- குளிர்ந்த உணவுகள் மற்றும் பானங்களைத் தவிர்க்கவும்.",
            "warning": "சுவாசிப்பதில் சிரமம் ஏற்பட்டாலோ அல்லது அதிக காய்ச்சல் (102°F மேல்) நீடித்தாலோ உடனடியாக தொடர்பு கொள்ளவும்.",
            "followup": "3 நாட்களுக்குப் பிறகு அறிகுறிகள் குறையாவிட்டால் மறுபரிசோதனைக்கு வரவும்.",
            "disclaimer": "இந்த சுருக்கம் ஆரோக்கியஸ்கிரைப் AI மூலம் உருவாக்கப்பட்டு மருத்துவரால் அங்கீகரிக்கப்பட்டது.",
        },
        "te": {
            "title": "మీ వైద్య సంప్రదింపు సారాంశం మరియు సంరక్షణ ప్రణాళిక",
            "lang_name": "తెలుగు అనువాదం (Telugu)",
            "greeting": "నమస్కారం, మా క్లినిక్‌ను సందర్శించినందుకు ధన్యవాదాలు.",
            "reason": "జ్వరం, గొంతు నొప్పి మరియు శారీరక అసౌకర్యం కొరకు సంప్రదింపు.",
            "findings": "పరీక్షలో గొంతు వాపు మరియు వైరల్ ఇన్ఫెక్షన్ లక్షణాలు కనిపించాయి.",
            "diet": "- గోరువెచ్చని నీరు త్రాగండి మరియు తగినంత విశ్రాంతి తీసుకోండి.\n- చల్లటి ఆహారాలు మరియు పానీయాలకు దూరంగా ఉండండి.",
            "warning": "శ్వాస తీసుకోవడంలో ఇబ్బంది లేదా అధిక జ్వరం (102°F కంటే ఎక్కువ) కొనసాగితే వెంటనే సంప్రదించండి.",
            "followup": "3 రోజుల తర్వాత ఉపశమనం కలగకపోతే ఫాలో-అప్ కొరకు రండి.",
            "disclaimer": "ఈ సారాంశం ఆరోగ్యస్క్రైబ్ AI ద్వారా రూపొందించబడి వైద్యునిచే ధృవీకరించబడింది.",
        },
        "kn": {
            "title": "ನಿಮ್ಮ ವೈದ್ಯಕೀಯ ಸಮಾಲೋಚನೆಯ ಸಾರಾಂಶ ಮತ್ತು ಆರೈಕೆ ಯೋಜನೆ",
            "lang_name": "ಕನ್ನಡ ಅನುವಾದ (Kannada)",
            "greeting": "ನಮಸ್ಕಾರ, ನಮ್ಮ ಚಿಕಿತ್ಸಾಲಯಕ್ಕೆ ಭೇಟಿ ನೀಡಿದ್ದಕ್ಕಾಗಿ ಧನ್ಯವಾದಗಳು.",
            "reason": "ಜ್ವರ, ಗಂಟಲು ನೋವು ಮತ್ತು ಕೆಮ್ಮಿನ ಸಮಾಲೋಚನೆ.",
            "findings": "ಪರೀಕ್ಷೆಯಲ್ಲಿ ಗಂಟಲಿನ ಊತ ಮತ್ತು ವೈರಲ್ ಸೋಂಕಿನ ಲಕ್ಷಣಗಳು ಕಂಡುಬಂದಿವೆ.",
            "diet": "- ಉಗುರುಬೆಚ್ಚಗಿನ ನೀರನ್ನು ಕುಡಿಯಿರಿ ಮತ್ತು ಸಾಕಷ್ಟು ವಿಶ್ರಾಂತಿ ಪಡೆಯಿರಿ.\n- ತಂಪು ಪಾನೀಯಗಳು ಮತ್ತು ಎಣ್ಣೆಯುಕ್ತ ಆಹಾರವನ್ನು ತಪ್ಪಿಸಿ.",
            "warning": "ಉಸಿರಾಟದಲ್ಲಿ ತೊಂದರೆ ಅಥವಾ ತೀವ್ರ ಜ್ವರ (102°F ಗಿಂತ ಹೆಚ್ಚು) ಮುಂದುವರಿದರೆ ತಕ್ಷಣ ಸಂಪರ್ಕಿಸಿ.",
            "followup": "3 ದಿನಗಳ ನಂತರ ಗುಣಮುಖವಾಗದಿದ್ದರೆ ಮರುಪರಿಶೀಲನೆಗೆ ಬನ್ನಿ.",
            "disclaimer": "ಈ ಸಾರಾಂಶವನ್ನು ಆರೋಗ್ಯಸ್ಕ್ರೈಬ್ AI ಸಿದ್ಧಪಡಿಸಿದ್ದು ವೈದ್ಯರಿಂದ ಅಧಿಕೃತವಾಗಿ ಅನುಮೋದಿಸಲಾಗಿದೆ.",
        },
        "ml": {
            "title": "നിങ്ങളുടെ ഡോക്ടർ പരിശോധന സംഗ്രഹം & പരിചരണ പദ്ധതി",
            "lang_name": "മലയാളം പരിഭാഷ (Malayalam)",
            "greeting": "നമസ്കാരം, ഞങ്ങളുടെ ക്ലിനിക്ക് സന്ദർശിച്ചതിന് നന്ദി.",
            "reason": "പനി, തൊണ്ടവേദന, ശരീരവേദന എന്നിവയ്ക്കുള്ള പരിശോധന.",
            "findings": "പരിശോധനയിൽ തൊണ്ടയിലെ വീക്കവും വൈറൽ അണുബാധയും കണ്ടെത്തി.",
            "diet": "- ചൂടുവെള്ളം കുടിക്കുക, ആവശ്യത്തിന് വിശ്രമിക്കുക.\n- തണുത്ത ഭക്ഷണപാനീയങ്ങൾ ഒഴിവാക്കുക.",
            "warning": "ശ്വാസമെടുക്കാൻ ബുദ്ധിമുട്ടോ കടുത്ത പനിയോ ഉണ്ടായാൽ ഉടൻ ബന്ധപ്പെടുക.",
            "followup": "3 ദിവസത്തിന് ശേഷം രോഗശമനം ഇല്ലെങ്കിൽ തുടർ പരിശോധനയ്ക്ക് വരിക.",
            "disclaimer": "ഈ സംഗ്രഹം ആരോഗ്യസ്ക്രൈബ് AI തയ്യാറാക്കി ഡോക്ടർ പരിശോധിച്ച് അംഗീകരിച്ചതാണ്.",
        },
        "mr": {
            "title": "तुमच्या डॉक्टरांच्या सल्ल्याचा सारांश आणि काळजी योजना",
            "lang_name": "मराठी अनुवाद (Marathi)",
            "greeting": "नमस्ते, आमच्या क्लिनिकला भेट दिल्याबद्दल धन्यवाद.",
            "reason": "ताप, घसा दुखणे आणि खोकल्यासाठी तपासणी.",
            "findings": "तपासणीत घशात सूज आणि सौम्य संसर्ग आढळला आहे.",
            "diet": "- कोमट पाणी प्या आणि पुरेशी विश्रांती घ्या.\n- थंड पदार्थ आणि तेलकट अन्न टाळा.",
            "warning": "श्वास घेण्यास त्रास झाल्यास किंवा तीव्र ताप आल्यास तातडीने संपर्क साधा.",
            "followup": "३ दिवसांनंतर आराम न वाटल्यास पुन्हा भेटा.",
            "disclaimer": "हा सारांश आरोग्यस्क्राइब AI द्वारे तयार केला असून डॉक्टरांनी मंजूर केला आहे.",
        },
        "bn": {
            "title": "আপনার ডাক্তারের পরামর্শের সারসংক্ষেপ ও পরিচর্যা পরিকল্পনা",
            "lang_name": "বাংলা অনুবাদ (Bengali)",
            "greeting": "নমস্কার, আমাদের ক্লিনিকে আসার জন্য ধন্যবাদ।",
            "reason": "জ্বর, গলা ব্যথা ও শারীরিক অস্বস্তির পরামর্শ।",
            "findings": "পরীক্ষায় গলায় ফোলাভাব এবং ভাইরাল সংক্রমণের লক্ষণ পাওয়া গেছে।",
            "diet": "- হালকা গরম জল পান করুন এবং পর্যাপ্ত বিশ্রাম নিন।\n- ঠান্ডা খাবার ও পানীয় এড়িয়ে চলুন।",
            "warning": "শ্বাসকষ্ট বা তীব্র জ্বর (১০২°F এর বেশি) দেখা দিলে অবিলম্বে যোগাযোগ করুন।",
            "followup": "৩ দিন পর উপসর্গের উন্নতি না হলে আবার আসুন।",
            "disclaimer": "এই সারসংক্ষেপটি আরোগ্যস্ক্রাইব AI দ্বারা তৈরি এবং ডাক্তার দ্বারা অনুমোদিত।",
        },
        "gu": {
            "title": "તમારા ડૉક્ટર પરામર્શનો સારાંશ અને સંભાળ યોજના",
            "lang_name": "ગુજરાતી અનુવાદ (Gujarati)",
            "greeting": "નમસ્તે, અમારા ક્લિનિકની મુલાકાત લેવા બદલ આભાર.",
            "reason": "તાવ, ગળામાં દુખાવો અને શરદી માટે પરામર્શ.",
            "findings": "તપાસમાં ગળામાં સોજો અને વાયરલ ચેપના લક્ષણો જણાયા છે.",
            "diet": "- નવશેકું પાણી પીવો અને પૂરતો આરામ કરો.\n- ઠંડા પીણાં અને તેલી ખોરાક ટાળો.",
            "warning": "શ્વાસ લેવામાં તકલીફ થાય અથવા વધુ તાવ રહે તો તરત જ સંપર્ક કરો.",
            "followup": "૩ દિવસ પછી રાહત ન થાય તો ફોલો-અપ માટે આવો.",
            "disclaimer": "આ સારાંશ આરોગ્યસ્ક્રાઇબ AI દ્વારા તૈયાર કરવામાં આવ્યો છે અને ડૉક્ટર દ્વારા મંજૂર થયેલ છે.",
        },
    }

    async def translate_patient_summary(
        self,
        summary_markdown: str,
        structured_json: dict[str, Any],
        target_language: str,
    ) -> tuple[str, dict[str, Any]]:
        # Normalize language prefix (e.g., "ta-IN" -> "ta")
        lang_key = target_language.split("-")[0].lower() if target_language else "en"

        if lang_key in self.INDIC_TEMPLATES:
            tpl = self.INDIC_TEMPLATES[lang_key]
            # Extract medication lines from original summary to keep drug names & schedules unchanged
            med_lines = []
            for line in summary_markdown.splitlines():
                if line.strip().startswith("- **") or line.strip().startswith("* **"):
                    med_lines.append(line.strip())
            meds_block = "\n".join(med_lines) if med_lines else "- Paracetamol 650mg: 1 tablet 3 times daily for 3 days\n- Azithromycin 500mg: 1 tablet once daily for 3 days"

            translated_md = f"""# {tpl['title']}

> [!NOTE]
> **{tpl['lang_name']}**: भाषा अनुवाद सारांश

### 1. {tpl['greeting']}

### 2. आने का कारण / Reason for Visit
{tpl['reason']}

### 3. डॉक्टर का निष्कर्ष / Clinical Impression
{tpl['findings']}

### 4. दवाइयां लेने का नियम / Prescribed Medicines (Unchanged)
{meds_block}

### 5. खान-पान और देखभाल सलाह / Diet & Care
{tpl['diet']}

### 6. आपातकालीन चेतावनी संकेत / Warning Signs
{tpl['warning']}

### 7. दोबारा मिलने का समय / Follow-Up
{tpl['followup']}

### 8. {tpl['disclaimer']}
"""
            return translated_md.strip(), structured_json

        return summary_markdown, structured_json


class MockTextToSpeechProvider:
    """Produces mock audio bytes representing synthetic vernacular narration."""

    async def synthesize_speech(
        self,
        text: str,
        language_code: str = "hi-IN",
        voice_id: str | None = None,
    ) -> bytes:
        # Return a minimal 44-byte RIFF WAV header for testing
        riff = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
        return riff

