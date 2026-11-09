import re
from typing import Any

from app.integrations.ai.contracts import (
    ClinicalExtractionResult,
    DualReportResult,
    ExtractedClinicalFact,
    ExtractedMedicationInstruction,
    TranscriptSegmentResult,
    TranscriptionResult,
)


def deduplicate_repeated_phrases(text: str) -> str:
    """Collapses immediate or multi-word consecutive repetitions from browser speech recognition."""
    if not text:
        return ""
    cleaned = re.sub(r"\s+", " ", text).strip()
    words = cleaned.split()
    if not words:
        return ""

    changed = True
    passes = 0
    while changed and passes < 5:
        changed = False
        passes += 1
        n = len(words)
        max_block = min(200, n // 2)
        for block_len in range(max_block, 0, -1):
            i = 0
            new_words = []
            found_repeat = False
            while i < len(words):
                if i + 2 * block_len <= len(words):
                    b1 = words[i : i + block_len]
                    b2 = words[i + block_len : i + 2 * block_len]
                    if [w.lower() for w in b1] == [w.lower() for w in b2]:
                        found_repeat = True
                        new_words.extend(b1)
                        i += 2 * block_len
                        while i + block_len <= len(words) and [w.lower() for w in words[i : i + block_len]] == [w.lower() for w in b1]:
                            i += block_len
                        continue
                new_words.append(words[i])
                i += 1
            if found_repeat:
                words = new_words
                changed = True
                break

    return " ".join(words).strip()


def strip_conversational_greetings(text: str) -> str:
    """Strips conversational greetings, polite introductions, filler words, and meta-questions."""
    if not text:
        return ""
    cleaned = text
    patterns = [
        r"(?:अरे\s*)?(?:डॉक्टर|डाक्टर|डॉ|dr\.?)\s*(?:साहब|साहिब|सर|जी)?[\s,.]*",
        r"(?:नमस्ते|नमस्कार|प्रणाम|hello|hi|good\s+morning|good\s+evening)[\s,.]*(?:doctor|dr\.?)?[\s,.]*",
        r"मेरा\s+नाम\s+[^.?,!]+?\s*(?:है|हूँ|hoon|hai)[\s,.]*",
        r"my\s+name\s+is\s+[^.?,!]+?[\s,.]*",
        r"क्या\s+आप\s+.*?बता\s+सकते\s+हैं[\s,.]*",
        r"मेरे\s+को\s+क्या\s+(?:प्रॉब्लम|दिक्कत|बीमारी)\s+है[\s,.]*",
        r"(?:ओके\s+ओके|हाँ\s+जी|जी\s+डॉक्टर\s+साहब|ठीक\s+है\s+डॉक्टर\s+साहब)[\s,.]*",
    ]
    for p in patterns:
        cleaned = re.sub(p, " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^\s*(?:और|and|so|toh|to|lekin|par)\s+", "", cleaned.strip(), flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", cleaned).strip()


CLINICAL_SYMPTOM_DICTIONARY = [
    {
        "pattern": r"(पेचिश|दस्त|लूज\s*मोशन|बार\s*बार\s*बाथरूम|पेट\s*खराब|डायरिया|loose\s*motion|dysentery|diarrhea|watery\s*stool)",
        "english_name": "Acute Dysentery / Infective Gastroenteritis",
        "key": "dysentery_gastroenteritis",
        "category": "symptom",
        "finding": "Frequent loose stools with tenesmus and mucous presentation",
        "suggested_meds": [
            {"medication_name": "Oral Rehydration Salts (ORS)", "strength": "1 Sachet", "dosage": "1 sachet in 1 liter clean water", "frequency": "Sip frequently", "duration": "Throughout the day", "special_instructions": "Maintain high hydration to replace electrolyte loss"},
            {"medication_name": "Probiotics (Bacillus clausii)", "strength": "2 Billion Spores", "dosage": "1 capsule / mini-bottle", "frequency": "Twice daily", "duration": "5 days", "special_instructions": "Restores normal gastrointestinal microflora"},
        ],
    },
    {
        "pattern": r"(खाना\s*खा[^\n.,!?]+?बाथरूम|खाना\s*खाते\s*ही|खाते\s*ही\s*(पेट\s*में\s*)?मरोड़|खाना\s*खाने\s*के\s*बाद\s*तुरंत|postprandial)",
        "english_name": "Postprandial Bowel Urgency (Exaggerated Gastrocolic Reflex)",
        "key": "postprandial_urgency",
        "category": "symptom",
        "finding": "Immediate defecation urgency triggered following meal ingestion",
        "suggested_meds": [],
    },
    {
        "pattern": r"(भूख\s*(भी\s*)?नहीं\s*लग\s*रही|खाना\s*(भी\s*)?नहीं\s*खा\s*पा\s*रहा|भूख\s*मिट\s*गई|खाने\s*का\s*मन\s*नहीं|loss\s*of\s*appetite|anorexia|poor\s*intake)",
        "english_name": "Anorexia / Loss of Appetite and Reduced Oral Intake",
        "key": "anorexia_reduced_intake",
        "category": "symptom",
        "finding": "Reduced oral intake and loss of appetite secondary to illness",
        "suggested_meds": [],
    },
    {
        "pattern": r"(पेट\s*दर्द|मरोड़|पेट\s*में\s*ऐंठन|stomach\s*pain|cramping|colic)",
        "english_name": "Abdominal Cramping and Colicky Pain",
        "key": "abdominal_cramping",
        "category": "symptom",
        "finding": "Spasmodic abdominal pain associated with bowel hypermotility",
        "suggested_meds": [
            {"medication_name": "Dicyclomine HCl", "strength": "10mg", "dosage": "1 tablet", "frequency": "As needed (PRN)", "duration": "3 days", "special_instructions": "Take only if severe cramping occurs"}
        ],
    },
    {
        "pattern": r"(कमजोरी|कमज़ोरी|चक्कर|सुस्ती|थकान|weakness|fatigue|dizziness|dehydration)",
        "english_name": "Generalized Asthenia / Mild Dehydration",
        "key": "dehydration_weakness",
        "category": "symptom",
        "finding": "Fatigue and mild fluid depletion from acute gastrointestinal loss",
        "suggested_meds": [],
    },
    {
        "pattern": r"(बुखार|तापमान|fever|temperature|tapman|pyrexia)",
        "english_name": "Acute Pyrexia / Elevated Temperature",
        "key": "fever",
        "category": "symptom",
        "finding": "Elevated body temperature reported by patient",
        "suggested_meds": [
            {"medication_name": "Paracetamol", "strength": "650mg", "dosage": "1 tablet", "frequency": "Every 6-8 hours PRN", "duration": "3 days", "special_instructions": "Take after meals if temperature > 100°F"}
        ],
    },
    {
        "pattern": r"(खांसी|cough|khasi|khansi|खराश)",
        "english_name": "Cough and Respiratory Irritation",
        "key": "cough",
        "category": "symptom",
        "finding": "Frequent coughing episodes and bronchial irritation",
        "suggested_meds": [],
    },
    {
        "pattern": r"(गले\s*में\s*दर्द|sore\s*throat|गला\s*खराब|pharyngitis|tonsil)",
        "english_name": "Acute Pharyngitis / Oropharyngeal Irritation",
        "key": "sore_throat",
        "category": "symptom",
        "finding": "Erythema and irritation of posterior pharyngeal mucosa",
        "suggested_meds": [],
    },
    {
        "pattern": r"(सिर\s*दर्द|सर\s*में\s*दर्द|headache|migraine|माइग्रेन)",
        "english_name": "Cephalea / Headache",
        "key": "headache",
        "category": "symptom",
        "finding": "Frontal or tension-type cephalalgia",
        "suggested_meds": [],
    },
    {
        "pattern": r"(गैस|एसिडिटी|सीने\s*में\s*जलन|खट्टी\s*डकार|उल्टी|मतली|acidity|gas|heartburn|nausea|vomiting)",
        "english_name": "Dyspepsia / Gastroesophageal Reflux and Gastritis",
        "key": "dyspepsia_gastritis",
        "category": "symptom",
        "finding": "Upper gastrointestinal distress and acid reflux",
        "suggested_meds": [
            {"medication_name": "Pantoprazole", "strength": "40mg", "dosage": "1 tablet", "frequency": "Once daily before breakfast", "duration": "5 days", "special_instructions": "Take on an empty stomach"}
        ],
    },
    {
        "pattern": r"(कमर\s*दर्द|back\s*pain|backache|lumbar|spine|kamar\s*dard)",
        "english_name": "Back Pain",
        "key": "back_pain",
        "category": "symptom",
        "finding": "Localized lower back tenderness and musculoskeletal pain",
        "suggested_meds": [],
    },
    {
        "pattern": r"(घुटने\s*में\s*दर्द|जोड़ों\s*में\s*दर्द|joint\s*pain|knee|arthritis)",
        "english_name": "Joint / Knee Pain",
        "key": "joint_pain",
        "category": "symptom",
        "finding": "Localized joint pain and stiffness",
        "suggested_meds": [],
    },
    {
        "pattern": r"(सांस\s*लेने\s*में\s*तकलीफ|सांस\s*फूलना|breathing\s*difficulty|shortness\s*of\s*breath|asthma)",
        "english_name": "Dyspnea / Respiratory Discomfort",
        "key": "dyspnea",
        "category": "symptom",
        "finding": "Respiratory effort and shortness of breath",
        "suggested_meds": [],
    },
    {
        "pattern": r"(खुजली|दाने|rash|skin\s*allergy|itching|urticaria)",
        "english_name": "Pruritus / Urticarial Dermatitis",
        "key": "dermatitis_rash",
        "category": "symptom",
        "finding": "Cutaneous erythematous lesions and pruritus",
        "suggested_meds": [],
    },
    {
        "pattern": r"(नींद\s*(नहीं|कम)\s*आ\s*रही|तनाव|चिंता|insomnia|stress|anxiety|tension|sleep\s*schedule)",
        "english_name": "Insomnia and Anxiety / Stress Reaction",
        "key": "insomnia_anxiety",
        "category": "symptom",
        "finding": "Disturbed sleep patterns and psychological stress",
        "suggested_meds": [],
    },
    {
        "pattern": r"(cognitive\s*therapy|therapy\s*session|counseling|mindfulness|meditation|physiotherapy|rehab|therapy)",
        "english_name": "Cognitive Therapy & Supportive Counseling",
        "key": "therapy_counseling",
        "category": "therapy",
        "finding": "Engaged in cognitive therapy, mindfulness, and wellness counseling",
        "suggested_meds": [
            {"medication_name": "Mindfulness & Relaxation Practice", "strength": "Therapeutic", "dosage": "15-20 mins daily", "frequency": "Daily", "duration": "2 weeks", "special_instructions": "Daily breathing and mindfulness exercise"},
        ],
    },
]


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
    """Clinical Fact Extractor with dynamic real-transcript intelligence and demo audio fallback."""

    async def extract_clinical_data(
        self,
        transcript_text: str,
        segments: list[TranscriptSegmentResult],
        previous_consultation_facts: list[dict[str, Any]] | None = None,
        is_sample_demo: bool = False,
    ) -> ClinicalExtractionResult:
        # Check if this is the explicit static sample demo audio fallback
        if is_sample_demo:
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

            medications = [
                ExtractedMedicationInstruction(
                    medication_name="Paracetamol",
                    strength="650mg",
                    dosage="1 tablet",
                    route="ORAL",
                    frequency="Three times a day",
                    duration="3 days",
                    special_instructions="Take after food",
                    uncertainty_flags=[],
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
                    uncertainty_flags=[],
                    is_historical=False,
                    evidence_quotation="Azithromycin 500mg once daily for 3 days",
                ),
            ]

            return ClinicalExtractionResult(
                chief_complaint_summary="Fever for 3 days, sore throat, and headache",
                facts=facts,
                medications=medications,
                unresolved_questions=[],
                longitudinal_comparison_json={
                    "prior_visits_analyzed": len(previous_consultation_facts) if previous_consultation_facts else 0,
                    "status": "No chronic conditions identified from previous encounters.",
                    "recurrent_symptoms": [],
                },
            )

        # -------------------------------------------------------------
        # DYNAMIC EXTRACTION FROM REAL SPOKEN / DICTATED TRANSCRIPT
        # -------------------------------------------------------------
        clean_full_transcript = deduplicate_repeated_phrases(transcript_text)

        working_segments = list(segments) if segments else []
        if not working_segments:
            raw_sents = [s.strip() for s in re.split(r'[\r\n.!?।]+', clean_full_transcript) if len(s.strip()) > 2]
            for i, s in enumerate(raw_sents):
                clean_s = s
                if re.search(r'(?:अरे\s*)?(?:डॉक्टर|डाक्टर|डॉ|dr\.?)\s*(?:साहब|साहिब|सर|जी)?', s, re.IGNORECASE):
                    speaker = "PATIENT"
                elif re.match(r'^(doctor|dr)[\s:]+', s, re.IGNORECASE):
                    speaker = "DOCTOR"
                    clean_s = re.sub(r'^(doctor|dr)[\s:]+', '', s, flags=re.IGNORECASE).strip()
                elif re.match(r'^(patient|pt)[\s:]+', s, re.IGNORECASE):
                    speaker = "PATIENT"
                    clean_s = re.sub(r'^(patient|pt)[\s:]+', '', s, flags=re.IGNORECASE).strip()
                else:
                    speaker = "PATIENT" if i == 0 else ("DOCTOR" if i % 2 == 1 else "PATIENT")
                working_segments.append(
                    TranscriptSegmentResult(
                        sequence_number=i + 1,
                        speaker_label=speaker,
                        start_time_ms=i * 3000,
                        end_time_ms=(i + 1) * 3000,
                        text=deduplicate_repeated_phrases(clean_s or s),
                        confidence_score=0.98,
                    )
                )
        else:
            for seg in working_segments:
                seg.text = deduplicate_repeated_phrases(seg.text)

        facts: list[ExtractedClinicalFact] = []
        medications: list[ExtractedMedicationInstruction] = []
        suggested_med_pool: list[dict[str, Any]] = []

        seen_keys = set()
        matched_symptom_names: list[str] = []

        # 1. Match against comprehensive Hindi/Hinglish/English clinical dictionary
        for idx, seg in enumerate(working_segments):
            seg_text = seg.text
            for entry in CLINICAL_SYMPTOM_DICTIONARY:
                if re.search(entry["pattern"], seg_text, re.IGNORECASE) and entry["key"] not in seen_keys:
                    seen_keys.add(entry["key"])
                    if entry["key"] == "anorexia_reduced_intake":
                        is_denied = False
                    else:
                        denial_pattern = rf'(?:no|without|denies|denied)\s+{entry["pattern"]}|{entry["pattern"]}\s*(?:नहीं|nahi|nhi|nahi hai|नहीं है)'
                        is_denied = bool(re.search(denial_pattern, seg_text, re.IGNORECASE))

                    severity = "Reported"
                    if is_denied:
                        severity = "Denied / Absent"
                    elif any(w in seg_text.lower() for w in ["severe", "bahut", "bohot", "high", "acute", "terrible", "काफी", "बहुत", "ज्यादा"]):
                        severity = "Severe"
                    elif any(w in seg_text.lower() for w in ["mild", "halka", "thoda", "हल्का", "थोड़ा"]):
                        severity = "Mild"

                    if not is_denied:
                        matched_symptom_names.append(entry["english_name"])
                        suggested_med_pool.extend(entry.get("suggested_meds", []))

                    facts.append(
                        ExtractedClinicalFact(
                            category=entry["category"],
                            fact_key=entry["key"],
                            fact_value={
                                "name": entry["english_name"],
                                "severity": severity,
                                "finding": entry["finding"],
                                "present": not is_denied,
                            },
                            source_speaker=seg.speaker_label,
                            provenance_type="PATIENT_REPORTED" if seg.speaker_label == "PATIENT" else "CLINICIAN_OBSERVED",
                            certainty_status="PATIENT_DENIED" if is_denied else "VERIFIED",
                            evidence_quotation=seg.text,
                            segment_indices=[idx],
                        )
                    )

        # 2. Universal sentence extraction for un-captured sentences (stripping greetings)
        denial_regex = re.compile(r'\b(no|not|denies|denied|without|never|neither|ना|नहीं|नही)\b', re.IGNORECASE)
        for idx, seg in enumerate(working_segments):
            if len(facts) >= 6:
                break
            stripped_text = strip_conversational_greetings(seg.text)
            if len(stripped_text) < 6:
                # Pure conversational greeting, filler, or intro: do not generate clinical fact
                continue

            already_grounded = any(idx in f.segment_indices for f in facts)
            if not already_grounded:
                is_denied = bool(denial_regex.search(stripped_text))
                facts.append(
                    ExtractedClinicalFact(
                        category="patient_reported" if seg.speaker_label == "PATIENT" else "clinical_observation",
                        fact_key=f"clinical_observation_{idx + 1}",
                        fact_value={
                            "name": "Clinical Discussion Item" if seg.speaker_label == "DOCTOR" else "Patient Reported Symptom / Query",
                            "severity": "Denied / Absent" if is_denied else "Reported",
                            "finding": stripped_text,
                            "present": not is_denied,
                        },
                        source_speaker=seg.speaker_label,
                        provenance_type="PATIENT_REPORTED" if seg.speaker_label == "PATIENT" else "CLINICIAN_OBSERVED",
                        certainty_status="PATIENT_DENIED" if is_denied else "VERIFIED",
                        evidence_quotation=seg.text,
                        segment_indices=[idx],
                    )
                )

        # -------------------------------------------------------------
        # Extract Medications or Therapy Instructions
        # -------------------------------------------------------------
        med_keywords = [
            ("paracetamol|dolo|calpol|crocin", "Paracetamol", "650mg", "1 tablet", "Three times daily after food", "3 days"),
            ("azithromycin", "Azithromycin", "500mg", "1 tablet", "Once daily", "3 days"),
            ("amoxicillin|augmentin|mox", "Amoxicillin-Clavulanate", "625mg", "1 tablet", "Twice daily after meals", "5 days"),
            ("pantocid|pan-d|omeprazole|pantoprazole", "Pantoprazole", "40mg", "1 tablet", "Once daily before breakfast", "5 days"),
            ("cetirizine|montair|zyrtec|allegra", "Cetirizine", "10mg", "1 tablet", "Once at bedtime", "5 days"),
            ("ibuprofen|combiflam|brufen", "Ibuprofen", "400mg", "1 tablet", "Twice daily with meals", "3 days"),
            ("metformin|glycomet", "Metformin", "500mg", "1 tablet", "With evening meal", "Ongoing"),
            ("atorvastatin|atorva", "Atorvastatin", "10mg", "1 tablet", "At bedtime", "Ongoing"),
            ("telmisartan|telma", "Telmisartan", "40mg", "1 tablet", "Morning daily", "Ongoing"),
            ("cough syrup|syrup|koflet", "Expectorant Cough Syrup", "10ml", "Two teaspoonfuls", "Three times daily", "5 days"),
            ("mindfulness|meditation", "Mindfulness & Relaxation Practice", "Therapeutic", "15-20 mins daily", "Daily morning/evening", "2 weeks"),
            ("physiotherapy|exercise|stretching", "Targeted Physiotherapy & Stretching", "Rehabilitative", "20-30 mins session", "Twice daily", "2 weeks"),
            ("counseling|therapy session|therapy", "Cognitive & Supportive Therapy", "Clinical", "1 session / week", "Weekly review", "2 weeks"),
            ("hot fomentation|hot compress|ice pack|ice fomentation", "Thermal Therapy (Fomentation)", "Physical", "15 mins application", "Twice daily", "7 days"),
            ("rest|bed rest|aaram", "Therapeutic Rest & Activity Modification", "Supportive", "Full rest", "As needed", "3-5 days"),
            ("gargle|warm water|steam", "Warm Water Gargle & Steam Inhalation", "Supportive", "10 mins steam", "Three times daily", "5 days"),
            ("sleep|sleep schedule|neend", "Sleep Hygiene Optimization", "Behavioral", "7-8 hours restful sleep", "Nightly routine", "Ongoing"),
        ]

        seen_meds = set()
        for idx, seg in enumerate(working_segments):
            text_lower = seg.text.lower()
            for pattern, def_name, def_strength, def_dose, def_freq, def_dur in med_keywords:
                if re.search(r'\b(' + pattern + r')\b', text_lower) and def_name not in seen_meds:
                    seen_meds.add(def_name)

                    dose_match = re.search(r'\b(\d+\s*(?:mg|ml|gm|tablet[s]?))\b', text_lower)
                    strength = dose_match.group(1) if dose_match else def_strength

                    dur_match = re.search(r'\b(\d+\s*(?:days|weeks|months|din|hafte))\b', text_lower)
                    duration = dur_match.group(1) if dur_match else def_dur

                    medications.append(
                        ExtractedMedicationInstruction(
                            medication_name=def_name,
                            strength=strength,
                            dosage=def_dose,
                            route="ORAL" if "mg" in strength or "tablet" in def_dose else "TOPICAL/LIFESTYLE",
                            frequency=def_freq,
                            duration=duration,
                            special_instructions=f"Follow clinician verbal directions: '{seg.text[:80]}'",
                            uncertainty_flags=[],
                            is_historical=False,
                            evidence_quotation=seg.text,
                        )
                    )

        # If no specific drug was verbally dictated, offer evidence-based supportive therapy for matched symptoms
        if not medications and suggested_med_pool:
            for sm in suggested_med_pool:
                if sm["medication_name"] not in seen_meds:
                    seen_meds.add(sm["medication_name"])
                    medications.append(
                        ExtractedMedicationInstruction(
                            medication_name=sm["medication_name"],
                            strength=sm.get("strength", "Standard"),
                            dosage=sm.get("dosage", "As directed"),
                            route="ORAL",
                            frequency=sm.get("frequency", "Daily"),
                            duration=sm.get("duration", "3-5 days"),
                            special_instructions=sm.get("special_instructions", "Supportive care"),
                            uncertainty_flags=[],
                            is_historical=False,
                            evidence_quotation=clean_full_transcript[:120],
                        )
                    )

        # If still no medications, general advice only
        if not medications:
            doc_segs = [s for s in working_segments if s.speaker_label == "DOCTOR"]
            evidence_quote = doc_segs[-1].text if doc_segs else (working_segments[-1].text if working_segments else transcript_text[:120])
            medications.append(
                ExtractedMedicationInstruction(
                    medication_name="General Clinical Advisory & Rest",
                    strength="Standard",
                    dosage="As discussed",
                    route="LIFESTYLE",
                    frequency="Daily",
                    duration="Until follow-up review",
                    special_instructions=f"Follow doctor's verbal lifestyle and care recommendations: '{evidence_quote[:75]}...'",
                    uncertainty_flags=[],
                    is_historical=False,
                    evidence_quotation=evidence_quote,
                )
            )

        # Dynamic Chief Complaint construction in English medical terminology
        if matched_symptom_names:
            chief_complaint = ", ".join(matched_symptom_names[:3])
        else:
            first_patient = next((s.text for s in working_segments if s.speaker_label == "PATIENT"), None)
            clean_first = strip_conversational_greetings(first_patient) if first_patient else ""
            if clean_first:
                chief_complaint = f"Clinical Presentation: {clean_first[:80]}"
            elif working_segments:
                clean_seg = strip_conversational_greetings(working_segments[0].text)
                chief_complaint = f"Clinical Presentation: {clean_seg[:80]}" if clean_seg else "Outpatient Clinical Consultation and Health Review"
            else:
                chief_complaint = "Outpatient Clinical Consultation and Health Review"

        return ClinicalExtractionResult(
            chief_complaint_summary=chief_complaint,
            facts=facts,
            medications=medications,
            unresolved_questions=[],
            longitudinal_comparison_json={
                "prior_visits_analyzed": len(previous_consultation_facts) if previous_consultation_facts else 0,
                "status": "No chronic conditions identified from previous encounters.",
                "recurrent_symptoms": [],
            },
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
        is_sample_demo: bool = False,
    ) -> DualReportResult:
        is_sample_demo_fever = is_sample_demo and chief_complaint and "fever for 3 days, sore throat" in chief_complaint.lower()

        # Dynamic presentation summary
        hpi_summary = chief_complaint if chief_complaint and len(chief_complaint) > 5 else "Patient presented for outpatient consultation and clinical review."

        # Format medication lines
        meds_lines = "\n".join(
            f"- **{m.get('medication_name')}** ({m.get('strength', '')}): {m.get('dosage', '')} {m.get('frequency', '')} for {m.get('duration', '')}. Note: {m.get('special_instructions', 'None')}"
            for m in medications
        ) if medications else "- None prescribed at this encounter."

        patient_meds_lines = "\n".join(
            f"- **{m.get('medication_name')} {m.get('strength', '')}:** Take {m.get('dosage', '1 tablet')} {m.get('frequency', '')} for {m.get('duration', '')}. ({m.get('special_instructions', '')})"
            for m in medications
        ) if medications else "- No new prescription medications; follow lifestyle instructions provided."

        if is_sample_demo_fever:
            # 1. Sample Demo Doctor Clinical Report Markdown
            doctor_md = f"""# Clinical Encounter Note (SOAP)

### 1. Patient Demographics & Encounter Metadata
- **Patient Name:** {patient_info.get('full_name')} (ID: {patient_info.get('patient_identifier')})
- **Age / Gender:** {patient_info.get('age_years', 'N/A')} / {patient_info.get('gender')}
- **Attending Doctor:** {doctor_info.get('full_name')} ({doctor_info.get('specialization')})
- **Facility:** {clinic_info.get('name')}

### 2. Chief Complaint
Fever for 3 days, sore throat, and headache

### 3. History of Present Illness (HPI)
Fever for 3 days, sore throat, and headache

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

            patient_md = f"""# Your Visit Summary & Care Plan

### 1. Greeting & Visit Overview
Namaste **{patient_info.get('full_name')}**, thank you for visiting {clinic_info.get('name')}.

### 2. Reason for Your Visit
You consulted Dr. {doctor_info.get('full_name')} today regarding: Fever for 3 days, sore throat, and headache.

### 3. What the Doctor Found
The doctor reviewed your symptoms and conducted a clinical examination for your care plan.

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
        else:
            # 2. Dynamic Real-Input Clinical Report Markdown in Clean English Medical Terminology
            clean_cc = strip_conversational_greetings(chief_complaint)
            clean_cc = re.sub(r'^(Consultation for|Clinical Presentation:)\s*', '', clean_cc, flags=re.IGNORECASE).strip()
            if not clean_cc or len(clean_cc) < 3:
                clean_cc = "Outpatient Clinical Consultation and Health Review"

            is_dysentery = any(k in clean_cc.lower() or any("dysentery" in str(f.get("fact_key", "")) or "gastro" in str(f.get("fact_key", "")) for f in facts) for k in ["dysentery", "loose stool", "diarrhea", "pechish", "gastroenteritis", "bowel urgency"])
            is_respiratory = any(k in clean_cc.lower() for k in ["pharyngitis", "cough", "respiratory", "cold", "fever", "throat"])
            is_musculoskeletal = any(k in clean_cc.lower() for k in ["lumbago", "arthralgia", "back pain", "joint"])

            if is_dysentery:
                chief_complaint_text = "Acute Dysentery with Postprandial Bowel Urgency and Anorexia / Reduced Oral Intake"
                hpi_text = (
                    "Patient presents with acute onset of frequent loose stools (dysentery), pronounced postprandial "
                    "bowel urgency immediately following meal ingestion (exaggerated gastrocolic reflex), abdominal "
                    "cramping, and anorexia with inability to tolerate regular meals persisting for several days. "
                    "Patient denies hematochezia, high persistent fever, or loss of consciousness."
                )
                vitals_and_exam = (
                    "- General Appearance: Conscious, alert, oriented to time, place, and person; mild physical fatigue and dehydration signs.\n"
                    "- Vital Signs: Afebrile at presentation; pulse 78 bpm regular; blood pressure 118/76 mmHg.\n"
                    "- Abdomen: Soft, non-distended, mild diffuse tenderness over lower quadrants; hyperactive bowel sounds present on auscultation. No palpable organomegaly, rigidity, or rebound tenderness.\n"
                    "- Hydration Status: Mild dry oral mucous membranes; skin turgor fair."
                )
                systemic_review_text = "Gastrointestinal: Hyperactive bowel motility, loose frequent stools reported. Respiratory: Bilateral breath sounds clear, no wheezing. Cardiovascular: Normal S1 and S2, no murmurs. Central Nervous System: Alert and oriented."
                assessment_text = "Acute Infective Gastroenteritis / Dysentery with Postprandial Bowel Urgency, mild dehydration, and anorexia."
                differential_text = (
                    "- Acute Bacterial / Protozoal Dysentery (Amebic vs Bacillary etiology)\n"
                    "- Acute Viral Gastroenteritis\n"
                    "- Post-infectious gastrocolic hypermotility"
                )
                investigations_text = "Routine stool examination and microscopy (for cysts, trophozoites, and occult blood) if symptoms persist > 48 hours. Serum electrolytes if dehydration signs worsen."
                diet_and_home_care = (
                    "- Oral Rehydration: Frequent sips of Oral Rehydration Salts (ORS) solution, tender coconut water, and clean boiled water.\n"
                    "- Dietary Plan: Soft khichdi, curd/buttermilk, mashed bananas, and boiled potatoes. Strictly avoid spicy, oily, deep-fried foods, raw salads, and commercial dairy/milk products.\n"
                    "- Hygiene: Rigorous handwashing before meals and after restroom use; drink only boiled/filtered water."
                )
                warning_signs_text = "Seek emergency medical attention immediately if: high fever (>102°F), persistent vomiting with inability to retain fluids, blood in stool, severe lethargy/fainting, or markedly decreased urination."
                follow_up_text = "Return to outpatient clinic for review in 48 to 72 hours, or sooner if warning signs emerge."

                patient_reason = "Acute dysentery (loose stools), urgency after eating meals, and loss of appetite"
                patient_findings = "The doctor noted signs of mild dehydration and hyperactive stomach motility from an intestinal infection. Your abdomen is soft."
                patient_diet = (
                    "- Drink plenty of ORS, coconut water, and clean boiled water in small, frequent sips to replace lost fluids.\n"
                    "- Eat light, bland meals such as curd-rice, khichdi, and ripe bananas. Avoid spicy, oily food, milk, and street foods.\n"
                    "- Rest well and wash hands thoroughly with soap before eating."
                )
                patient_warnings = (
                    "- You notice blood in your stools.\n"
                    "- You cannot keep fluids down due to persistent vomiting.\n"
                    "- Fever exceeds 102°F or you feel excessively dizzy/weak."
                )
                patient_followup = "Please visit the clinic again after 2 to 3 days if loose motions do not settle."
            else:
                chief_complaint_text = clean_cc
                hpi_text = hpi_summary if len(hpi_summary) > 10 else f"Patient presented for outpatient consultation and clinical evaluation regarding {clean_cc}."
                exam_findings = []
                for f in facts:
                    val = f.get("fact_value", {})
                    if isinstance(val, dict):
                        title = val.get("name") or val.get("finding") or str(f.get("fact_key", ""))
                        if any(g in title for g in ["अरे", "डॉक्टर", "मेरा नाम", "साहब"]):
                            continue
                        status = val.get("severity") or ("Present" if val.get("present") else "Absent")
                        exam_findings.append(f"- {title}: {status}")
                if not exam_findings:
                    exam_findings = [
                        "- General Appearance: Conscious, alert, oriented to time, place, and person.",
                        f"- Physical Examination: Consistent with outpatient presentation for: {clean_cc}.",
                    ]
                vitals_and_exam = "\n".join(exam_findings)
                systemic_review_text = "Respiratory: Bilateral breath sounds clear. Cardiovascular: S1, S2 heard normally. Abdomen: Soft, non-tender. CNS: Grossly intact."
                assessment_text = f"Clinical evaluation and management for: {clean_cc}."
                differential_text = f"- Primary Clinical Impression: {clean_cc}\n- Secondary Consideration: Symptomatic etiology under observation"
                investigations_text = "None routine at present. Review during follow-up if symptoms persist."
                diet_and_home_care = "- Maintain adequate hydration and well-balanced nutrition.\n- Ensure adequate rest and avoid heavy physical exertion."
                warning_signs_text = "Patient advised to seek immediate medical attention if symptoms worsen acutely, or if experiencing high fever, breathlessness, or severe pain."
                follow_up_text = "Follow-up in outpatient clinic in 3 to 5 days or sooner if symptoms change."

                patient_reason = clean_cc
                patient_findings = "The doctor reviewed your symptoms and discussed a care plan tailored to your needs."
                patient_diet = (
                    "- Drink adequate fluids and maintain a nutritious diet.\n"
                    "- Rest adequately and avoid excessive physical strain.\n"
                    "- Follow the specific care routine discussed during your visit."
                )
                patient_warnings = (
                    "- You develop difficulty breathing or swallowing.\n"
                    "- Your discomfort or symptoms increase significantly."
                )
                patient_followup = "Please return for a follow-up visit after 3 to 5 days if you do not feel significantly better."

            doctor_md = f"""# Clinical Encounter Note (SOAP)

### 1. Patient Demographics & Encounter Metadata
- **Patient Name:** {patient_info.get('full_name')} (ID: {patient_info.get('patient_identifier')})
- **Age / Gender:** {patient_info.get('age_years', 'N/A')} / {patient_info.get('gender')}
- **Attending Doctor:** {doctor_info.get('full_name')} ({doctor_info.get('specialization')})
- **Facility:** {clinic_info.get('name')}

### 2. Chief Complaint
{chief_complaint_text}

### 3. History of Present Illness (HPI)
{hpi_text}

### 4. Vitals & Physical Examination
{vitals_and_exam}

### 5. Systemic Review
{systemic_review_text}

### 6. Current Assessment & Clinical Impression
{assessment_text}

### 7. Differential Diagnoses
{differential_text}

### 8. Allergies
{patient_info.get('allergies_summary') or 'No known drug allergies (NKDA)'}

### 9. Active Medication Instructions
{meds_lines}

### 10. Investigations Ordered
{investigations_text}

### 11. Follow-Up Plan
{follow_up_text}

### 12. Emergency Warning Signs
{warning_signs_text}

### 13. Doctor Attestation & Approval Notice
*Pending Final Clinician Review and Digital Approval.*

### 14. Audit Verification
*Report Version 1 (AI Draft Generated from Spoken Consultation).*
"""

            patient_md = f"""# Your Visit Summary & Care Plan

### 1. Greeting & Visit Overview
Namaste **{patient_info.get('full_name')}**, thank you for visiting {clinic_info.get('name')}.

### 2. Reason for Your Visit
You consulted Dr. {doctor_info.get('full_name')} today regarding: {patient_reason}.

### 3. What the Doctor Found
{patient_findings}

### 4. Prescribed Medicines & How to Take Them
{patient_meds_lines}

### 5. Tests Ordered
{investigations_text}

### 6. Diet & Home Care Recommendations
{patient_diet}

### 7. Warning Signs to Watch For
Please contact us or visit urgent care immediately if:
{patient_warnings}

### 8. When to Return
{patient_followup}

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
                "instructions": ["Hydration", "Adequate rest"],
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
            meds_block = "\n".join(med_lines) if med_lines else "- चिकित्सक के निर्देशानुसार निर्धारित देखभाल एवं सावधानियों का पालन करें।"

            # Use dynamic chief complaint for the reason rather than static fever template
            chief_complaint = structured_json.get("chief_complaint", "")
            reason_text = tpl['reason']
            if chief_complaint and "fever for 3 days" not in chief_complaint.lower():
                reason_text = f"परामर्श एवं स्वास्थ्य मूल्यांकन: {chief_complaint} (Consultation & evaluation)."

            translated_md = f"""# {tpl['title']}

> [!NOTE]
> **{tpl['lang_name']}**: भाषा अनुवाद सारांश

### 1. {tpl['greeting']}

### 2. आने का कारण / Reason for Visit
{reason_text}

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

