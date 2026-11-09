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


def get_transcription_provider() -> TranscriptionProvider:
    if settings.ai_provider_mode == "gnani":
        return GnaniTranscriptionProvider()
    return MockTranscriptionProvider()


def get_clinical_extraction_provider() -> ClinicalExtractionProvider:
    if settings.ai_provider_mode == "gnani":
        return GnaniClinicalExtractionProvider()
    return MockClinicalExtractionProvider()


def get_report_generation_provider() -> ReportGenerationProvider:
    if settings.ai_provider_mode == "gnani":
        return GnaniReportGenerationProvider()
    return MockReportGenerationProvider()


def get_translation_provider() -> TranslationProvider:
    return MockTranslationProvider()


def get_tts_provider() -> TextToSpeechProvider:
    if settings.ai_provider_mode == "gnani":
        return GnaniTextToSpeechProvider()
    return MockTextToSpeechProvider()
