from typing import Any, Protocol
from pydantic import BaseModel


class TranscriptSegmentResult(BaseModel):
    sequence_number: int
    speaker_label: str  # "DOCTOR", "PATIENT", "UNKNOWN"
    start_time_ms: int
    end_time_ms: int
    text: str
    confidence_score: float = 0.95


class TranscriptionResult(BaseModel):
    full_text: str
    language_detected: str
    segments: list[TranscriptSegmentResult]


class ExtractedClinicalFact(BaseModel):
    category: str  # "symptom", "diagnosis", "medication", "vital", "allergy", "investigation"
    fact_key: str
    fact_value: dict[str, Any]
    source_speaker: str = "PATIENT"
    provenance_type: str = "AI_EXTRACTED"  # "PATIENT_REPORTED", "CLINICIAN_OBSERVED", "AI_EXTRACTED", "HISTORICAL"
    certainty_status: str = "VERIFIED"    # "VERIFIED", "UNVERIFIED", "NOT_MENTIONED", "UNKNOWN", "PATIENT_DENIED", etc.
    validation_flags: list[str] = []
    evidence_quotation: str
    segment_indices: list[int] = []


class ExtractedMedicationInstruction(BaseModel):
    medication_name: str
    strength: str | None = None
    dosage: str | None = None
    route: str = "ORAL"
    frequency: str | None = None
    duration: str | None = None
    special_instructions: str | None = None
    uncertainty_flags: list[str] = []
    is_historical: bool = False
    evidence_quotation: str


class ClinicalExtractionResult(BaseModel):
    chief_complaint_summary: str
    facts: list[ExtractedClinicalFact]
    medications: list[ExtractedMedicationInstruction]
    unresolved_questions: list[str] = []
    longitudinal_comparison_json: dict[str, Any] = {}


class DualReportResult(BaseModel):
    doctor_clinical_markdown: str
    doctor_structured_json: dict[str, Any]
    patient_summary_markdown: str
    patient_structured_json: dict[str, Any]


class TranscriptionProvider(Protocol):
    async def transcribe(self, audio_bytes: bytes, language_code: str = "en-IN") -> TranscriptionResult:
        """Transcribes consultation audio into timestamped segments with speaker attribution."""
        ...


class ClinicalExtractionProvider(Protocol):
    async def extract_clinical_data(
        self,
        transcript_text: str,
        segments: list[TranscriptSegmentResult],
        previous_consultation_facts: list[dict[str, Any]] | None = None,
    ) -> ClinicalExtractionResult:
        """Extracts structured clinical facts, medication instructions, and evidence grounding."""
        ...


class ReportGenerationProvider(Protocol):
    async def generate_dual_reports(
        self,
        chief_complaint: str,
        facts: list[dict[str, Any]],
        medications: list[dict[str, Any]],
        patient_info: dict[str, Any],
        doctor_info: dict[str, Any],
        clinic_info: dict[str, Any],
    ) -> DualReportResult:
        """Generates both 14-section DOCTOR_CLINICAL note and 10-section PATIENT_SUMMARY."""
        ...


class TranslationProvider(Protocol):
    async def translate_patient_summary(
        self,
        summary_markdown: str,
        structured_json: dict[str, Any],
        target_language: str,
    ) -> tuple[str, dict[str, Any]]:
        """Translates patient summary narrative into vernacular Indian language while preserving clinical values."""
        ...


class TextToSpeechProvider(Protocol):
    async def synthesize_speech(
        self,
        text: str,
        language_code: str = "hi-IN",
        voice_id: str | None = None,
    ) -> bytes:
        """Synthesizes high-fidelity vernacular voice narration for patient summaries."""
        ...

