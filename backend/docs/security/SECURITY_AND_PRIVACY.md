# ArogyaScribe — Security & Privacy Architecture

## 1. Authentication & Cryptography

### 1.1 Password Hashing (Argon2id)
All user passwords are encrypted using **Argon2id**, the winner of the Password Hashing Competition (PHC) and recommended standard by OWASP for password hashing.
- **Algorithm:** Argon2id
- **Time Cost:** 3 iterations
- **Memory Cost:** 64 MB (65,536 KiB)
- **Parallelism:** 4 lanes/threads
- **Salt:** 16 cryptographically random bytes generated via OS CSPRNG (`os.urandom`)

### 1.2 JWT Token Architecture & Rotation
ArogyaScribe uses asymmetric or HMAC-SHA256 signed JSON Web Tokens with strict role and tenant binding.
- **Access Tokens:**
  - Lifetime: 15 minutes
  - Claims: `sub` (User UUID), `role` (`PLATFORM_OWNER` | `ORG_ADMIN` | `RECEPTIONIST` | `DOCTOR`), `org_id` (Organization UUID), `type` (`"access"`), `jti` (Token UUID), `exp`, `iat`.
- **Refresh Tokens:**
  - Lifetime: 7 days
  - Claims: `sub`, `type` (`"refresh"`), `jti`, `exp`, `iat`.
  - Stored hashed in Redis or invalidated upon logout / credential change. Single-use rotation enforces that using a refresh token generates a new token pair and invalidates the previous one.

---

## 2. Multi-Tenant Authorization & Isolation

Every request passing through authenticated endpoints is validated against the tenant boundary:
1. **Token Scope:** The JWT claims contain `org_id`.
2. **Repository Guard:** Database queries automatically append `WHERE organization_id = :org_id` on all multi-tenant tables (`patients`, `appointments`, `consultations`, `reports`, etc.).
3. **Cross-Tenant Prevention:** Attempting to access an asset belonging to another organization raises an immediate HTTP 403 Forbidden or 404 Not Found, preventing cross-tenant leakage.

---

## 3. Patient Data Privacy & Zero-Login Rule

1. **No Patient Credentials:** Patients do not create passwords or log in. This completely removes the attack surface associated with credential stuffing, SIM swapping, and weak patient authentication.
2. **Consent-Gated Processing:** Consultation recording cannot be uploaded or initiated unless a verified `consent_record` exists for that encounter. Uploading audio without consent is refused with HTTP 403.
3. **Sensitive Contact Handling:** Patient phone numbers used for WhatsApp summary dispatch are kept in client-side component memory during the send action and are never persisted to unnecessary analytics or log files.
4. **Ephemeral Sharing:** Remote links for patient summary viewing use tokenized, expiring `secure_share_grants` with single-visit or short-expiry constraints.

---

## 4. Protected Health Information (PHI) Storage

1. **Private S3 / MinIO Buckets:**
   - Bucket `arogyascribe-private` has public access completely blocked (`BlockPublicAcls`, `IgnorePublicAcls`, `BlockPublicPolicy`, `RestrictPublicBuckets`).
   - Objects are stored using AES-256 server-side encryption (`SSE-S3` or `SSE-KMS`).
2. **Pre-signed Access Only:**
   - Raw audio chunks and generated PDF reports are never served directly through public URLs.
   - Authorized clinicians access media strictly via time-limited (max 60 minutes) pre-signed S3 URLs generated on-demand after role verification.

---

## 5. Clinical Safety & AI Reliability Guardrails

1. **AI Output Tagging:** AI generated summaries and extracted clinical facts are explicitly styled with the purple `"AI DRAFT"` tag. They are never portrayed as finalized medical opinions.
2. **Incomplete Medication Blocker:**
   - Medications missing dose, frequency, or duration are automatically classified as `review_status = "unresolved"`.
   - The consultation report cannot be approved until all unresolved medication blockers are resolved (either completed with clinical details or explicitly rejected).
3. **Evidence Grounding Requirement:**
   - Extracted clinical facts must link to at least one valid transcript segment.
   - A fact lacking valid evidence cannot be accepted unless explicitly verified and edited by the doctor.
4. **Verbatim Clinician Wording:**
   - When a doctor types custom instructions or notes, the system preserves the doctor's exact wording without automated "normalization", "autocorrect", or translation that could alter clinical intent.

