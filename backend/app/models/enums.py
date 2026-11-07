import enum
from typing import Any

def enum_val(v: Any) -> str:
    """Helper to safely extract the string value from either an Enum or a raw string."""
    if v is None:
        return ""
    return v.value if hasattr(v, "value") else str(v)

class UserRole(str, enum.Enum):
    PLATFORM_OWNER = "PLATFORM_OWNER"
    ORG_ADMIN = "ORG_ADMIN"
    RECEPTIONIST = "RECEPTIONIST"
    DOCTOR = "DOCTOR"

class OrgType(str, enum.Enum):
    POLYCLINIC = "POLYCLINIC"
    SINGLE_DOCTOR = "SINGLE_DOCTOR"
    HOSPITAL = "HOSPITAL"
    CLINIC = "CLINIC"

class OrgStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    PENDING = "PENDING"
    DEACTIVATED = "DEACTIVATED"

class SubscriptionStatus(str, enum.Enum):
    TRIAL = "TRIAL"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    SUSPENDED = "SUSPENDED"
    PENDING_PAYMENT = "PENDING_PAYMENT"

class BillingCycle(str, enum.Enum):
    MONTHLY = "MONTHLY"
    ANNUAL = "ANNUAL"

class PaymentMode(str, enum.Enum):
    DEVELOPMENT_MANUAL = "DEVELOPMENT_MANUAL"
    GATEWAY_VERIFIED = "GATEWAY_VERIFIED"

class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"

class AppointmentType(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    WALK_IN = "WALK_IN"

class AppointmentStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    CONFIRMED = "CONFIRMED"
    ARRIVED = "ARRIVED"
    WAITING = "WAITING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"

class ConsultationStatus(str, enum.Enum):
    SETUP = "SETUP"
    CONSENT_RECORDED = "CONSENT_RECORDED"
    RECORDING = "RECORDING"
    PROCESSING = "PROCESSING"
    REVIEW_READY = "REVIEW_READY"
    APPROVED = "APPROVED"
    COMPLETED = "COMPLETED"

class AudioUploadStatus(str, enum.Enum):
    PENDING = "PENDING"
    UPLOADED = "UPLOADED"
    VALIDATED = "VALIDATED"
    FAILED = "FAILED"

class TranscriptSourceType(str, enum.Enum):
    AI_PRISMA = "AI_PRISMA"
    MOCK_STT = "MOCK_STT"
    DOCTOR_EDITED = "DOCTOR_EDITED"

class SpeakerLabel(str, enum.Enum):
    DOCTOR = "DOCTOR"
    PATIENT = "PATIENT"
    UNKNOWN = "UNKNOWN"

class ProvenanceType(str, enum.Enum):
    PATIENT_REPORTED = "PATIENT_REPORTED"
    CLINICIAN_OBSERVED = "CLINICIAN_OBSERVED"
    AI_EXTRACTED = "AI_EXTRACTED"
    HISTORICAL = "HISTORICAL"

class CertaintyStatus(str, enum.Enum):
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    NOT_MENTIONED = "NOT_MENTIONED"
    UNKNOWN = "UNKNOWN"
    PATIENT_DENIED = "PATIENT_DENIED"
    CLINICIAN_OBSERVED_ABSENT = "CLINICIAN_OBSERVED_ABSENT"
    CONFLICTING = "CONFLICTING"

class DoctorReviewStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    EDITED = "EDITED"
    REJECTED = "REJECTED"

class ReportType(str, enum.Enum):
    DOCTOR_CLINICAL = "DOCTOR_CLINICAL"
    DOCTOR_NOTE = "DOCTOR_NOTE"
    PATIENT_SUMMARY = "PATIENT_SUMMARY"

class ReportStatus(str, enum.Enum):
    AI_GENERATED_DRAFT = "AI_GENERATED_DRAFT"
    DOCTOR_EDITED_DRAFT = "DOCTOR_EDITED_DRAFT"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    SUPERSEDED = "SUPERSEDED"

class PdfType(str, enum.Enum):
    DOCTOR_REPORT_PDF = "DOCTOR_REPORT_PDF"
    PATIENT_SUMMARY_PDF = "PATIENT_SUMMARY_PDF"

class JobType(str, enum.Enum):
    AUDIO_VALIDATION = "AUDIO_VALIDATION"
    TRANSCRIPTION = "TRANSCRIPTION"
    CLINICAL_EXTRACTION = "CLINICAL_EXTRACTION"
    REPORT_GENERATION = "REPORT_GENERATION"
    TRANSLATION = "TRANSLATION"
    PDF_GENERATION = "PDF_GENERATION"

class JobStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class DeliveryChannel(str, enum.Enum):
    MANUAL_WHATSAPP = "MANUAL_WHATSAPP"
    MANUAL_EMAIL = "MANUAL_EMAIL"
    DIRECT_DOWNLOAD = "DIRECT_DOWNLOAD"
