"""Gnani AI Live Provider Implementations

Contains the HTTP REST adapters for:
- Gnani Prisma v2.5 (STT): Multi-lingual speech recognition with Indian code-switching
- Gnani Evon v3.3 (LLM): Clinical fact extraction, evidence grounding, and dual report generation
- Gnani Timbre v2.5 (TTS): Vernacular audio narration for patient discharge summaries

Direct live REST calls to the Gnani / Vachana gateway with zero artificial caching
and zero circuit-breaker throttling.
"""
import logging
from typing import Any
import httpx

from app.core.config import settings
from app.integrations.ai.contracts import (
    ClinicalExtractionResult,
    DualReportResult,
    TranscriptSegmentResult,
    TranscriptionResult,
)
from app.integrations.ai.mock_providers import (
    MockClinicalExtractionProvider,
    MockReportGenerationProvider,
    MockTranscriptionProvider,
)

logger = logging.getLogger("arogyascribe.ai.gnani")


def _is_valid_key(api_key: str | None) -> bool:
    """Returns True if api_key is non-empty and not a placeholder."""
    if not api_key:
        return False
    clean = api_key.strip()
    return bool(clean and clean != "YOUR_GNANI_API_KEY_HERE" and not clean.startswith("YOUR_"))


def _get_auth_headers(api_key: str) -> dict[str, str]:
    """Generates standard authentication headers required by the Gnani/Vachana gateway."""
    clean = api_key.strip()
    return {
        "x-api-key-id": clean,
        "x-api-key": clean,
        "X-API-Key": clean,
        "Authorization": f"Bearer {clean}",
        "Accept": "application/json",
    }


class GnaniTranscriptionProvider:
    """Gnani Prisma v2.5 STT REST Adapter."""

    def __init__(self) -> None:
        self.api_key = settings.gnani_api_key
        self.base_url = (getattr(settings, "gnani_base_url", None) or "https://api.vachana.ai").rstrip("/")
        self.endpoint = f"{self.base_url}/v1/stt/transcribe"
        self._fallback = MockTranscriptionProvider()

    async def transcribe(self, audio_bytes: bytes, language_code: str = "en-IN") -> TranscriptionResult:
        if not _is_valid_key(self.api_key):
            logger.warning(
                "Gnani STT: GNANI_API_KEY is not configured in environment (current value: %r). "
                "Set GNANI_API_KEY in Render to enable live speech-to-text API calls.",
                self.api_key,
            )
            return await self._fallback.transcribe(audio_bytes, language_code)

        headers = _get_auth_headers(self.api_key)
        files = {"audio_file": ("encounter.wav", audio_bytes, "audio/wav")}
        data = {"language": language_code, "model": getattr(settings, "gnani_stt_model", "prisma-v2.5")}

        logger.info(
            ">>> DISPATCHING LIVE STT CALL TO: %s (size: %d bytes, lang: %s, key: %s...)",
            self.endpoint,
            len(audio_bytes),
            language_code,
            self.api_key[:6] if len(self.api_key) > 6 else "***",
        )

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(self.endpoint, headers=headers, files=files, data=data)
                logger.info("Gnani STT response status: HTTP %d", response.status_code)
                if response.status_code >= 400:
                    logger.error("Gnani STT API returned HTTP %d: %s", response.status_code, response.text)
                    response.raise_for_status()
                res_json = response.json()

            segments = [
                TranscriptSegmentResult(
                    sequence_number=i + 1,
                    speaker_label=seg.get("speaker", "UNKNOWN"),
                    start_time_ms=seg.get("start_time", 0),
                    end_time_ms=seg.get("end_time", 0),
                    text=seg.get("transcript", ""),
                    confidence_score=seg.get("confidence", 0.95),
                )
                for i, seg in enumerate(res_json.get("segments", []))
            ]

            return TranscriptionResult(
                full_text=res_json.get("full_transcript", ""),
                language_detected=res_json.get("language_detected", language_code),
                segments=segments,
            )
        except Exception as exc:
            logger.error("Gnani STT live request failed (%s). Utilizing local fallback.", exc)
            return await self._fallback.transcribe(audio_bytes, language_code)


class GnaniClinicalExtractionProvider:
    """Gnani Evon v3.3 Clinical Information Extraction Adapter."""

    def __init__(self) -> None:
        self.api_key = settings.gnani_api_key
        self.base_url = (getattr(settings, "gnani_base_url", None) or "https://api.vachana.ai").rstrip("/")
        self.endpoint = f"{self.base_url}/v1/clinical/extract"
        self._fallback = MockClinicalExtractionProvider()

    async def extract_clinical_data(
        self,
        transcript_text: str,
        segments: list[TranscriptSegmentResult],
        previous_consultation_facts: list[dict[str, Any]] | None = None,
        is_sample_demo: bool = False,
    ) -> ClinicalExtractionResult:
        if not _is_valid_key(self.api_key):
            logger.warning(
                "Gnani Clinical Extraction: GNANI_API_KEY is not configured in environment (current value: %r). "
                "Set GNANI_API_KEY in Render to enable live clinical extraction API calls.",
                self.api_key,
            )
            return await self._fallback.extract_clinical_data(
                transcript_text, segments, previous_consultation_facts, is_sample_demo=is_sample_demo
            )

        payload = {
            "model": getattr(settings, "gnani_llm_model", "evon-v3.3"),
            "transcript": transcript_text,
            "segments": [s.model_dump() for s in segments],
            "previous_facts": previous_consultation_facts or [],
        }

        logger.info(
            ">>> DISPATCHING LIVE CLINICAL EXTRACTION CALL TO: %s (transcript length: %d chars, key: %s...)",
            self.endpoint,
            len(transcript_text),
            self.api_key[:6] if len(self.api_key) > 6 else "***",
        )

        try:
            headers = _get_auth_headers(self.api_key)
            headers["Content-Type"] = "application/json"
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(
                    self.endpoint,
                    headers=headers,
                    json=payload,
                )
                logger.info("Gnani Clinical response status: HTTP %d", response.status_code)
                if response.status_code >= 400:
                    logger.error("Gnani Clinical API returned HTTP %d: %s", response.status_code, response.text)
                    response.raise_for_status()
                res = response.json()

            return ClinicalExtractionResult.model_validate(res)
        except Exception as exc:
            logger.error("Gnani Clinical Extraction live request failed (%s). Utilizing local fallback.", exc)
            return await self._fallback.extract_clinical_data(
                transcript_text, segments, previous_consultation_facts, is_sample_demo=is_sample_demo
            )


class GnaniReportGenerationProvider:
    """Gnani Evon v3.3 Report Generation Provider."""

    def __init__(self) -> None:
        self.api_key = settings.gnani_api_key
        self.base_url = (getattr(settings, "gnani_base_url", None) or "https://api.vachana.ai").rstrip("/")
        self.endpoint = f"{self.base_url}/v1/reports/generate"
        self._fallback = MockReportGenerationProvider()

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
        if not _is_valid_key(self.api_key):
            logger.warning(
                "Gnani Reports: GNANI_API_KEY is not configured in environment (current value: %r). "
                "Set GNANI_API_KEY in Render to enable live report generation API calls.",
                self.api_key,
            )
            return await self._fallback.generate_dual_reports(
                chief_complaint, facts, medications, patient_info, doctor_info, clinic_info, is_sample_demo=is_sample_demo
            )

        payload = {
            "model": getattr(settings, "gnani_llm_model", "evon-v3.3"),
            "chief_complaint": chief_complaint,
            "facts": facts,
            "medications": medications,
            "patient_info": patient_info,
            "doctor_info": doctor_info,
            "clinic_info": clinic_info,
        }

        logger.info(
            ">>> DISPATCHING LIVE REPORT GENERATION CALL TO: %s (facts: %d, meds: %d, key: %s...)",
            self.endpoint,
            len(facts),
            len(medications),
            self.api_key[:6] if len(self.api_key) > 6 else "***",
        )

        try:
            headers = _get_auth_headers(self.api_key)
            headers["Content-Type"] = "application/json"
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(self.endpoint, headers=headers, json=payload)
                logger.info("Gnani Reports response status: HTTP %d", response.status_code)
                if response.status_code >= 400:
                    logger.error("Gnani Reports API returned HTTP %d: %s", response.status_code, response.text)
                    response.raise_for_status()
                res = response.json()

            return DualReportResult.model_validate(res)
        except Exception as exc:
            logger.error("Gnani Reports live request failed (%s). Utilizing local fallback.", exc)
            return await self._fallback.generate_dual_reports(
                chief_complaint, facts, medications, patient_info, doctor_info, clinic_info, is_sample_demo=is_sample_demo
            )


class GnaniTextToSpeechProvider:
    """Gnani Timbre v2.5 Vernacular TTS Adapter."""

    def __init__(self) -> None:
        self.api_key = settings.gnani_api_key
        self.base_url = (getattr(settings, "gnani_base_url", None) or "https://api.vachana.ai").rstrip("/")
        self.endpoint = f"{self.base_url}/v1/tts/synthesize"

    async def synthesize_speech(
        self,
        text: str,
        language_code: str = "hi-IN",
        voice_id: str | None = None,
    ) -> bytes:
        if not _is_valid_key(self.api_key):
            return b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"

        payload = {
            "text": text,
            "language": language_code,
            "voice": voice_id or getattr(settings, "gnani_tts_voice", "Nalini"),
            "audio_format": "wav",
        }

        logger.info(">>> DISPATCHING LIVE TTS CALL TO: %s (lang: %s, text len: %d)", self.endpoint, language_code, len(text))
        try:
            headers = _get_auth_headers(self.api_key)
            headers["Content-Type"] = "application/json"
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.endpoint,
                    headers=headers,
                    json=payload,
                )
                if response.status_code >= 400:
                    logger.error("Gnani TTS API returned HTTP %d: %s", response.status_code, response.text)
                    response.raise_for_status()
                return response.content
        except Exception as exc:
            logger.error("Gnani TTS live request failed (%s)", exc)
            return b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
