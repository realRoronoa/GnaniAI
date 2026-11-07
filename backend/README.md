# ArogyaScribe — Backend Infrastructure & API

FastAPI, SQLAlchemy 2.0, PostgreSQL 16, Celery, and Redis backend engine for the **ArogyaScribe** B2B healthcare SaaS platform.

---

## 1. Directory Structure

```text
backend/
├── app/
│   ├── api/v1/                # Versioned REST endpoints (health, auth, patients, etc.)
│   ├── core/                  # Core configurations, security (Argon2id, JWT), and errors
│   ├── db/                    # SQLAlchemy 2 DeclarativeBase, session, and engine
│   ├── domain/                # Pure business logic and domain entities
│   ├── integrations/          # AI (Gnani/Mock), Storage (S3/MinIO), Messaging (WhatsApp)
│   ├── models/                # SQLAlchemy database models (28 relational tables)
│   ├── repositories/          # Data access repository patterns
│   ├── schemas/               # Pydantic v2 validation and serialization schemas
│   ├── services/              # Workflow orchestrators and business services
│   ├── templates/             # Clinical note and print templates
│   ├── utils/                 # General helpers (audio chunking, hash utilities)
│   └── workers/               # Celery worker tasks and queue configurations
├── docs/                      # Living Architecture and Engineering Documentation
├── migrations/                # Alembic database migration scripts
├── scripts/                   # Seed, backup, and maintenance scripts
├── tests/                     # Unit, integration, and API test suites
├── alembic.ini                # Alembic migration configuration
├── docker-compose.yml         # PostgreSQL 16, Redis 7, MinIO + init script
├── pyproject.toml             # Python package configuration and dependencies
├── .env.example               # Environment variables template
└── README.md                  # This document
```

---

## 2. Infrastructure Services (Docker)

Launch the core storage, queue, and database services:

```bash
docker-compose up -d
```

| Service | Port | Purpose | Default Credentials |
|---|---|---|---|
| **PostgreSQL 16** | `5432` | Primary multi-tenant relational database | `arogyascribe` / `local_dev_password_change_in_prod` |
| **Redis 7** | `6379` | Celery message broker and result cache | *(No authentication required in local dev)* |
| **MinIO API** | `9000` | S3-compatible private object storage for audio & PDFs | `minioadmin` / `minioadminpassword` |
| **MinIO Console** | `9001` | Web administration UI for MinIO | `minioadmin` / `minioadminpassword` |
| **minio-init** | — | Automatic private bucket provisioner (`arogyascribe-private`) | *(Runs once upon container startup)* |

---

## 3. Local Development Setup

### 3.1 Create Virtual Environment & Install Dependencies
```bash
python -m venv .venv

# On Windows:
.venv\Scripts\activate

# On Linux/macOS:
source .venv/bin/activate

pip install -e ".[dev]"
```

### 3.2 Configure Environment
```bash
cp .env.example .env
```

### 3.3 Database Migrations & Synthetic Demo Seeder
```bash
# Run migrations
alembic upgrade head

# Seed synthetic demo data (Platform Owner, 3 Plans, Demo Polyclinic, Org Admin, Receptionist, Doctor, 2 Patients)
python scripts/seed_demo.py
```

### 3.4 Start the FastAPI API Server
```bash
uvicorn app.main:app --reload --port 8000
```
- Interactive Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Health Telemetry: [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)

---

## 4. Phase 1 APIs & Endpoints

### 4.1 Authentication & RBAC (`/api/v1/auth`)
- `POST /api/v1/auth/login`: Authenticate staff, check organization status, issue access/refresh JWT tokens.
- `POST /api/v1/auth/refresh`: Rotate and refresh active session tokens.
- `POST /api/v1/auth/logout`: Invalidate user session.
- `GET /api/v1/auth/me`: Retrieve current user profile, active tenant membership, and clinician/receptionist profile details.
- `POST /api/v1/auth/password/forgot`: Safe public forgot password endpoint.
- `POST /api/v1/organizations/register`: Public clinic onboarding endpoint (initiates Step 1 of the B2B onboarding pipeline).

### 4.2 Platform Owner / Super Admin (`/api/v1/platform`)
- `GET /api/v1/platform/overview`: System-wide telemetry (total orgs, subscriptions, doctors, receptionists, consultations).
- `GET /api/v1/platform/organizations`: List all tenant clinics and polyclinics.
- `POST /api/v1/platform/organizations`: Onboard new organization with main branch, initial Org Admin, and trial plan.
- `POST /api/v1/platform/organizations/{org_id}/approve-onboarding`: Connect & approve pending clinic registration inquiries, generate temporary credentials, and provision active plan quotas.
- `PATCH /api/v1/platform/organizations/{org_id}/status`: Activate, suspend, or deactivate organizations.
- `GET /api/v1/platform/plans`: List platform subscription tiers.
- `POST /api/v1/platform/plans`: Create new subscription plan tier.
- `PATCH /api/v1/platform/plans/{plan_id}`: Update plan pricing or limits.
- `POST /api/v1/platform/subscriptions/activate`: Activate subscription, record payment transaction, and provision entitlements.
- `GET /api/v1/platform/subscriptions`: List all tenant subscriptions.
- `GET /api/v1/platform/audit-events`: System audit log inspection.

### 4.3 Organization Admin & Entitlements (`/api/v1/org`)
- `GET /api/v1/org/dashboard`: Real-time tenant operational dashboard.
- `GET /api/v1/org/profile` & `PATCH /api/v1/org/profile`: View and update clinic profile.
- `GET /api/v1/org/branches`: List all physical clinic branches.
- `POST /api/v1/org/branches`: Create a branch (*enforces `max_branches` plan quota*).
- `GET /api/v1/org/staff`: Overview of doctors and receptionists.
- `POST /api/v1/org/staff/doctors`: Register doctor profile (*enforces `max_doctors` plan quota*).
- `POST /api/v1/org/staff/receptionists`: Register front-desk receptionist (*enforces `max_receptionists` plan quota*).
- `GET /api/v1/org/schedules` & `POST /api/v1/org/schedules`: Weekly doctor shift rosters.
- `GET /api/v1/org/subscription`: Quota usage vs plan limits.

### 4.4 Patient Management & Longitudinal History (`/api/v1/patients`)
- `GET /api/v1/patients/check-duplicates`: Verify mobile and name for potential matches without auto-merging families.
- `POST /api/v1/patients`: Register a new patient (strictly clinical/admin record; no login).
- `GET /api/v1/patients`: Search patient directory by name, UHID, or mobile number.
- `GET /api/v1/patients/{id}` & `PATCH /api/v1/patients/{id}`: View and update patient profile and administrative notes.
- `GET /api/v1/patients/{id}/longitudinal-history`: Attending clinician view: past consultations, approved notes, and historical medications (`is_historical=True`).

### 4.5 Appointments & Reception Queue (`/api/v1/appointments` & `/api/v1/reception`)
- `POST /api/v1/appointments`: Book scheduled or walk-in appointment with automated queue calculation.
- `PATCH /api/v1/appointments/{id}/status`: Validated finite state machine transition validator (`SCHEDULED` -> `CONFIRMED` -> `ARRIVED` -> `WAITING` -> `IN_PROGRESS` -> `COMPLETED`).
- `PATCH /api/v1/appointments/{id}/assign-doctor`: Reassign an appointment to another clinician.
- `GET /api/v1/appointments/queue`: Filterable queue grouped by doctor with waiting room ordering.
- `GET /api/v1/reception/overview`: Receptionist dashboard tallying today's visits by status.

### 4.6 Doctor Workspace, Consultations & Consent Gate (`/api/v1/doctor` & `/api/v1/consultations`)
- `GET /api/v1/doctor/dashboard`: Doctor workspace displaying active encounter, waiting queue, upcoming patients, and pending notes.
- `POST /api/v1/consultations`: Start or resume a consultation session and transition appointment to `IN_PROGRESS`.
- `GET /api/v1/consultations/{id}`: Retrieve encounter status and consent record.
- `POST /api/v1/consultations/{id}/consent`: Record specific informed patient consent before audio recording can begin.
- `POST /api/v1/consultations/{id}/consent/withdraw`: Withdraw consent, immediately reverting consultation to `SETUP` and blocking recording/processing.

### 4.7 Audio Recording & Pluggable AI Pipeline (`/api/v1/consultations/{id}`)
- `POST /api/v1/consultations/{id}/audio`: Private S3 audio upload strictly gated by active patient consent.
- `POST /api/v1/consultations/{id}/process`: Synchronous or Celery pipeline trigger running transcription, clinical fact extraction, and dual draft report generation.

### 4.8 Transcript & Clinical Review (`/api/v1/consultations/{id}`)
- `GET /api/v1/consultations/{id}/transcript`: Active encounter transcript segments with speaker labels and confidence scores.
- `PUT` / `PATCH /api/v1/consultations/{id}/transcript`: Doctor transcript editing preserving original AI text with full audit trail.
- `GET /api/v1/consultations/{id}/facts`: Extracted clinical facts with evidence citations.
- `GET /api/v1/consultations/{id}/medications`: Structured prescriptions with uncertainty flags.
- `PUT` / `PATCH /api/v1/consultations/{id}/medications/{id}/verify`: Doctor prescription verification (resolving uncertainty flags).

### 4.10 Subscription Plans & Public Pricing (`/api/v1/plans`)
- `GET /api/v1/plans/public`: Publicly accessible active plans for landing page and registration.
- `GET /api/v1/platform/plans`: Super Admin full plan list.
- `POST /api/v1/platform/plans`: Super Admin plan creation.
- `PATCH /api/v1/platform/plans/{plan_id}`: Super Admin live pricing and quota updates.

---

## 5. Security Lockdown, Environment Credentials & B2B Pipeline

### 5.1 Environment Variable Configuration (`backend/.env`)
All production and seed credentials are strictly loaded via Pydantic settings from `.env`. Zero secrets are hardcoded in the codebase:
- `SUPERADMIN_EMAIL`: Platform Owner login email (e.g. `superadmin@arogyascribe.in`).
- `SUPERADMIN_INITIAL_PASSWORD`: Secret Platform Owner password (never exposed to client).
- `OWNER_NOTIFICATION_EMAIL`: Recipient mailbox for incoming clinic registration notifications.
- `DEMO_ORG_ADMIN_PASSWORD`: Org Admin demo password for seed testing.
- `DEMO_RECEPTIONIST_PASSWORD`: Receptionist demo password for seed testing.
- `DEMO_DOCTOR_PASSWORD`: Doctor demo password for seed testing.
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`: Production outbound email transport (falls back gracefully to `./storage/email_outbox.log` when unconfigured).
- `GNANI_GUARD_ENABLED`: Strict guardrail preventing live Gnani consumption beyond safety thresholds.

### 5.2 Real B2B Customer Onboarding Pipeline (4 Steps)
1. **Clinic Inbound Lead (`POST /api/v1/organizations/register`):** Clinic submits registration on landing page; creates `PENDING` organization record without activating staff login.
2. **Owner Email Notification (`EmailNotificationService`):** System dispatches high-priority alert to `OWNER_NOTIFICATION_EMAIL` and appends full metadata to `./storage/email_outbox.log` and `AuditEvent`.
3. **Owner Review & Approval (`POST /api/v1/platform/organizations/{org_id}/approve-onboarding`):** Platform Owner verifies the clinic, applies custom or coupon discounts, generates secure temporary credentials, and transitions organization to `ACTIVE`.
4. **Org Admin Staff Provisioning with Quota Enforcement:** Org Admin logs in and invites doctors and receptionists; `EntitlementService` strictly enforces subscription plan caps.

### 5.3 Production Subscription Plans
1. **Starter Plan:** ₹4,999/month (Max 2 doctors, 1 receptionist, 1 branch, 250 visits/month, 25 GB storage).
2. **Professional Plan (Recommended):** ₹14,999/month (Max 10 doctors, 4 receptionists, 3 branches, 1,000 visits/month, 100 GB storage, 9 Indian language summaries).
3. **Enterprise Plan:** ₹49,999/month (Max 25 doctors, 10 receptionists, 10 branches, 3,000 visits/month, 500 GB storage, multi-branch, audit logs).

### 5.4 Seed Demo Accounts

| Role | Email | Password Source | Scope |
|---|---|---|---|
| **Platform Owner** | `superadmin@arogyascribe.in` | Loaded from `SUPERADMIN_INITIAL_PASSWORD` in `.env` | Global SaaS Administration |
| **Org Admin** | `orgadmin@arogyacare.in` | Loaded from `DEMO_ORG_ADMIN_PASSWORD` in `.env` | Arogya Care Multi-Specialty Clinic |
| **Receptionist** | `reception@arogyacare.in` | Loaded from `DEMO_RECEPTIONIST_PASSWORD` in `.env` | Indiranagar Main Branch |
| **Doctor** | `dr.sharma@arogyacare.in` | Loaded from `DEMO_DOCTOR_PASSWORD` in `.env` | General Medicine (Indiranagar Main Branch) |

---

## 6. Testing & Code Quality

Run complete test suite (all 21 automated integration and unit tests covering tenant isolation, credential security, onboarding pipelines, and the complete 24-step clinical workflow):
```bash
pytest -v
```

Run specific test suites:
- **24-Step End-to-End Master Workflow:** `pytest tests/api/test_24_step_e2e_workflow.py -v`
- **SaaS Core, Multi-Tenancy & B2B Onboarding:** `pytest tests/api/test_phase1_saas_core.py -v`
- **Reception & Doctor Lifecycles:** `pytest tests/api/test_phase2_3_reception_doctor_workflow.py -v`
- **AI Pipeline, Medication Safety & Approval:** `pytest tests/api/test_phase4_5_clinical_ai_reports_e2e.py -v`
- **Core Security & Infrastructure:** `pytest tests/unit/test_core_infrastructure.py -v`

---

## 7. Backend Completion Summary

- **Phase 0:** Core infrastructure, security (Argon2id + JWT), database base, living docs, docker-compose.
- **Phase 1:** All 28 PostgreSQL tables, Alembic migrations, idempotent synthetic seeder, SaaS core auth & RBAC APIs.
- **Phase 2:** Reception engine, duplicate-safe patient registration, appointment finite state machine & queues.
- **Phase 3:** Doctor workspace, longitudinal patient history, mandatory consent capture & withdrawal.
- **Phase 4:** Private object storage, 5 pluggable AI contracts (Gnani Prisma/Evon/Timbre + Mocks), Gnani credit guardrail, Celery worker tasks, transcript review & grounded facts.
- **Phase 5:** Medication safety verification gate, dual-report versioning & superseding, doctor approval, Pan-India 9-language translation (hi, ta, te, kn, ml, mr, bn, gu), ReportLab PDF generation, WhatsApp/Email delivery.
- **Phase 6 & 7 Verification:** Contract alignment with frontend UI, 4-step B2B clinic onboarding pipeline, Super Admin credential lockdown, live plan quotas, and automated test suite.
- **Status: 100% Backend Complete & 100% Tested (21/21 pytest tests passing).**

