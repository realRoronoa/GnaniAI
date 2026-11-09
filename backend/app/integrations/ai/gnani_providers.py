"""Gnani AI Provider Implementations with SHA-256 Disk Caching & Credit Guardrail

Contains the HTTP adapters for:
- Gnani Prisma v2.5 (STT): Multi-lingual speech recognition with Indian code-switching
- Gnani Evon v3.3 (LLM): Clinical fact extraction, evidence grounding, and dual report generation
- Gnani Timbre v2.5 (TTS): Vernacular audio narration for patient discharge summaries

Protected by a local SHA-256 persistent disk cache and a 6-call hard circuit breaker
to strictly conserve the hackathon's 5,000 credits.
"""
import hashlib
import json
import logging
import os
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
    return {
        "x-api-key-id": api_key,
        "x-api-key": api_key,
        "X-API-Key": api_key,
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }


def _ensure_cache_dir() -> str:
    cache_dir = getattr(settings, "gnani_cache_dir", "./storage/gnani_cache")
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def _check_and_increment_counter() -> bool:
    """Returns True if within allowed budget (< gnani_max_live_calls), False if capped."""
    cache_dir = _ensure_cache_dir()
    counter_path = os.path.join(cache_dir, "usage_counter.json")
    max_allowed = getattr(settings, "gnani_max_live_calls", 6)

    data = {"live_calls_count": 0, "max_allowed_calls": max_allowed}
    if os.path.exists(counter_path):
        try:
            with open(counter_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass

    current_count = data.get("live_calls_count", 0)
    if current_count >= max_allowed:
        return False

    data["live_calls_count"] = current_count + 1
    try:
        with open(counter_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass
    return True


def _read_disk_cache(cache_key: str) -> dict | None:
    cache_dir = _ensure_cache_dir()
    file_path = os.path.join(cache_dir, f"{cache_key}.json")
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def _write_disk_cache(cache_key: str, data: dict) -> None:
    cache_dir = _ensure_cache_dir()
    file_path = os.path.join(cache_dir, f"{cache_key}.json")
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


class GnaniTranscriptionProvider:
    """Gnani Prisma v2.5 STT REST Adapter with SHA-256 disk cache & credit protection."""

    def __init__(self) -> None:
        self.api_key = settings.gnani_api_key
        self.base_url = (getattr(settings, "gnani_base_url", None) or "https://api.vachana.ai").rstrip("/")
        self.endpoint = f"{self.base_url}/v1/stt/transcribe"
        self._fallback = MockTranscriptionProvider()

    async def transcribe(self, audio_bytes: bytes, language_code: str = "en-IN") -> TranscriptionResult:
        cache_key = hashlib.sha256(audio_bytes + language_code.encode("utf-8")).hexdigest()

        # Check local disk cache
        cached = _read_disk_cache(cache_key)
        if cached:
            logger.info("Gnani STT: Cache hit for key %s", cache_key[:12])
            return TranscriptionResult.model_validate(cached)

        # Guardrail: check valid API key
        if not _is_valid_key(self.api_key):
            logger.info("Gnani STT: No valid GNANI_API_KEY provided in backend/.env. Using local fallback engine.")
            result = await self._fallback.transcribe(audio_bytes, language_code)
            _write_disk_cache(cache_key, result.model_dump())
            return result

        # Guardrail: check circuit breaker budget limit
        if not _check_and_increment_counter():
            logger.warning("Gnani STT: Live call budget limit reached (%d max calls). Using local fallback.", settings.gnani_max_live_calls)
            result = await self._fallback.transcribe(audio_bytes, language_code)
            _write_disk_cache(cache_key, result.model_dump())
            return result

        headers = _get_auth_headers(self.api_key)
        files = {"audio_file": ("encounter.wav", audio_bytes, "audio/wav")}
        data = {"language": language_code, "model": getattr(settings, "gnani_stt_model", "prisma-v2.5")}

        try:
            logger.info("Gnani STT: Dispatching live transcription request to %s (audio size: %d bytes)", self.endpoint, len(audio_bytes))
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(self.endpoint, headers=headers, files=files, data=data)
                if response.status_code >= 400:
                    logger.error("Gnani STT: API returned error HTTP %d: %s", response.status_code, response.text)
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

            result = TranscriptionResult(
                full_text=res_json.get("full_transcript", ""),
                language_detected=res_json.get("language_detected", language_code),
                segments=segments,
            )
            _write_disk_cache(cache_key, result.model_dump())
            return result
        except Exception as exc:
            logger.warning("Gnani STT: Live API call failed (%s). Falling back to local transcript generation.", exc)
            fallback_res = await self._fallback.transcribe(audio_bytes, language_code)
            _write_disk_cache(cache_key, fallback_res.model_dump())
            return fallback_res


class GnaniClinicalExtractionProvider:
    """Gnani Evon v3.3 Clinical Information Extraction Adapter with disk cache & guardrail."""

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
        cache_key = hashlib.sha256((transcript_text + str(is_sample_demo)).encode("utf-8")).hexdigest()

        cached = _read_disk_cache(cache_key)
        if cached:
            logger.info("Gnani Clinical Extraction: Cache hit for key %s", cache_key[:12])
            return ClinicalExtractionResult.model_validate(cached)

        if not _is_valid_key(self.api_key):
            logger.info("Gnani Clinical Extraction: No valid GNANI_API_KEY configured. Using local extraction engine.")
            fallback_res = await self._fallback.extract_clinical_data(
                transcript_text, segments, previous_consultation_facts, is_sample_demo=is_sample_demo
            )
            _write_disk_cache(cache_key, fallback_res.model_dump())
            return fallback_res

        if not _check_and_increment_counter():
            logger.warning("Gnani Clinical Extraction: Live call budget limit reached. Using local fallback.")
            fallback_res = await self._fallback.extract_clinical_data(
                transcript_text, segments, previous_consultation_facts, is_sample_demo=is_sample_demo
            )
            _write_disk_cache(cache_key, fallback_res.model_dump())
            return fallback_res

        payload = {
            "model": getattr(settings, "gnani_llm_model", "evon-v3.3"),
            "transcript": transcript_text,
            "segments": [s.model_dump() for s in segments],
            "previous_facts": previous_consultation_facts or [],
        }

        try:
            logger.info("Gnani Clinical Extraction: Dispatching live extraction request to %s", self.endpoint)
            headers = _get_auth_headers(self.api_key)
            headers["Content-Type"] = "application/json"
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(
                    self.endpoint,
                    headers=headers,
                    json=payload,
                )
                if response.status_code >= 400:
                    logger.error("Gnani Clinical Extraction: API returned error HTTP %d: %s", response.status_code, response.text)
                    response.raise_for_status()
                res = response.json()

            result = ClinicalExtractionResult.model_validate(res)
            _write_disk_cache(cache_key, result.model_dump())
            return result
        except Exception as exc:
            logger.warning("Gnani Clinical Extraction: Live API call failed (%s). Falling back to local extractor.", exc)
            fallback_res = await self._fallback.extract_clinical_data(
                transcript_text, segments, previous_consultation_facts, is_sample_demo=is_sample_demo
            )
            _write_disk_cache(cache_key, fallback_res.model_dump())
            return fallback_res


class GnaniReportGenerationProvider:
    """Gnani Evon v3.3 Report Generation Provider with disk cache & credit guardrail."""

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
        cache_key = hashlib.sha256(
            (chief_complaint + json.dumps(facts, sort_keys=True) + json.dumps(medications, sort_keys=True) + str(is_sample_demo)).encode("utf-8")
        ).hexdigest()

        cached = _read_disk_cache(cache_key)
        if cached:
            logger.info("Gnani Reports: Cache hit for key %s", cache_key[:12])
            return DualReportResult.model_validate(cached)

        if not _is_valid_key(self.api_key):
            logger.info("Gnani Reports: No valid GNANI_API_KEY configured. Using local report engine.")
            fallback_res = await self._fallback.generate_dual_reports(
                chief_complaint, facts, medications, patient_info, doctor_info, clinic_info, is_sample_demo=is_sample_demo
            )
            _write_disk_cache(cache_key, fallback_res.model_dump())
            return fallback_res

        if not _check_and_increment_counter():
            logger.warning("Gnani Reports: Live call budget reached. Using local report generator.")
            fallback_res = await self._fallback.generate_dual_reports(
                chief_complaint, facts, medications, patient_info, doctor_info, clinic_info, is_sample_demo=is_sample_demo
            )
            _write_disk_cache(cache_key, fallback_res.model_dump())
            return fallback_res

        payload = {
            "model": getattr(settings, "gnani_llm_model", "evon-v3.3"),
            "chief_complaint": chief_complaint,
            "facts": facts,
            "medications": medications,
            "patient_info": patient_info,
            "doctor_info": doctor_info,
            "clinic_info": clinic_info,
        }

        try:
            logger.info("Gnani Reports: Calling live report generation endpoint: %s", self.endpoint)
            headers = _get_auth_headers(self.api_key)
            headers["Content-Type"] = "application/json"
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(self.endpoint, headers=headers, json=payload)
                if response.status_code >= 400:
                    logger.error("Gnani Reports: API returned error HTTP %d: %s", response.status_code, response.text)
                    response.raise_for_status()
                res = response.json()

            result = DualReportResult.model_validate(res)
            _write_disk_cache(cache_key, result.model_dump())
            return result
        except Exception as exc:
            logger.warning("Gnani Reports: Live API call failed (%s). Using local report generator.", exc)
            fallback_res = await self._fallback.generate_dual_reports(
                chief_complaint, facts, medications, patient_info, doctor_info, clinic_info, is_sample_demo=is_sample_demo
            )
            _write_disk_cache(cache_key, fallback_res.model_dump())
            return fallback_res


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
                    logger.error("Gnani TTS: API returned error HTTP %d: %s", response.status_code, response.text)
                    response.raise_for_status()
                return response.content
        except Exception as exc:
            logger.warning("Gnani TTS: Live synthesis failed (%s)", exc)
            return b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
