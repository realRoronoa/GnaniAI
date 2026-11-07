# ArogyaScribe — Frontend Architecture

React 18, TypeScript, Vite, and Tailwind CSS frontend for the **ArogyaScribe** clinical documentation platform.

---

## 1. Design System Tokens (Extracted from UI Reference Handoff)

**Brand Direction:** Mineral Sage + Deep Forest + Burnt Copper

```css
:root {
  /* Brand surfaces */
  --paper: #D7DCCF;       /* Page canvas / mineral sage */
  --paper-2: #C7CEBF;     /* Alternate section surface */
  --surface: #E9EDE3;     /* Card, dialog, and form surface */
  --surface-2: #DEE5D9;   /* Nested surface / table header */

  /* Brand identity */
  --ink: #172820;         /* Deepest forest / primary text */
  --ink-2: #263F33;       /* Forest surface */
  --brand: #263F33;

  /* Text and structure */
  --text: #1C2C23;
  --text-2: #4C5C51;      /* Readability contrast */
  --line: #AEBBAC;       /* Structural border only */

  /* Brand accents */
  --accent: #A84F38;      /* Burnt copper; marketing CTA & active borders */
  --accent-text: #954832; /* Darker copper for links/text */
  --accent-2: #C29A5B;    /* Antique brass; decorative/highlight */
  --hover: #954832;

  /* Semantic states */
  --ok: #326D4A;
  --approved: #326D4A;
  --warn: #78551C;
  --err: #A8433A;
  --rec: #A9362D;

  /* AI / clinical review states */
  --ai: #4D6578;
  --ai-bg: #E0E6E8;
  --approved-bg: #DDE9DC;
  --warn-bg: #F0E5CD;
  --rec-bg: #F1DFDB;
}
```

### Typography
- **Headings / Display:** `Fraunces`, `Bricolage Grotesque`, `Georgia`, `serif`
- **Body / Navigation / Controls:** `Instrument Sans`, `Figtree`, `system-ui`, `sans-serif`
- **Vernacular Hindi:** `Noto Sans Devanagari`, `Nirmala UI`, `sans-serif`

---

## 2. Directory Structure

```text
frontend/
├── src/
│   ├── components/            # Reusable core design components (Button, Modal, DataTable, Card, StatCard, StatusBadge)
│   │   ├── common/            # Design-matched reusable primitives
│   │   └── layout/            # AppLayout (Fixed 250px sidebar, 112px brand header, bottom user pill)
│   ├── features/              # Feature-driven modular domains
│   │   ├── auth/              # AuthContext, Token Refresh, LoginPage with 1-Click Quick Demo Role Fill
│   │   ├── public/            # Public Website Landing Page, Product Demo, Pricing, Lead Registration
│   │   ├── platform-admin/    # Platform Overview, Organizations Directory, Plans & Billing, Audit Log
│   │   ├── organizations/     # Org Overview & Entitlements Gauge, Branches, Staff Rosters, Shift Schedules
│   │   ├── reception/         # Daily check-in queue & patient triage (Phase B)
│   │   └── doctors/           # Doctor consultation workspace & dual report approval (Phase B)
│   ├── routes/                # ProtectedRoute (role-based) & AppRoutes
│   ├── services/              # api.ts (Axios client with bearer auth & 401 refresh interceptor)
│   ├── styles/                # index.css with CSS variables and texture
│   └── types/                 # TypeScript interfaces matching backend models
├── index.html                 # Google Fonts preconnect & entry HTML
├── vite.config.ts             # Vite dev server + /api proxy to FastAPI port 8000
├── tailwind.config.js         # Tailwind config matching exact design system tokens
└── tsconfig.json              # TypeScript compilation configuration
```

---

## 3. Implemented Screens & Features (Phase A)

### Public Website & Authentication
1. **Public Landing Page (`/`):**
   - Brand storytelling: *"The doctor talks. The doctor decides."*
   - Interactive 5-tab consultation pipeline demo (`Record`, `Transcript`, `Verify`, `Two reports`, `Approve`).
   - "Built for Staff" role showcase (Doctors, Receptionists, Org Admins).
   - Dynamic database-driven Pricing Section (`GET /api/v1/plans/public`): Starter (₹4,999/mo), Professional (₹14,999/mo), Enterprise (₹49,999/mo) with monthly/annual billing toggle.
   - Trust & Oversight human-in-the-loop explanation.
   - Integrated Organization Lead Registration Modal (`POST /api/v1/organizations/register`).
2. **Unified Sign-In (`/login`):**
   - Single entry login for all staff with automatic backend role detection.
   - **Quick Demo Role Fill Bar (Operational Roles Only):** 1-click test credentials for `Org Admin`, `Receptionist`, and `Doctor` (gated by `VITE_ENABLE_DEMO_BAR !== 'false'`).
   - **Platform Owner Private Credentials:** Super Admin credentials are not exposed on public auto-fill buttons and must be typed in manually.
   - Clear privacy notice: *There is no patient login.*

### Platform Owner Console (`/platform/*`)
1. **Overview (`/platform/overview`):**
   - 4 KPI stat tiles: Total Organizations, Active Subscriptions, Registered Doctors, Monthly Consultations.
   - Recently onboarded organizations table with status badges.
2. **Organizations Directory (`/platform/organizations`):**
   - Searchable table of tenant organizations.
   - **Pending Onboarding Inquiries Banner & Modal:** Live approval workflow for clinics that registered via the landing page, allowing custom pricing/coupon override, temporary password generation, and 1-click activation.
   - Onboard New Organization modal (`POST /api/v1/platform/organizations`).
   - Tenant status toggle (`ACTIVE` / `SUSPENDED`).
3. **Organization Detail (`/platform/organizations/:organizationId`):**
   - Organization metadata and privacy boundary notice.
4. **Plans & Billing (`/platform/plans`):**
   - Subscription plan cards with seat limits and consultation quotas.
   - **Platform Owner Pricing & Coupon Studio:** Live controls for prices, quotas, and promo coupon simulator (`PERCENTAGE`, `FLAT_INR`, `FIXED_OVERRIDE_INR`) with instant customer preview card and database persistence (`PATCH /api/v1/platform/plans/{plan_id}`).
   - Dev/Manual Subscription Activation modal (`POST /api/v1/platform/subscriptions/activate`).
5. **Audit Log (`/platform/audit-log`):**
   - Searchable audit events table displaying operational actions, timestamps, and roles.

### Organization Admin Console (`/org/*`)
1. **Clinic Overview (`/org/overview`):**
   - Real-time entitlement utilization progress bars for Doctors, Receptionists, Branches, and Consultations.
2. **Clinic Branches (`/org/branches`):**
   - Branch locations table and Add Branch modal (`POST /api/v1/org/branches`).
3. **Staff Roster (`/org/staff`):**
   - Tabbed roster for Doctors and Receptionists.
   - **Live Plan Quota Gauges:** Displays real-time allocation status (`Doctors: X / Y used`, `Reception: X / Y used`) and disables invite buttons when quotas are exhausted.
   - Add/Invite Doctor modal (`POST /api/v1/org/staff/doctors`).
   - Add/Invite Receptionist modal (`POST /api/v1/org/staff/receptionists`).
4. **Doctor Shift Schedules (`/org/schedules`):**
   - Weekly OPD consultation slots table and Add Shift modal (`POST /api/v1/org/schedules`).

### Receptionist Console (`/reception/*`)
1. **Overview & Live OPD Queue (`/reception/overview`, `/reception/queue`):**
   - KPI counters for total outpatient bookings, waiting patients, in-progress visits, and completed encounters.
   - Filterable patient queue with 1-click status transitions (`SCHEDULED` -> `CONFIRMED` -> `ARRIVED` -> `WAITING`).
   - 15-second background auto-polling.
2. **Patient Directory & Duplicate-Safe Registration (`/reception/patients`):**
   - Searchable directory of clinic patients with UHID, phone number, and gender badges.
   - Real-time pre-registration duplicate detection (`GET /api/v1/patients/check-duplicates`).
   - Non-blocking duplicate warning card allowing receptionists to explicitly confirm shared household numbers without merging patient identities.
   - Patient demographics editor.
3. **Outpatient Appointments (`/reception/appointments`):**
   - Appointment scheduler with patient selection, branch selection, doctor assignment, and appointment type (`SCHEDULED` vs `WALK_IN`).
   - Reassign Doctor modal updating active queue positions.
4. **Report Delivery Desk (`/reception/delivery`):**
   - Restricted delivery console showing only doctor-approved encounters.
   - One-click Patient Summary PDF download.
   - Direct WhatsApp message composer link (`https://wa.me/...`) and Email dispatch composer (`mailto:...`).
   - Manual share logging (`POST /api/v1/consultations/{id}/mark-shared`) recording reception audit trail.

### Doctor Clinical Workspace (`/doctor/*`)
1. **Doctor Daily Dashboard (`/doctor/dashboard`):**
   - Active consultation alert banner with instant "Resume Encounter" CTA.
   - Live waiting room queue displaying wait times, visit types, and 1-click "Start Visit" CTA.
   - Unapproved reports counter reminding doctors of pending sign-offs.
2. **Patient Profile & Longitudinal History (`/doctor/patients/:patientId`):**
   - Patient header with verified allergy alerts.
   - Chronological encounter timeline with previous diagnoses and chief complaints.
   - Explicitly marked **Historical Prescriptions** table labeled `HISTORICAL — Verify before continuing` to prevent confusion with active prescriptions.
3. **Distraction-Free 4-Stage Consultation Studio (`/doctor/consultations/:consultationId`):**
   - **Stage 1 (Consent & Recording):**
     - Mandatory informed consent checkbox and withdraw consent button.
     - Real browser microphone recording using `MediaRecorder` with WebM audio chunking and live seconds timer.
     - Unmistakable recording text banner: `RECORDING ACTIVE — MIC LIVE`.
     - 1-Click Synthetic Consultation Audio Fallback for machines without physical microphones.
   - **Stage 2 (Transcript & Provenance):**
     - Diarized bilingual (Hinglish/English) transcript viewer with inline audited doctor edits (`PUT .../transcript`).
     - Structured clinical facts categorized into Symptoms, Diagnoses, and Plan items, complete with transcript quotation citations and Accept/Reject review actions.
   - **Stage 3 (Medication Verification Gate):**
     - Safety review table flagging missing dosage, frequency, or duration.
     - Doctor medication verification modal (`PUT .../medications/{id}`).
     - Strict gate: Dual-report sign-off is non-bypassably blocked until all medications are verified.
   - **Stage 4 (Dual Reports & Sign-Off):**
     - Side-by-side tabs for Doctor Clinical SOAP Note and vernacular Hindi Patient Summary with voice narration prompt.
     - Editable report text areas; saving edits supersedes previously approved reports to a new `DOCTOR_EDITED_DRAFT` requiring re-approval.
     - Cryptographic sign-off button (`POST .../approve`) calculating SHA-256 hash and locking report to `APPROVED`.
     - Direct PDF download buttons and patient delivery links.

### Upcoming Roadmap (`/upcoming`)
- Showcase of all 8 planned V2 roadmap features badged `COMING SOON — PLANNED FOR FUTURE RELEASE`:
  1. Automated WhatsApp Bot (Twilio/Meta BSP)
  2. Integrated Multi-Language TTS Patient Narration
  3. ABDM M1, M2, M3 Milestones & Ayushman Bharat Health Account (ABHA)
  4. Real-Time Teleconsultation & Remote Scribing
  5. Multi-Clinic Group Super-Consoles
  6. Clinical Drug Interaction Engine (CDSS)
  7. Offline-First Mobile Companion PWA
  8. Voice-Activated Hands-Free Commands
- MVP vs V2 automation comparison table highlighting human-in-the-loop doctor governance.

---

## 4. Verification, Testing & Build
- **Automated Vitest Test Suite:**
  ```bash
  npm test
  ```
  Runs 6 end-to-end frontend interaction test suites (`src/__tests__/app_workflows.test.tsx`) covering:
  - Strict 4-role RBAC enforcement and unauthenticated redirect to `/login`
  - V2 Roadmap cards and `COMING SOON — PLANNED FOR FUTURE RELEASE` badges
  - Duplicate patient detection and family phone sharing
  - Mandatory informed consent gating for consultation audio capture
  - Medication safety guardrails and doctor verification blocking
  - Dual-report editors and cryptographic doctor approval flow
  **Status:** 6/6 tests passing (100%).

- **TypeScript Strict Compilation & Vite Bundle Build:**
  ```bash
  npm run build
  ```
  Runs `tsc && vite build`.
  **Status:** `dist/index.html`, `dist/assets/index-*.css`, `dist/assets/index-*.js` compiled cleanly with 0 TypeScript and 0 Vite errors.
