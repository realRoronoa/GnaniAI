# ArogyaScribe — Test Strategy & Quality Assurance Plan

## 1. Testing Philosophy

ArogyaScribe is a medical documentation platform. Errors in clinical facts, unauthorized access to protected health records, or silent data corruption can compromise patient care. The testing strategy enforces:
1. **Zero Mock Leaks:** Tests verify both deterministic local mock adapters and real provider interfaces.
2. **Strict Multi-Tenant Verification:** Every data-access path is tested for cross-tenant isolation.
3. **Clinical Safety Rule Enforcement:** Every clinical safety rule (consent requirement, medication completeness blocker, hash verification) has dedicated automated assertions.

---

## 2. Test Pyramid & Execution Tiers

```text
       ▲
      / \        Tier 4: 24-Step End-to-End Workflow Tests (API & Scenario)
     /---\
    /     \      Tier 3: Multi-Tenant Isolation & Security Tests
   /-------\
  /         \    Tier 2: Service & Database Integration Tests (PostgreSQL, MinIO)
 /-----------\
/             \  Tier 1: Pure Unit Tests (Password hashing, JWT, schemas, phone normalizer)
```

### 2.1 Tier 1: Unit Tests
- Fast, in-memory, zero network dependencies.
- Coverage:
  - `Argon2id` password hashing and verification.
  - JWT generation, claims validation (`sub`, `role`, `org_id`, `type`, `jti`), and expiry rejection.
  - Indian mobile number normalization (`normalizeIndianMobile`) with valid/invalid inputs.
  - WhatsApp message formatting and length constraints.

### 2.2 Tier 2: Database & Integration Tests
- Exercises SQLAlchemy models, migrations, and database constraints against PostgreSQL or SQLite.
- Coverage:
  - `TimestampUUIDMixin` automatic timestamping on insert/update.
  - Foreign key cascade deletions on tenant removal.
  - Unique constraints (`(organization_id, uhid)`, `slug`, `email`).
  - Pre-signed URL generation and private bucket upload via `StorageInterface`.

### 2.3 Tier 3: Multi-Tenant Isolation & Role Security Tests
- Explicitly attempts unauthorized cross-tenant operations:
  - User from Organization A attempts to fetch or update a Patient from Organization B.
  - Receptionist attempts to access doctor-only report sign-off endpoints.
  - Doctor attempts to access platform-owner subscription management routes.
- Expectation: Always returns HTTP 403 Forbidden or 404 Not Found.

---

## 3. The 24-Step End-to-End Clinical Lifecycle Test Plan

A comprehensive scenario test validating the entire business workflow:

1. **Platform Initialization:** Platform owner registers and sets up subscription plans.
2. **Organization Registration:** Clinic administrator signs up and creates Organization A.
3. **Location Provisioning:** Clinic admin adds physical branch location.
4. **Staff Onboarding:** Clinic admin creates Doctor and Receptionist credentials.
5. **Reception Login:** Receptionist logs in and acquires scoped JWT.
6. **Patient Registration:** Receptionist creates a new patient record with unique UHID.
7. **Appointment Scheduling:** Receptionist books an outpatient appointment for the Doctor.
8. **Doctor Queue View:** Doctor logs in and inspects the location queue.
9. **Patient Check-in:** Receptionist marks appointment status as `CHECKED_IN`.
10. **Consultation Initiation & Consent Gate:** Doctor admits patient; attempts audio capture before consent and verifies HTTP 403 rejection.
11. **Consent Recording:** Explicit recording consent is registered for the encounter.
12. **Audio Chunk Upload:** 16 kHz mono WAV audio chunks are uploaded and stored in private object storage.
13. **Audio Transcription:** STT pipeline ingests chunks in chronological sequence.
14. **Transcript Attribution:** Transcript segments are emitted with speaker labels and millisecond offsets.
15. **Clinical Fact Extraction:** LLM extracts structured symptoms, diagnoses, and medication facts.
16. **Safety Blocker Trigger:** Medication with missing dose/duration is flagged as `unresolved`.
17. **Approval Refusal:** Attempting to approve clinical report with unresolved blocker fails with HTTP 409 `UNRESOLVED_FACTS`.
18. **Doctor Fact Editing:** Doctor fills in missing dose and duration directly on the fact.
19. **Doctor Acceptance:** Fact status transitions to `unreviewed` then `accepted`.
20. **Draft Note Generation:** System generates clinician SOAP note and vernacular patient summary.
21. **Doctor Note Approval:** Doctor signs off on doctor note with matching SHA-256 hash.
22. **Patient Summary Approval:** Doctor signs off on patient summary draft.
23. **Voice Note Synthesis:** Vernacular TTS synthesizes audio narration for the approved patient summary.
24. **Patient Dispatch:** WhatsApp share URL is prepared from approved text with verified patient mobile number.

---

## 4. Test Tooling, CI Configuration & Automated Execution

- **Backend Runner:** `pytest` with `pytest-asyncio` and `pytest-cov`.
- **Target Coverage:** > 90% line coverage across `app/core/`, `app/services/`, and `app/api/`.
- **Linter & Type Check:** `ruff check .` and `mypy app tests`.

### 4.1 Automated Test Execution Results

#### Backend Test Suite (`pytest -v`)
- **Master 24-Step Lifecycle:** `tests/api/test_24_step_e2e_workflow.py::test_24_step_complete_clinical_and_saas_lifecycle_e2e` **PASSED**
- **SaaS Core & Tenant Security:** `tests/api/test_phase1_saas_core.py` (3 tests) **PASSED**
- **Reception & Doctor Lifecycles:** `tests/api/test_phase2_3_reception_doctor_workflow.py` (5 tests) **PASSED**
- **AI Pipeline, Medication Safety & Approval:** `tests/api/test_phase4_5_clinical_ai_reports_e2e.py` (6 tests) **PASSED**
- **Core Security & Hashing:** `tests/unit/test_core_infrastructure.py` (5 tests) **PASSED**
- **Total Backend Tests:** **20 passed, 0 failed, 1 warning (100% pass rate)**.

#### Frontend Vitest Suite (`npm test`)
- **Test File:** `frontend/src/__tests__/app_workflows.test.tsx`
- **Scenarios Tested:**
  1. Role-Based Access Control & Strict 4-Role Model (Zero Patient Login) & unauthenticated redirect to `/login`
  2. Upcoming Features (V2 Roadmap) with exact `COMING SOON — PLANNED FOR FUTURE RELEASE` badge
  3. Reception Duplicate Patient Registration and family phone number sharing
  4. Mandatory Informed Consent Gate (audio recording blocked before consent)
  5. Medication Safety Guardrail (missing dosage/frequency flags & Doctor Verification blocker)
  6. Dual-Report Markdown Editors & Doctor Approval Action
- **Total Frontend Tests:** **6 passed, 0 failed (100% pass rate)**.


