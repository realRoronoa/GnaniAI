export type UserRole = 'PLATFORM_OWNER' | 'ORG_ADMIN' | 'RECEPTIONIST' | 'DOCTOR';

export interface User {
  id: string;
  email: string;
  role: UserRole;
  organization_id?: string | null;
  full_name?: string | null;
  is_active: boolean;
  avatar_url?: string | null;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type?: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface Organization {
  id: string;
  name: string;
  org_type: string;
  status: 'ACTIVE' | 'SUSPENDED' | 'PENDING';
  address?: string | null;
  contact_email: string;
  contact_phone?: string | null;
  registration_number?: string | null;
  created_at: string;
  doctor_count?: number;
  active_subscription?: string | null;
}

export interface SubscriptionPlan {
  id: string;
  name: string;
  code: string;
  description?: string | null;
  monthly_price: number;
  annual_price?: number;
  max_doctors: number;
  max_receptionists: number;
  max_branches: number;
  monthly_consultation_limit?: number;
  max_consultations_per_month?: number;
  audio_storage_mb_limit?: number;
  report_generation_limit?: number;
  included_features_json?: string[];
  features_json?: Record<string, any>;
  duration_days?: number;
  trial_days?: number;
  is_active: boolean;
}

export interface Branch {
  id: string;
  organization_id: string;
  name: string;
  branch_code: string;
  city?: string | null;
  state?: string | null;
  address?: string | null;
  phone?: string | null;
  is_active: boolean;
}

export interface DoctorStaff {
  id: string;
  user_id: string;
  full_name: string;
  email: string;
  specialization?: string | null;
  registration_number?: string | null;
  assigned_branches?: string[];
  is_active: boolean;
}

export interface ReceptionistStaff {
  id: string;
  user_id: string;
  full_name: string;
  email: string;
  assigned_branches?: string[];
  is_active: boolean;
}

export interface DoctorSchedule {
  id: string;
  doctor_user_id: string;
  doctor_name?: string;
  location_id?: string;
  branch_name?: string;
  day_of_week: number;
  start_time: string;
  end_time: string;
  slot_duration_minutes: number;
  is_active: boolean;
}

export interface AuditEvent {
  id: string;
  actor_user_id?: string | null;
  actor_role?: string | null;
  action: string;
  resource_type: string;
  resource_id?: string | null;
  ip_address?: string | null;
  created_at: string;
  details?: Record<string, any>;
}

export interface PlatformMetrics {
  total_organizations: number;
  active_subscriptions: number;
  total_doctors: number;
  total_consultations_month: number;
  monthly_recurring_revenue: number;
}

export interface OrgEntitlements {
  max_doctors: number;
  used_doctors: number;
  max_receptionists: number;
  used_receptionists: number;
  max_branches: number;
  used_branches: number;
  max_consultations: number;
  used_consultations: number;
  plan_name: string;
  status: string;
}

// ==========================================
// Phase B Clinical & Reception Types
// ==========================================

export type AppointmentStatus =
  | 'SCHEDULED'
  | 'CONFIRMED'
  | 'ARRIVED'
  | 'WAITING'
  | 'IN_PROGRESS'
  | 'COMPLETED'
  | 'CANCELLED'
  | 'NO_SHOW';

export type AppointmentType = 'SCHEDULED' | 'WALK_IN';

export interface Patient {
  id: string;
  organization_id: string;
  patient_identifier: string; // e.g., ARC-2026-0001
  full_name: string;
  date_of_birth?: string | null;
  age_years?: number | null;
  gender: string;
  mobile_number: string;
  email?: string | null;
  preferred_language: string; // en, hi, kn
  allergies_summary?: string | null;
  allergy_verification_status: 'UNVERIFIED' | 'VERIFIED';
  administrative_notes?: string | null;
  created_at: string;
  last_visit_at?: string | null;
  total_visits_count?: number;
}

export interface DuplicatePatientMatch {
  id: string;
  patient_identifier: string;
  full_name: string;
  mobile_number: string;
  age_years?: number | null;
  gender: string;
  match_reason?: string;
  match_reasons?: string[];
}

export interface Appointment {
  id: string;
  organization_id: string;
  location_id?: string | null;
  patient_id: string;
  doctor_user_id?: string | null;
  doctor_name?: string | null;
  created_by_user_id: string;
  appointment_date: string;
  scheduled_time?: string | null;
  queue_position: number;
  appointment_type: AppointmentType;
  status: AppointmentStatus;
  reason_for_visit?: string | null;
  administrative_notes?: string | null;
  arrived_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  patient?: {
    id: string;
    patient_identifier: string;
    full_name: string;
    mobile_number: string;
    gender: string;
    age_years?: number | null;
    preferred_language: string;
    allergies_summary?: string | null;
    has_previous_visits?: boolean;
  } | null;
}

export interface ReceptionOverview {
  target_date: string;
  total_appointments: number;
  waiting_count: number;
  arrived_count: number;
  in_progress_count: number;
  completed_count: number;
  cancelled_count: number;
  no_show_count: number;
  scheduled_count: number;
}

export interface DoctorDashboard {
  today_date: string;
  doctor_name: string;
  waiting_queue: Appointment[];
  active_consultation?: {
    id: string;
    patient_id: string;
    patient_name: string;
    patient_identifier: string;
    started_at: string;
    status: string;
  } | null;
  upcoming_appointments: Appointment[];
  reports_pending_approval: Array<{
    consultation_id: string;
    patient_name: string;
    patient_identifier: string;
    encounter_time: string;
  }>;
  completed_today_count: number;
}

export interface ConsentRecord {
  id: string;
  consultation_id: string;
  is_granted: boolean;
  consent_purpose: string;
  consent_language: string;
  wording_version: string;
  consent_text_snapshot: string;
  granted_at: string;
  withdrawn_at?: string | null;
}

export interface Consultation {
  id: string;
  organization_id: string;
  location_id?: string | null;
  appointment_id?: string | null;
  patient_id: string;
  doctor_user_id: string;
  status: 'SETUP' | 'RECORDING' | 'PROCESSING' | 'CLINICAL_REVIEW' | 'COMPLETED' | 'CANCELLED';
  started_at: string;
  ended_at?: string | null;
  chief_complaint_summary?: string | null;
  longitudinal_comparison_json?: Record<string, any>;
  consent?: ConsentRecord | null;
}

export interface TranscriptSegment {
  id: string;
  sequence_number: number;
  speaker_label: 'DOCTOR' | 'PATIENT' | 'OTHER';
  start_time_ms: number;
  end_time_ms: number;
  original_text: string;
  corrected_text?: string | null;
  effective_text: string;
  confidence_score: number;
}

export interface TranscriptData {
  transcript_version_id?: string;
  version_number: number;
  source_type: string;
  language_detected?: string;
  full_text: string;
  segments: TranscriptSegment[];
}

export interface ClinicalFactEvidence {
  transcript_segment_id: string;
  evidence_quotation: string;
  start_time_ms?: number;
  end_time_ms?: number;
}

export interface ClinicalFact {
  id: string;
  category: string; // CHIEF_COMPLAINT, SYMPTOM, VITALS, ASSESSMENT, ALLERGY, FOLLOWUP
  fact_key: string;
  fact_value: Record<string, any> | string;
  source_speaker: string;
  provenance_type: 'PATIENT_REPORTED' | 'CLINICIAN_OBSERVED' | 'AI_EXTRACTED' | 'HISTORICAL';
  certainty_status: 'VERIFIED' | 'UNVERIFIED' | 'PATIENT_DENIED' | 'UNCERTAIN';
  doctor_review_status: 'ACCEPTED' | 'EDITED' | 'REJECTED';
  validation_flags?: string[];
  evidence: ClinicalFactEvidence[];
}

export interface MedicationInstruction {
  id: string;
  medication_name: string;
  strength?: string | null;
  dosage?: string | null;
  route?: string | null;
  frequency?: string | null;
  duration?: string | null;
  special_instructions?: string | null;
  uncertainty_flags?: string[];
  doctor_verified: boolean;
  is_historical: boolean;
}

export type ReportType = 'DOCTOR_CLINICAL' | 'DOCTOR_NOTE' | 'PATIENT_SUMMARY';
export type ReportStatus =
  | 'AI_GENERATED_DRAFT'
  | 'DOCTOR_EDITED_DRAFT'
  | 'AWAITING_APPROVAL'
  | 'APPROVED'
  | 'SUPERSEDED';

export interface ReportVersionItem {
  id: string;
  version_number: number;
  status: ReportStatus;
  rendered_markdown: string;
  content_sha256: string;
  created_at: string;
}

export interface ReportItem {
  report_id: string;
  report_type: ReportType;
  current_status: ReportStatus;
  current_version_number: number;
  target_language: string;
  content_markdown: string;
  content_sha256: string;
  all_versions?: ReportVersionItem[];
}

export interface DeliveryOptions {
  patient_name: string;
  mobile_number: string;
  email?: string | null;
  whatsapp_url?: string | null;
  email_url?: string | null;
  message_preview: string;
}

export interface DiscountCoupon {
  id: string;
  code: string;
  description?: string | null;
  discount_type: 'PERCENTAGE' | 'FLAT_INR';
  discount_value: number;
  applicable_plan_codes: string[];
  max_redemptions: number;
  current_redemptions: number;
  valid_until?: string | null;
  is_active: boolean;
  created_at: string;
}

