# ArogyaScribe — Architecture Decision Records (ADRs)

## ADR 0001: Independent Monorepo Layout with Decoupled Git Repositories
- **Context:** ArogyaScribe comprises a React frontend and a FastAPI backend. Managing them as tightly coupled git submodules creates friction in CI/CD, while a single git root creates deployment entanglement.
- **Decision:** Use a single filesystem root with two independent Git repositories (`frontend/.git` and `backend/.git`). Root contains only master documentation (`START_HERE.md`).
- **Consequence:** Teams can independently tag, branch, version, and deploy backend and frontend without merge conflicts or shared history bloat.

---

## ADR 0002: B2B SaaS Multi-Tenancy Hierarchy & 4 Roles Only (Zero Patient Login)
- **Context:** Clinic patients in Indian outpatient settings have varying digital literacy, rarely download portals, and cannot be burdened with passwords and OTP sign-ins for simple visit summaries.
- **Decision:** Strict 4-role system: `PLATFORM_OWNER`, `ORG_ADMIN`, `RECEPTIONIST`, and `DOCTOR`. Patients are modeled purely as clinical/administrative records with zero credentials or login endpoints. Patient summaries are shared securely via ephemeral WhatsApp links or printouts.
- **Consequence:** Zero patient authentication attack surface, HIPAA/DISHA data minimization compliance, and frictionless clinical reception operations.

---

## ADR 0003: PostgreSQL 16 with UUID Primary Keys & TimestampUUIDMixin
- **Context:** Auto-incrementing integer IDs leak volume and business intelligence (e.g., total patient count, total revenue) and cause collisions in distributed databases.
- **Decision:** All tables use UUID v4 identifiers and standard `created_at` and `updated_at` timezone-aware timestamps.
- **Consequence:** Completely opaque identifiers, safe distributed shard keys, and audit-ready temporal tracking.

---

## ADR 0004: Pluggable AI Adapters: Local Mock vs. Gnani AI Pipeline
- **Context:** Developers and automated CI systems need instant test passes without incurring API credit costs or handling flaky remote network dependencies. Production requires high-accuracy Indian multi-lingual STT/TTS.
- **Decision:** Build deterministic mock adapters enabled by default (`AI_PROVIDER_MODE="mock"`), alongside production Gnani AI adapters (`Prisma v2.5` STT, `Evon v3.3` Clinical LLM, and `Timbre v2.5` TTS).
- **Consequence:** Complete offline testability, zero mock leaks in production, and seamless provider switching via environment configuration.

---

## ADR 0005: Dual-Report Immutable Versioning with Cryptographic SHA-256
- **Context:** Clinical notes must be legally defensible. A doctor editing a report must never silently overwrite previous signed copies, and approvals must be tamper-evident.
- **Decision:** Every report revision generates a new `ReportVersion` with a computed `content_sha256`. Approval requires submitting the exact expected hash; if the draft was edited concurrently, approval fails with a 409 conflict. Approved reports are immutable; edits spawn version `v+1`.
- **Consequence:** Non-repudiation, bulletproof audit trails, and elimination of race conditions.

---

## ADR 0006: Asynchronous Task Processing with Celery & Redis
- **Context:** Audio chunking, speech-to-text, LLM extraction, and speech synthesis require seconds of compute time and must not block FastAPI HTTP request threads.
- **Decision:** Offload audio processing and AI pipelines to Celery workers backed by Redis 7. For single-process development demos, FastAPI `BackgroundTasks` provide a lightweight alternative.
- **Consequence:** Resilient worker horizontal scaling, predictable API response latencies, and guaranteed pipeline retry semantics.

---

## ADR 0007: Private Object Storage via MinIO/S3 with Pre-signed URLs
- **Context:** Patient consultation audio and generated clinical PDFs must never be publicly accessible over unauthenticated HTTP URLs.
- **Decision:** All audio assets and generated PDFs are stored in private buckets (`arogyascribe-private`). Read access is mediated via short-lived (60-minute) pre-signed URLs generated strictly after tenant-authorized requests.
- **Consequence:** Complete confidentiality of protected health information (PHI) at rest and in transit.

