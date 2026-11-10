from app.core.config import settings
from app.integrations.ai.contracts import (
    ClinicalExtractionProvider,
    ReportGenerationProvider,
    TextToSpeechProvider,
    TranscriptionProvider,
    TranslationProvider,
)
from app.integrations.ai.gnani_providers import (
    GnaniClinicalExtractionProvider,
    GnaniReportGenerationProvider,
    GnaniTextToSpeechProvider,
    GnaniTranscriptionProvider,
)
from app.integrations.ai.mock_providers import (
    MockClinicalExtractionProvider,
    MockReportGenerationProvider,
    MockTextToSpeechProvider,
    MockTranscriptionProvider,
    MockTranslationProvider,
)


def is_gnani_active() -> bool:
    """Returns True if a live Gnani API key exists or AI_PROVIDER_MODE is gnani."""
    return settings.has_active_gnani_key or settings.ai_provider_mode == "gnani"


def get_transcription_provider() -> TranscriptionProvider:
    if is_gnani_active():
        return GnaniTranscriptionProvider()
    return MockTranscriptionProvider()


def get_clinical_extraction_provider() -> ClinicalExtractionProvider:
    # Clinical extraction is performed by ArogyaScribe's resilient clinical parser
    return MockClinicalExtractionProvider()


def get_report_generation_provider() -> ReportGenerationProvider:
    # Dual report generation is performed by ArogyaScribe's multi-lingual SOAP engine
    return MockReportGenerationProvider()


def get_translation_provider() -> TranslationProvider:
    return MockTranslationProvider()


def get_tts_provider() -> TextToSpeechProvider:
    if is_gnani_active():
        return GnaniTextToSpeechProvider()
    return MockTextToSpeechProvider()
