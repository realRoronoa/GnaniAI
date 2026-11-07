# ArogyaScribe — Master Engineering & Architecture Guide

Welcome to **ArogyaScribe**, a B2B Healthcare Software-as-a-Service (SaaS) platform engineered for outpatient clinics, polyclinics, and hospital networks in India.

ArogyaScribe combines multi-lingual Indian speech recognition (Hinglish/Hindi/English), structured clinical fact extraction with source-linked evidence grounding, strict medication safety verification, and dual-report generation (doctor SOAP encounter notes and vernacular patient summaries with voice narration).

---

## 1. Quick Repository Layout

```text
arogyascribe/
├── START_HERE.md              # Master project map, live build progress log & quickstart
├── frontend/                  # Independent Git Repo (React 19, TypeScript, Tailwind v4)
│   ├── README.md              # Frontend architecture & Phase 7 UI plan
│   ├── .gitignore             # Frontend ignores (node_modules, dist, .next)
│   └── src/                   # Modular feature directory tree (auth, reception, doctors, etc.)
└── backend/                   # Independent Git Repo (FastAPI, SQLAlchemy 2, PostgreSQL 16)
    ├── README.md              # Backend setup, Docker infrastructure, and API map
    ├── docker-compose.yml     # PostgreSQL 16, Redis 7, MinIO + Bucket Provisioner
    ├── pyproject.toml         # Python 3.12+ dependencies (FastAPI, Celery, Alembic)
    ├── .env.example           # Environment template with development defaults
    ├── alembic.ini            # Database migration configuration
    ├── app/                   # Application packages (core, db, api, services, integrations)
    ├── docs/                  # Living Architecture & Engineering Documentation
    │   ├── architecture/      # HLD, LLD (28 Tables), and ADRs (DECISIONS.md)
    │   ├── security/          # Argon2id, JWT, multi-tenancy & clinical safety
    │   ├── testing/           # Test pyramid, unit/integration & 24-step E2E plan
    │   └── implementation/    # Live multi-phase implementation roadmap
    └── tests/                 # Unit, integration, and API test suites
```

> [!IMPORTANT]
> **Independent Git Repositories:** `frontend/` and `backend/` are decoupled Git repositories with independent version histories. The root directory contains no Git repository.

---

## 2. Core Architecture Rules

1. **4 Roles Only — Zero Patient Login:**
   - Platform roles are strictly limited to `PLATFORM_OWNER`, `ORG_ADMIN`, `RECEPTIONIST`, and `DOCTOR`.
   - Patients are purely clinical/administrative records managed by clinic staff. **There are no patient passwords, patient portals, or patient authentication tables.**
2. **Multi-Tenant Isolation:**
   - All clinical records and operations are partitioned by `organization_id`.
3. **Clinical Safety & Human-in-the-Loop:**
   - AI outputs are classified as **AI DRAFT**. Medication facts missing dose, frequency, or duration are unresolved blockers that prevent report approval until explicitly completed or rejected by a doctor.
4. **Dual-Report Approval with SHA-256 Checksums:**
   - Approved reports require cryptographic hash verification (`content_sha256`) to guarantee non-repudiation and prevent race conditions.

---

## 3. Master Documentation Directory (`backend/docs/`)

Explore the detailed engineering documentation before modifying code:

| Document | Purpose & Key Topics |
|---|---|
| [`HLD.md`](backend/docs/architecture/HLD.md) | High-Level Design: multi-tenant B2B hierarchy, role matrix, React + FastAPI + Celery + MinIO stack, and Gnani AI pipeline. |
| [`LLD.md`](backend/docs/architecture/LLD.md) | Low-Level Design: All 28 PostgreSQL tables, Appointment State Machine, Report Versioning State Machine, and AI Provider Interfaces. |
| [`DECISIONS.md`](backend/docs/architecture/DECISIONS.md) | Architecture Decision Records (ADRs 0001 through 0007). |
| [`SECURITY_AND_PRIVACY.md`](backend/docs/security/SECURITY_AND_PRIVACY.md) | Argon2id cryptography, JWT rotation, consent gating, private S3 storage, and clinical safety guardrails. |
| [`TEST_STRATEGY.md`](backend/docs/testing/TEST_STRATEGY.md) | Unit, integration, tenant-isolation, and the 24-step end-to-end clinical workflow test plan. |
| [`IMPLEMENTATION_PLAN.md`](backend/docs/implementation/IMPLEMENTATION_PLAN.md) | Phase-by-phase build tracker (Phases 0 through 7). |

---

## 4. Live Build Progress Log

### Phase 0: Workspace Scaffolding & Core Infrastructure — **COMPLETED** (2026-11-07)
- [x] Initialized independent Git repositories inside `frontend/` and `backend/`. Verified no root `.git`.
- [x] Scaffolded modular directory trees for frontend features and backend services.
- [x] Authored complete production architecture documentation in `backend/docs/`.
- [x] Provisioned `backend/docker-compose.yml` with PostgreSQL 16 (`5432`), Redis 7 (`6379`), MinIO (`9000`/`9001`), and automatic private bucket creation (`arogyascribe-private`).
- [x] Implemented core backend infrastructure: `app.core.config`, `app.core.security` (Argon2id + JWT), `app.db.base` (SQLAlchemy 2 DeclarativeBase + TimestampUUIDMixin), `app.db.session`, and `app.main` with `GET /api/v1/health`.
- [x] Verified unit tests for security, hashing, JWT claims, and health endpoint.

### Phase 1: Database Schema, Migrations, Seeder & SaaS Core APIs — **COMPLETED** (2026-11-07)
- [x] Enforced Master Specification on 4 roles (`PLATFORM_OWNER`, `ORG_ADMIN`, `RECEPTIONIST`, `DOCTOR`), zero patient login, `AppointmentStatus`, `AppointmentType`, `ReportStatus`, and the 5 AI provider contracts in `backend/docs/architecture/LLD.md`.
- [x] Implemented all 28 core SQLAlchemy 2 models across `tenant.py`, `subscriptions.py`, `patients_appointments.py`, `consultations_audio.py`, `clinical_reports.py`, and `system_audit.py`.
- [x] Created baseline Alembic migration `backend/migrations/versions/0001_initial_schema.py`.
- [x] Authored idempotent synthetic demo seeder `backend/scripts/seed_demo.py` with 4 platform accounts, 3 subscription tiers, a multi-branch polyclinic, and 2 synthetic patient records.
- [x] Built SaaS Core APIs: Authentication & RBAC (`/api/v1/auth`), Platform Admin (`/api/v1/platform`), and Organization Admin with entitlement quota enforcement (`/api/v1/org`).
- [x] Created automated test suite `tests/api/test_phase1_saas_core.py` verifying Platform Owner onboarding, Org Admin staff management, plan entitlement boundaries, and cross-tenant/role isolation (all 8 tests passing).

### Phase 2: Reception Operations, Duplicate-Safe Patient Engine & Appointment Queues — **COMPLETED** (2026-11-07)
- [x] Implemented pre-registration duplicate detection (`GET /api/v1/patients/check-duplicates`), allowing explicit family creation sharing phone numbers (Rule Part 4.3).
- [x] Built patient registration and search (`POST /api/v1/patients`, `GET /api/v1/patients`, `GET /api/v1/patients/{id}`, `PATCH /api/v1/patients/{id}`).
- [x] Implemented appointment booking (`POST /api/v1/appointments`) with automatic queue positioning.
- [x] Built strict finite state machine transition validator (`PATCH /api/v1/appointments/{id}/status`), preventing terminal states from moving backward and recording transition timestamps.
- [x] Built doctor reassignment (`PATCH /api/v1/appointments/{id}/assign-doctor`).
- [x] Implemented Reception Dashboard Overview (`GET /api/v1/reception/overview`) and doctor-grouped queue views (`GET /api/v1/appointments/queue`).

### Phase 3: Doctor Workspace, Longitudinal Patient History & Mandatory Consent Capture — **COMPLETED** (2026-11-07)
- [x] Built Doctor Workspace (`GET /api/v1/doctor/dashboard`) with queue isolation, active consultation, waiting patients, and pending reports.
- [x] Implemented Longitudinal Patient History (`GET /api/v1/patients/{id}/longitudinal-history`) returning chronological consultations, approved notes, and historical medications (`is_historical=True`).
- [x] Implemented consultation start (`POST /api/v1/consultations`), transitioning appointments to `IN_PROGRESS` and checking monthly consultation quotas.
- [x] Implemented mandatory informed consent gate (`POST /api/v1/consultations/{id}/consent`) and consent withdrawal (`POST /api/v1/consultations/{id}/consent/withdraw`), reverting consultation status to `SETUP` and blocking recording on withdrawal.
- [x] Comprehensive test suite `tests/api/test_phase2_3_reception_doctor_workflow.py` asserting all 5 test scenarios (all 13 tests passing across Phases 0 through 3).

### Phase 4: Audio Storage, Pluggable AI Pipeline, Transcript Review & Grounded Facts — **COMPLETED** (2026-11-07)
- [x] Implemented private S3/MinIO storage service (`StorageService`) with automatic in-memory fallback for automated testing.
- [x] Implemented audio upload (`POST /api/v1/consultations/{id}/audio`) with mandatory informed patient consent verification (strictly blocked with 403 Forbidden without consent).
- [x] Built 5 provider-independent AI contracts (`TranscriptionProvider`, `ClinicalExtractionProvider`, `ReportGenerationProvider`, `TranslationProvider`, `TextToSpeechProvider`) with live Gnani integration stubs and deterministic clinical mocks.
- [x] Implemented Celery worker tasks (`process_consultation_pipeline` and `process_consultation_audio_task`) orchestrating audio transcription, fact extraction, and dual draft generation.
- [x] Implemented transcript review and doctor corrections (`GET /api/v1/consultations/{id}/transcript`, `PUT/PATCH /api/v1/consultations/{id}/transcript`), preserving original AI text with complete audit trail.
- [x] Built clinical fact review with evidence grounding (`GET /api/v1/consultations/{id}/facts`, `PATCH /api/v1/consultations/{id}/facts/{id}`).

### Phase 5: Medication Verification, Dual-Report Approval, PDF Generation & Patient Delivery — **COMPLETED** (2026-11-07)
- [x] Implemented medication safety verification (`GET /api/v1/consultations/{id}/medications`, `PATCH /api/v1/consultations/{id}/medications/{id}/verify`), enforcing Part 8.3 & Part 9.3 guardrail: approval is strictly blocked (HTTP 400) if any medication instruction has unresolved uncertainty flags or is unverified.
- [x] Implemented doctor-only report approval (`POST /api/v1/consultations/{id}/approve`), transitioning reports to `APPROVED`, generating doctor and patient summary PDFs, and concluding consultation and linked appointment to `COMPLETED`.
- [x] Built report superseding logic (`PUT/PATCH /api/v1/consultations/{id}/reports/{type}`): editing an approved report supersedes the previous version and increments to a new `DOCTOR_EDITED_DRAFT` requiring re-approval.
- [x] Implemented ReportLab PDF generator (`PDFService`) producing professional clinical doctor encounter PDFs and vernacular patient summaries with hospital metadata, QR/signatures, and digital hashes.
- [x] Implemented PDF download endpoints (`GET /api/v1/consultations/{id}/reports/{type}/pdf` and `GET /api/v1/consultations/{id}/pdfs/{type}/download`).
- [x] Built WhatsApp & Email delivery share links (`GET /api/v1/consultations/{id}/reports/patient-summary/share-link`) and manual share logging (`POST /api/v1/consultations/{id}/reports/patient-summary/mark-shared`).
- [x] Created comprehensive test suite `tests/api/test_phase4_5_clinical_ai_reports_e2e.py` (all 6 tests passing, bringing the total backend test suite to 19/19 passing tests with 100% backend completion).

### Phase 6: Celery Worker Deployment & Production Hardening — **BACKEND COMPLETE**
- [x] Celery app, task queue, and synchronous pipeline fallback fully wired and verified.

### Phase 7A: Frontend Phase A (Design System, Auth, Public Website & Platform Owner / Org Admin Consoles) — **COMPLETED** (2026-11-07)
- [x] Extracted exact UI tokens from reference handoff (`arogyascribe-ui-handoff-v3.zip`): Mineral Sage (`#D7DCCF`), Deep Forest (`#172820`), Burnt Copper (`#A84F38`), and Antique Brass (`#C29A5B`).
- [x] Setup React 18 + TypeScript + Vite + Tailwind CSS with strict types and alias path resolution.
- [x] Core architecture: Axios API client with automatic token attachment, 401 refresh rotation, AuthContext provider, and role-based route guards (4 roles only, zero patient login).
- [x] Built design-matched reusable UI components (`AppLayout`, `Button`, `Modal`, `DataTable`, `Card`, `StatCard`, `StatusBadge`).
- [x] Public Website: High-conversion landing page with interactive 5-tab consultation demo, role cards, pricing comparison, and organization registration modal.
- [x] Unified Sign-in (`/login`) with 1-click **Quick Demo Role Fill** bar for all 4 seeded roles (`superadmin@arogyascribe.in`, `orgadmin@arogyacare.in`, `reception@arogyacare.in`, `dr.sharma@arogyacare.in`).
- [x] Platform Owner Console (`/platform/*`): Overview metrics, searchable Organizations directory with status toggle, Organization details, Subscription plans & manual activation modal, and immutable Audit Log viewer.
- [x] Organization Admin Console (`/org/*`): Clinic overview with visual entitlement gauges, branch management, staff roster (doctors & receptionists), and weekly doctor shift schedules.
- [x] Build verified: `tsc` and `vite build` completed with 0 errors.

### Phase 7B: Frontend Phase B (Reception Console, Doctor Clinical Studio & V2 Roadmap) — **COMPLETED** (2026-11-07)
- [x] Reception Console:
  - Live OPD Queue & Daily Overview (`/reception/overview`, `/reception/queue`) with status filter tabs, 15-second polling, and 1-click arrival/waiting transitions.
  - Patient Directory (`/reception/patients`) with real-time pre-registration duplicate phone check (`GET /api/v1/patients/check-duplicates`), non-blocking family warning card, and patient editor modal.
  - Outpatient Appointment Booking (`/reception/appointments`) with doctor assignment, branch selection, and inline doctor reassignment modal.
  - Manual Report Delivery Desk (`/reception/delivery`) allowing receptionists to download approved Patient Summary PDFs, generate one-click WhatsApp / Email links, and record manual dispatch logs (`POST /api/v1/consultations/{id}/mark-shared`).
- [x] Doctor Clinical Workspace:
  - Doctor Dashboard (`/doctor/dashboard`) displaying active consultation spotlight, waiting room queue with 1-click "Start Visit" CTA, and unapproved draft counters.
  - Longitudinal Patient Profile (`/doctor/patients/:patientId`) featuring allergy banners, chronological consultation timeline, and explicitly labeled **Historical Prescriptions** (`HISTORICAL — Verify before continuing`).
  - Distraction-Free Multi-Stage Consultation Studio (`/doctor/consultations/:consultationId`):
    - **Stage 1 (Consent & Audio Capture):** Mandatory consent gate with withdrawal control, real `navigator.mediaDevices.getUserMedia` + `MediaRecorder` audio recording with live timer, explicit text state badge (`RECORDING ACTIVE — MIC LIVE`), plus a **1-Click Synthetic Consultation Audio Fallback** for physical mic-less workstations.
    - **Stage 2 (Transcript & Fact Provenance):** Diarized multi-speaker transcript viewer with inline audited doctor edits (`PUT .../transcript`), and structured clinical facts with quotation citations and Accept/Reject review actions.
    - **Stage 3 (Medication Safety Verification):** Missing dose/duration detection flags and doctor confirmation modal (`PUT .../medications/{id}`). Non-bypassable approval gate strictly prevents report sign-off until all medications are confirmed.
    - **Stage 4 (Dual-Report Approval & Delivery):** Side-by-side doctor SOAP report and vernacular Hindi patient summary editor, versioning with superseding tracking, cryptographic doctor approval (`POST .../approve`), and instant PDF generation/download.
- [x] Upcoming Features & V2 Roadmap (`/upcoming`): Showcase of all 8 planned roadmap items badged `COMING SOON — PLANNED FOR FUTURE RELEASE` with MVP vs V2 automation comparison matrix.
- [x] Production Build Verification: `npm run build` compiled 1680 modules cleanly with 0 TypeScript and 0 Vite errors.

### Phase 7C: Contract Alignment, Automated Test Suites & 24-Step E2E Verification — **COMPLETED** (2026-11-07)
- [x] **Contract Alignment & API Hardening:**
  - Standardized JWT login response unpacking (`access_token`, `refresh_token`, `token_type`, `user`) across `LoginPage.tsx` and `LandingPage.tsx`.
  - Added public organization inquiry onboarding (`POST /api/v1/organizations/register` and `POST /api/v1/org/register`).
  - Added safe password recovery endpoint (`POST /api/v1/auth/password/forgot`).
  - Unified staff roster and schedule endpoints (`GET /api/v1/org/staff` and `location_id` mapping).
  - Aligned Reception and Doctor studio payloads (consent text snapshots, duplicate phone detection responses, manual WhatsApp/Email delivery hooks).
- [x] **Frontend Vitest Test Suite (`frontend/src/__tests__/app_workflows.test.tsx`):**
  - Configured Vitest, `@testing-library/react`, `@testing-library/jest-dom`, and `jsdom`.
  - Implemented 6 comprehensive automated test suites covering:
    1. Strict 4-Role RBAC Model (Zero Patient Login) & unauthenticated redirect to `/login`.
    2. Upcoming Features & V2 Roadmap verification (all 8 cards verified with exact `COMING SOON — PLANNED FOR FUTURE RELEASE` badge).
    3. Reception Duplicate Patient Registration and family-sharing phone detection.
    4. Mandatory Informed Consent Gate (blocking recording before consent, enabling after consent).
    5. Medication Safety Guardrail (missing dosage/duration flags & Doctor Verification blocker).
    6. Dual-Report Markdown Editors & Doctor Approval Action.
  - **Result:** `npm test` passed 6/6 tests (100% pass rate).
- [x] **Backend 24-Step End-to-End Master Test Suite (`tests/api/test_24_step_e2e_workflow.py`):**
  - Sequentially executed all 24 steps from Specification Part 19 in a single continuous clinical & SaaS lifecycle:
    1. Platform Owner logs in
    2. New tenant organization created
    3. Subscription plan assigned with entitlement limits
    4. Org Admin logs in
    5. Receptionist and Doctor staff users created
    6. Doctor OPD weekly schedule configured
    7. Receptionist logs in
    8. Duplicate patient phone check executed
    9. Patient registered with demographic UHID
    10. Walk-in appointment booked and placed in queue
    11. Patient arrives; status transitioned `ARRIVED` -> `WAITING`
    12. Doctor logs in and accesses workspace queue
    13. Doctor starts consultation encounter (`IN_PROGRESS`)
    14. Mandatory informed consent recorded
    15. Audio consultation payload uploaded to private object store
    16. Multi-lingual AI pipeline triggered
    17. Doctor reviews and corrects diarized transcript
    18. Clinical facts verified against transcript evidence quotes
    19. Unverified medication identified; doctor resolves missing dosage
    20. Dual draft reports reviewed (Doctor SOAP note + Vernacular Patient Summary)
    21. Cryptographic approval executed; consultation and appointment marked `COMPLETED`
    22. Authorized staff downloads approved Patient Summary PDF
    23. Patient summary shared manually via WhatsApp & delivery confirmed
    24. Longitudinal patient profile displays completed visit & approved records
  - **Result:** `pytest -v` passed all 20 tests (20 passed, 0 failed, 100% backend pass rate).

### Phase 7D: Dynamic Production Pricing, Public Plans API & Super Admin Pricing Studio — **COMPLETED** (2026-11-07)
- [x] **Exact Production Pricing Seed Data (`seed_demo.py`):**
  - **Starter Plan:** ₹4,999/month (₹49,990/year), For independent clinics. Quotas: 2 doctors, 1 receptionist, 1 branch, 250 consultations/month, 25 GB storage (25,600 MB).
  - **Professional Plan (Recommended):** ₹14,999/month (₹149,990/year), For growing clinics. Quotas: 10 doctors, 4 receptionists, 3 branches, 1,000 consultations/month, 100 GB storage (102,400 MB).
  - **Enterprise Plan:** ₹49,999/month (₹499,990/year), For hospitals and medical centres. Quotas: 25 doctors, 10 receptionists, 10 branches, 3,000 consultations/month, 500 GB storage (512,000 MB).
- [x] **Public Plans API (`GET /api/v1/plans/public`):**
  - Serves live active database subscription plans to public landing page and clinic registration modals without authentication.
- [x] **Dynamic Landing Page Pricing Grid (`LandingPage.tsx`):**
  - Dynamically renders live database plans, exact rupee symbols (`₹`), monthly/annual billing toggles, bulleted features list, and high-contrast styling.
- [x] **Platform Owner Pricing & Coupon Studio (`PlansBillingPage.tsx`):**
  - Interactive pricing management studio with live customer card preview, quota controls, promo coupon code simulator (`PERCENTAGE`, `FLAT_INR`, `FIXED_OVERRIDE_INR`), and database patch button (`PATCH /api/v1/platform/plans/{plan_id}`).
  - Verified live: changing prices in Super Admin instantly reflects on the public landing page with zero cache lag.

### Phase 7E: Security Lockdown, B2B Customer Onboarding & Cloud Packaging — **COMPLETED** (2026-11-07)
- [x] **Super Admin Security Lockdown (Zero Hardcoded Credentials):**
  - Moved all administrator and demo passwords strictly to environment variables (`backend/.env`): `SUPERADMIN_EMAIL`, `SUPERADMIN_INITIAL_PASSWORD`, `OWNER_NOTIFICATION_EMAIL`, `DEMO_ORG_ADMIN_PASSWORD`, etc.
  - Sanitized `backend/.env.example` with safe placeholder strings (`CHANGE_ME_STRONG_SECRET_PASSWORD`).
  - Removed Super Admin ("Platform Owner") from public frontend auto-fill buttons. Super Admin logs in strictly by typing credentials.
  - Gated clinic staff 1-click demo switcher with `VITE_ENABLE_DEMO_BAR !== 'false'`.
- [x] **Complete B2B Customer Acquisition Pipeline:**
  - Public registration (`POST /api/v1/organizations/register`) creates `PENDING` organizations with requested plans and coupons without activating login.
  - Instant email alerts dispatched to Platform Owner (`EmailNotificationService` in `backend/app/integrations/email/email_service.py`), logged to `./storage/email_outbox.log`, and recorded via `AuditEvent`.
  - Platform Owner connects & approves pending clinics in dashboard (`POST /api/v1/platform/organizations/{org_id}/approve-onboarding`), creating active subscriptions, primary branches, and Org Admin accounts with temporary passwords.
  - Plan quotas strictly enforced when Org Admins add staff (`check_doctor_limit`, `check_receptionist_limit`, `check_branch_limit`), with live counters in `OrgStaffPage.tsx`.
- [x] **Pan-India Multilingual & Cloud Packaging:**
  - 9 languages supported: `en`, `hi`, `ta`, `te`, `kn`, `ml`, `mr`, `bn`, `gu`.
  - ReportLab PDF download & in-browser printable Indic summary (`window.print()`) with Google Noto Indic fonts.
  - Gnani AI credit guardrail: SHA-256 disk cache under `./storage/gnani_cache/` + 6-call hard circuit breaker.
  - Containerization: `backend/Dockerfile`, `frontend/Dockerfile`, `nginx.conf`, and `frontend/vercel.json`.

---

## 5. Demo Accounts & Credentials

The synthetic demo seeder (`python scripts/seed_demo.py`) provisions the following accounts from environment configuration (`.env`):

| Role | Email | Password Source | Scope |
|---|---|---|---|
| **Platform Owner** | `superadmin@arogyascribe.in` | `SUPERADMIN_INITIAL_PASSWORD` (.env) | Global SaaS Administration (Type manually) |
| **Org Admin** | `orgadmin@arogyacare.in` | `DEMO_ORG_ADMIN_PASSWORD` (.env) | Arogya Care Multi-Specialty Clinic |
| **Receptionist** | `reception@arogyacare.in` | `DEMO_RECEPTIONIST_PASSWORD` (.env) | Indiranagar Main Branch |
| **Doctor** | `dr.sharma@arogyacare.in` | `DEMO_DOCTOR_PASSWORD` (.env) | General Medicine (Indiranagar Main Branch) |

*(Note: During local demo mode, Org Admin, Receptionist, and Doctor accounts can be signed into with 1 click from the demo bar. Super Admin must type their password directly).*

---

## 6. Quickstart for Developers

### Boot Infrastructure
```bash
cd backend
docker-compose up -d
```

### Run Backend API
```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```
Visit API Documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)  
Health Check: [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)

