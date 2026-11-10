from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging
from typing import Any
import httpx

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.appointments import router as appointments_router
from app.api.v1.auth import router as auth_router
from app.api.v1.clinical_review import router as clinical_review_router
from app.api.v1.consultations import router as consultations_router
from app.api.v1.organizations import registration_router as org_registration_router, router as organizations_router
from app.api.v1.patients import router as patients_router
from app.api.v1.platform_admin import router as platform_admin_router
from app.api.v1.public_plans import router as public_plans_router
from app.api.v1.recording import router as recording_router
from app.api.v1.reports import router as reports_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine

logger = logging.getLogger("arogyascribe")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown events handler: auto-provisions schema and ensures essential plans."""
    Base.metadata.create_all(bind=engine)
    try:
        from scripts.seed_demo import seed_essentials
        seed_essentials()
    except Exception as e:
        logger.warning("Startup database initialization notice: %s", e)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="ArogyaScribe — B2B Healthcare SaaS Platform for AI-Assisted Clinical Documentation in India",
    lifespan=lifespan,
)

# Universal CORS Middleware configuration
origins = settings.allowed_origins if isinstance(settings.allowed_origins, list) else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != ["*"] else ["*"],
    allow_origin_regex=r"https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.middleware("http")
async def add_cors_headers_middleware(request: Request, call_next):
    """Guarantees CORS headers on every single response, including OPTIONS preflight and exceptions."""
    origin = request.headers.get("origin")
    if request.method == "OPTIONS":
        response = JSONResponse(content="OK", status_code=200)
    else:
        try:
            response = await call_next(request)
        except Exception as exc:
            logger.exception("Server processing error on %s %s: %s", request.method, request.url.path, exc)
            response = JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": f"Processing error: {exc}"},
            )

    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Vary"] = "Origin"

    return response


# Mount API Routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(public_plans_router, prefix="/api/v1")
app.include_router(platform_admin_router, prefix="/api/v1")
app.include_router(organizations_router, prefix="/api/v1")
app.include_router(org_registration_router, prefix="/api/v1")
app.include_router(patients_router, prefix="/api/v1")
app.include_router(appointments_router, prefix="/api/v1")
app.include_router(consultations_router, prefix="/api/v1")
app.include_router(recording_router, prefix="/api/v1")
app.include_router(clinical_review_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")


@app.get(
    "/api/v1/health",
    tags=["System"],
    summary="Health check & environment telemetry",
    status_code=status.HTTP_200_OK,
)
async def health_check() -> dict[str, Any]:
    """Returns the operational status, environment, and active integration modes."""
    eff_key = settings.get_effective_gnani_key()
    has_key = bool(eff_key)
    preview = (eff_key[:6] + "..." + eff_key[-4:]) if len(eff_key) > 10 else ("***" if eff_key else "NOT_SET")
    from app.integrations.ai.gnani_providers import get_ffmpeg_binary
    ffmpeg_bin = get_ffmpeg_binary()
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": "0.1.9",
        "build": "v0.1.9-resilient-audio-422-fix",
        "environment": settings.app_env,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ai_provider_mode": settings.AI_PROVIDER,
        "has_gnani_key": has_key,
        "gnani_key_preview": preview,
        "gnani_base_url": settings.gnani_base_url,
        "ffmpeg_binary": ffmpeg_bin,
        "payment_mode": settings.payment_mode,
        "database_connected": bool(engine),
    }


@app.get(
    "/api/v1/health/gnani-test",
    tags=["System"],
    summary="Live Gnani AI verification test (STT + TTS)",
    status_code=status.HTTP_200_OK,
)
@app.get(
    "/api/v1/health/ai-live-test",
    tags=["System"],
    summary="Live Gnani AI verification test (alias)",
    status_code=status.HTTP_200_OK,
)
async def gnani_live_diagnostic_test() -> dict[str, Any]:
    """Sends 1 test STT call (2-second WAV) and 1 test TTS call ('नमस्ते') to api.vachana.ai."""
    import time
    import uuid
    from app.integrations.ai.gnani_providers import generate_silence_wav

    effective_key = settings.get_effective_gnani_key()
    has_key = bool(effective_key)
    masked_key = (effective_key[:6] + "..." + effective_key[-4:]) if len(effective_key) > 10 else ("***" if effective_key else "NOT_SET")
    base_url = (getattr(settings, "gnani_base_url", None) or "https://api.vachana.ai").rstrip("/")
    stt_endpoint = f"{base_url}/stt/v3"
    tts_endpoint = f"{base_url}/api/v1/tts/inference"

    res_data: dict[str, Any] = {
        "gnani_api_key_detected": has_key,
        "key_preview": masked_key,
        "key_length": len(effective_key),
        "active_provider_mode": settings.AI_PROVIDER,
        "base_url": base_url,
        "stt": {
            "endpoint": stt_endpoint,
            "http_status_code": None,
            "latency_ms": None,
            "success": False,
            "response_body": None,
        },
        "tts": {
            "endpoint": tts_endpoint,
            "http_status_code": None,
            "latency_ms": None,
            "success": False,
            "response_bytes_len": None,
            "response_preview": None,
        },
        "all_checks_passed": False,
        "message": "",
    }

    if not has_key:
        res_data["message"] = "No active GNANI_API_KEY detected in environment variables. Set GNANI_API_KEY on Render."
        return res_data

    # 1. Test STT with 2-second valid WAV
    wav_bytes = generate_silence_wav(2.0)
    stt_headers = {
        "X-API-Key-ID": effective_key,
        "X-API-Request-ID": str(uuid.uuid4()),
    }
    stt_files = {"audio_file": ("diagnostic_silence.wav", wav_bytes, "audio/wav")}
    stt_data = {"language_code": "hi-IN"}

    t0 = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            stt_resp = await client.post(stt_endpoint, headers=stt_headers, files=stt_files, data=stt_data)
            stt_latency = round((time.perf_counter() - t0) * 1000, 2)
            res_data["stt"]["latency_ms"] = stt_latency
            res_data["stt"]["http_status_code"] = stt_resp.status_code
            try:
                res_data["stt"]["response_body"] = stt_resp.json()
            except Exception:
                res_data["stt"]["response_body"] = stt_resp.text[:300]
            res_data["stt"]["success"] = stt_resp.status_code == 200
    except Exception as exc:
        res_data["stt"]["latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
        res_data["stt"]["response_body"] = f"Connection failed: {exc}"

    # 2. Test TTS with "नमस्ते"
    tts_headers = {
        "Content-Type": "application/json",
        "X-API-Key-ID": effective_key,
    }
    tts_payload = {
        "text": "नमस्ते",
        "voice": "Nalini",
        "model": "timbre-v2.5",
        "language": "hi-IN",
        "speed": 1.0,
        "audio_config": {
            "sample_rate": 48000,
            "num_channels": 1,
            "sample_width": 2,
            "encoding": "linear_pcm",
            "container": "wav",
        },
    }

    t1 = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            tts_resp = await client.post(tts_endpoint, headers=tts_headers, json=tts_payload)
            tts_latency = round((time.perf_counter() - t1) * 1000, 2)
            res_data["tts"]["latency_ms"] = tts_latency
            res_data["tts"]["http_status_code"] = tts_resp.status_code
            res_data["tts"]["response_bytes_len"] = len(tts_resp.content)
            res_data["tts"]["success"] = tts_resp.status_code == 200
            if tts_resp.status_code >= 400:
                try:
                    res_data["tts"]["response_preview"] = tts_resp.json()
                except Exception:
                    res_data["tts"]["response_preview"] = tts_resp.text[:300]
            else:
                res_data["tts"]["response_preview"] = f"Received {len(tts_resp.content)} bytes audio/wav"
    except Exception as exc:
        res_data["tts"]["latency_ms"] = round((time.perf_counter() - t1) * 1000, 2)
        res_data["tts"]["response_preview"] = f"Connection failed: {exc}"

    res_data["all_checks_passed"] = bool(res_data["stt"]["success"] and res_data["tts"]["success"])
    res_data["message"] = (
        "Gnani STT & TTS live endpoints both verified successfully!"
        if res_data["all_checks_passed"]
        else f"STT HTTP {res_data['stt']['http_status_code']}, TTS HTTP {res_data['tts']['http_status_code']}"
    )

    return res_data


@app.post("/api/v1/health/wipe-all-data")
def wipe_database_endpoint() -> dict[str, Any]:
    """Maintenance endpoint: completely clears all tenant organizations, clinics, doctors,
    patients, and consultations. Leaves only SubscriptionPlans and SuperAdmin.
    """
    from scripts.seed_demo import wipe_all_tenant_data
    return wipe_all_tenant_data()


@app.post("/api/v1/health/wipe-all-consultations")
def wipe_all_consultations_endpoint() -> dict[str, Any]:
    """Maintenance endpoint: clears all consultations, audio, transcripts, facts,
    medications, and reports, while strictly preserving Organizations, Clinics, and User accounts.
    """
    from sqlalchemy import delete
    from app.db.session import SessionLocal
    from app.models.clinical_reports import (
        ClinicalFact,
        ClinicalFactEvidence,
        MedicationInstruction,
        PdfAsset,
        Report,
        ReportApproval,
        ReportVersion,
    )
    from app.models.consultations_audio import (
        AudioAsset,
        ConsentRecord,
        Consultation,
        TranscriptSegment,
        TranscriptVersion,
    )
    with SessionLocal() as db:
        db.execute(delete(PdfAsset))
        db.execute(delete(ReportApproval))
        db.execute(delete(ReportVersion))
        db.execute(delete(Report))
        db.execute(delete(MedicationInstruction))
        db.execute(delete(ClinicalFactEvidence))
        db.execute(delete(ClinicalFact))
        db.execute(delete(TranscriptSegment))
        db.execute(delete(TranscriptVersion))
        db.execute(delete(AudioAsset))
        db.execute(delete(ConsentRecord))
        db.execute(delete(Consultation))
        db.commit()
    return {"message": "All consultation encounters wiped clean. Doctor and Clinic accounts preserved."}


@app.get("/api/v1/health/db-status")
def database_status_endpoint() -> dict[str, Any]:
    """Diagnostic endpoint: returns tenant counts and user emails."""
    from sqlalchemy import select
    from app.db.session import SessionLocal
    from app.models.tenant import User, Organization
    from app.models.consultations_audio import Consultation
    with SessionLocal() as db:
        users = db.execute(select(User)).scalars().all()
        orgs = db.execute(select(Organization)).scalars().all()
        cons = db.execute(select(Consultation)).scalars().all()
        last_cons_info = None
        if cons:
            c = cons[-1]
            from app.models.consultations_audio import TranscriptVersion, TranscriptSegment
            from app.models.clinical_reports import ClinicalFact, MedicationInstruction, Report
            t_ver = db.execute(select(TranscriptVersion).where(TranscriptVersion.consultation_id == c.id)).scalars().first()
            segs = db.execute(select(TranscriptSegment).where(TranscriptSegment.consultation_id == c.id)).scalars().all() if t_ver else []
            facts = db.execute(select(ClinicalFact).where(ClinicalFact.consultation_id == c.id)).scalars().all()
            meds = db.execute(select(MedicationInstruction).where(MedicationInstruction.consultation_id == c.id)).scalars().all()
            reports = db.execute(select(Report).where(Report.consultation_id == c.id)).scalars().all()
            last_cons_info = {
                "id": str(c.id),
                "status": str(c.status),
                "chief_complaint": c.chief_complaint_summary,
                "transcript_full_text": t_ver.full_text if t_ver else None,
                "segments_count": len(segs),
                "segments": [{"speaker": s.speaker_label.value if hasattr(s.speaker_label, 'value') else str(s.speaker_label), "text": s.original_text} for s in segs],
                "facts_count": len(facts),
                "medications_count": len(meds),
                "medications": [m.medication_name for m in meds],
                "reports_count": len(reports),
            }
        return {
            "users_count": len(users),
            "users": [{"email": u.email, "full_name": u.full_name, "is_super_admin": u.is_super_admin} for u in users],
            "orgs_count": len(orgs),
            "orgs": [{"id": str(o.id), "name": o.name} for o in orgs],
            "consultations_count": len(cons),
            "last_consultation": last_cons_info,
        }


@app.post("/api/v1/health/seed-demo")
def seed_demo_endpoint() -> dict[str, Any]:
    """Provisions complete demo clinic, doctor, receptionist, patients, and ready consultations."""
    from scripts.seed_demo import seed
    seed()
    return {
        "status": "success",
        "message": "Demo clinic & doctor successfully provisioned.",
        "doctor_credentials": {
            "email": "dr.sharma@arogyacare.in",
            "password": "Doctor@123",
        },
        "admin_credentials": {
            "email": "owner@arogyacare.in",
            "password": "OrgAdmin@123",
        },
    }


@app.get("/", include_in_schema=False)
async def root_redirect() -> JSONResponse:
    return JSONResponse(
        content={
            "message": "Welcome to ArogyaScribe B2B Healthcare SaaS API",
            "docs_url": "/docs",
            "health_url": "/api/v1/health",
        }
    )
