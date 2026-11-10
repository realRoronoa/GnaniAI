"""Gnani AI Official Live Provider Implementations

Implements the official Gnani AI / Vachana REST APIs based on https://docs.gnani.ai:
- Gnani Prisma v3.0 / v2.5 (STT): POST https://api.vachana.ai/stt/v3
  Headers: X-API-Key-ID: <key>
  Multipart: audio_file, model, language_code, format
- Gnani Evon v3.3 (Clinical Reasoning / LLM): POST https://api.vachana.ai/v1/clinical/extract
- Gnani Timbre v2.5 (TTS): POST https://api.vachana.ai/api/v1/tts/inference
  Headers: X-API-Key-ID: <key>
  JSON: text, voice, model, language, speed, audio_config

Audio conversion to 16kHz 16-bit mono WAV is applied to browser WebM/Opus audio before STT transmission.
"""
import logging
import os
import subprocess
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
)

logger = logging.getLogger("arogyascribe.ai.gnani")


def convert_to_wav_16k_mono(audio_bytes: bytes) -> bytes:
    """Converts browser-recorded audio (WebM/Opus) to 16kHz 16-bit mono WAV using ffmpeg.
    
    If ffmpeg is unavailable or conversion fails, safely returns the original audio bytes.
    """
    if not audio_bytes or len(audio_bytes) < 44:
        return audio_bytes

    try:
        cmd = [
            "ffmpeg", "-y",
            "-i", "pipe:0",
            "-ar", "16000",
            "-ac", "1",
            "-acodec", "pcm_s16le",
            "-f", "wav",
            "pipe:1"
        ]
        proc = subprocess.run(cmd, input=audio_bytes, capture_output=True, timeout=15)
        if proc.returncode == 0 and len(proc.stdout) > 44:
            logger.info("ffmpeg conversion successful: %d bytes -> %d bytes (16kHz mono WAV)", len(audio_bytes), len(proc.stdout))
            return proc.stdout
        else:
            logger.warning("ffmpeg conversion returned exit code %d (stderr: %s)", proc.returncode, proc.stderr[:200] if proc.stderr else b"")
    except Exception as exc:
        logger.debug("ffmpeg conversion unavailable or failed (%s). Sending input audio bytes directly.", exc)

    return audio_bytes


def _is_valid_key(api_key: str | None) -> bool:
    """Returns True if api_key is non-empty and not a placeholder."""
    if not api_key:
        return False
    clean = api_key.strip()
    return bool(clean and clean != "YOUR_GNANI_API_KEY_HERE" and not clean.startswith("YOUR_"))


def _get_auth_headers(api_key: str) -> dict[str, str]:
    """Generates standard authentication headers as specified in https://docs.gnani.ai/api/introduction/introduction."""
    clean = api_key.strip()
    return {
        "X-API-Key-ID": clean,
        "x-api-key-id": clean,
        "X-API-Key": clean,
        "x-api-key": clean,
        "Authorization": f"Bearer {clean}",
        "Accept": "application/json",
    }


class GnaniTranscriptionProvider:
    """Gnani Prisma v3.0 / v2.5 STT REST Adapter (POST https://api.vachana.ai/stt/v3)."""

    def __init__(self) -> None:
        self.api_key = settings.get_effective_gnani_key()
        self.base_url = (getattr(settings, "gnani_base_url", None) or "https://api.vachana.ai").rstrip("/")
        # Official endpoint path from https://docs.gnani.ai/api/STT/speech-to-text.md
        self.endpoint = f"{self.base_url}/stt/v3"

    async def transcribe(self, audio_bytes: bytes, language_code: str = "en-IN") -> TranscriptionResult:
        if not _is_valid_key(self.api_key):
            logger.warning("Gnani STT: No valid API key configured. Returning empty STT result.")
            return TranscriptionResult(
                full_text="",
                language_detected=language_code or "en-IN",
                segments=[],
                provider_metadata={"live_api_success": False, "reason": "NO_API_KEY"},
            )

        # Ensure audio is 16kHz mono WAV for high-accuracy recognition and billing
        wav_bytes = convert_to_wav_16k_mono(audio_bytes)

        headers = _get_auth_headers(self.api_key)
        files = {"audio_file": ("encounter.wav", wav_bytes, "audio/wav")}

        # Format language parameter: Prisma v3.0 supports indic-auto or comma-separated hints like hi-IN,en-IN
        gnani_lang = "indic-auto" if (not language_code or language_code in ["en-IN", "en"]) else f"{language_code},en-IN"
        data = {
            "model": getattr(settings, "gnani_stt_model", "prisma-v3.0"),
            "language_code": gnani_lang,
            "format": "transcribe",
        }

        masked_key = self.api_key[:6] + "..." + self.api_key[-4:] if len(self.api_key) > 10 else "***"
        logger.info(
            ">>> GNANI STT REQUEST: URL=%s | Key=%s | Model=%s | Lang=%s | AudioSize=%d bytes",
            self.endpoint,
            masked_key,
            data["model"],
            data["language_code"],
            len(wav_bytes),
        )

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(self.endpoint, headers=headers, files=files, data=data)
                logger.info("<<< GNANI STT RESPONSE: HTTP %d | Body preview: %s", response.status_code, response.text[:300])

                if response.status_code >= 400:
                    logger.error("Gnani STT API returned error HTTP %d: %s", response.status_code, response.text)
                    return TranscriptionResult(
                        full_text="",
                        language_detected=language_code,
                        segments=[],
                        provider_metadata={"live_api_success": False, "http_status": response.status_code, "error": response.text[:200]},
                    )

                res_json = response.json()

            # Parse official response schema:
            # {"success": true, "transcript": "...", "model": "prisma-v3.0", "detected_language_code": "hi-IN", ...}
            transcript_text = (res_json.get("transcript") or res_json.get("full_transcript") or "").strip()
            detected_lang = res_json.get("detected_language_code") or res_json.get("language_detected") or language_code

            segments = []
            if "segments" in res_json and isinstance(res_json["segments"], list) and res_json["segments"]:
                segments = [
                    TranscriptSegmentResult(
                        sequence_number=i + 1,
                        speaker_label=seg.get("speaker", "UNKNOWN"),
                        start_time_ms=seg.get("start_time", 0),
                        end_time_ms=seg.get("end_time", 0),
                        text=seg.get("transcript", ""),
                        confidence_score=seg.get("confidence", 0.95),
                    )
                    for i, seg in enumerate(res_json["segments"])
                ]

            return TranscriptionResult(
                full_text=transcript_text,
                language_detected=detected_lang,
                segments=segments,
                provider_metadata={"live_api_success": bool(transcript_text), "raw_response": res_json},
            )
        except Exception as exc:
            logger.error("Gnani STT live request exception: %s", exc)
            return TranscriptionResult(
                full_text="",
                language_detected=language_code,
                segments=[],
                provider_metadata={"live_api_success": False, "error": str(exc)},
            )


class GnaniClinicalExtractionProvider:
    """Gnani Evon v3.3 Clinical Information Extraction Adapter."""

    def __init__(self) -> None:
        self.api_key = settings.get_effective_gnani_key()
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
            logger.warning("Gnani Clinical: No valid API key configured. Utilizing local clinical extraction engine.")
            return await self._fallback.extract_clinical_data(
                transcript_text, segments, previous_consultation_facts, is_sample_demo=is_sample_demo
            )

        payload = {
            "model": getattr(settings, "gnani_llm_model", "evon-v3.3"),
            "transcript": transcript_text,
            "segments": [s.model_dump() for s in segments],
            "previous_facts": previous_consultation_facts or [],
        }

        masked_key = self.api_key[:6] + "..." + self.api_key[-4:] if len(self.api_key) > 10 else "***"
        logger.info(
            ">>> GNANI CLINICAL REQUEST: URL=%s | Key=%s | TranscriptLen=%d chars",
            self.endpoint,
            masked_key,
            len(transcript_text),
        )

        try:
            headers = _get_auth_headers(self.api_key)
            headers["Content-Type"] = "application/json"
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(self.endpoint, headers=headers, json=payload)
                logger.info("<<< GNANI CLINICAL RESPONSE: HTTP %d | Body preview: %s", response.status_code, response.text[:300])

                if response.status_code >= 400:
                    logger.error("Gnani Clinical API returned HTTP %d: %s", response.status_code, response.text)
                    response.raise_for_status()
                res = response.json()

            return ClinicalExtractionResult.model_validate(res)
        except Exception as exc:
            logger.warning("Gnani Clinical live request exception (%s). Utilizing local fallback.", exc)
            return await self._fallback.extract_clinical_data(
                transcript_text, segments, previous_consultation_facts, is_sample_demo=is_sample_demo
            )


class GnaniReportGenerationProvider:
    """Gnani Evon v3.3 Report Generation Provider."""

    def __init__(self) -> None:
        self.api_key = settings.get_effective_gnani_key()
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
            logger.warning("Gnani Reports: No valid API key configured. Utilizing local report engine.")
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

        masked_key = self.api_key[:6] + "..." + self.api_key[-4:] if len(self.api_key) > 10 else "***"
        logger.info(
            ">>> GNANI REPORTS REQUEST: URL=%s | Key=%s | Facts=%d | Meds=%d",
            self.endpoint,
            masked_key,
            len(facts),
            len(medications),
        )

        try:
            headers = _get_auth_headers(self.api_key)
            headers["Content-Type"] = "application/json"
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(self.endpoint, headers=headers, json=payload)
                logger.info("<<< GNANI REPORTS RESPONSE: HTTP %d | Body preview: %s", response.status_code, response.text[:300])

                if response.status_code >= 400:
                    logger.error("Gnani Reports API returned HTTP %d: %s", response.status_code, response.text)
                    response.raise_for_status()
                res = response.json()

            return DualReportResult.model_validate(res)
        except Exception as exc:
            logger.warning("Gnani Reports live request exception (%s). Utilizing local fallback.", exc)
            return await self._fallback.generate_dual_reports(
                chief_complaint, facts, medications, patient_info, doctor_info, clinic_info, is_sample_demo=is_sample_demo
            )


class GnaniTextToSpeechProvider:
    """Gnani Timbre v2.5 Vernacular TTS Adapter (POST https://api.vachana.ai/api/v1/tts/inference)."""

    def __init__(self) -> None:
        self.api_key = settings.get_effective_gnani_key()
        self.base_url = (getattr(settings, "gnani_base_url", None) or "https://api.vachana.ai").rstrip("/")
        # Official endpoint path from https://docs.gnani.ai/api/TTS/tts-inference.md
        self.endpoint = f"{self.base_url}/api/v1/tts/inference"

    async def synthesize_speech(
        self,
        text: str,
        language_code: str = "hi-IN",
        voice_id: str | None = None,
    ) -> bytes:
        if not _is_valid_key(self.api_key):
            return b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"

        # Official request schema from https://docs.gnani.ai/api/TTS/tts-inference.md
        payload = {
            "text": text,
            "voice": voice_id or getattr(settings, "gnani_tts_voice", "Nalini"),
            "model": getattr(settings, "gnani_tts_model", "timbre-v2.5"),
            "language": language_code,
            "speed": 1.0,
            "audio_config": {
                "sample_rate": 48000,
                "num_channels": 1,
                "sample_width": 2,
                "encoding": "linear_pcm",
                "container": "wav",
            },
        }

        logger.info(">>> GNANI TTS REQUEST: URL=%s | Lang=%s | Voice=%s | TextLen=%d", self.endpoint, language_code, payload["voice"], len(text))
        try:
            headers = _get_auth_headers(self.api_key)
            headers["Content-Type"] = "application/json"
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.endpoint, headers=headers, json=payload)
                if response.status_code >= 400:
                    logger.error("Gnani TTS API returned HTTP %d: %s", response.status_code, response.text)
                    response.raise_for_status()
                return response.content
        except Exception as exc:
            logger.error("Gnani TTS live request failed (%s)", exc)
            return b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
