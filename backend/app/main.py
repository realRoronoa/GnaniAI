from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging
from typing import Any

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
    """Startup and shutdown events handler: auto-provisions schema, ensures essential plans, and cleans mock data."""
    Base.metadata.create_all(bind=engine)
    try:
        from scripts.seed_demo import seed_essentials, clean_mock_data
        seed_essentials()
        clean_mock_data()
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
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": "0.1.5",
        "build": "official-gnani-live",
        "environment": settings.app_env,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ai_provider_mode": settings.AI_PROVIDER,
        "has_gnani_key": has_key,
        "gnani_key_preview": preview,
        "gnani_base_url": settings.gnani_base_url,
        "payment_mode": settings.payment_mode,
        "database_connected": bool(engine),
    }


@app.get(
    "/api/v1/health/ai-live-test",
    tags=["System"],
    summary="Live Gnani AI verification test",
    status_code=status.HTTP_200_OK,
)
@app.get(
    "/api/v1/health/gnani-test",
    tags=["System"],
    summary="Live Gnani AI verification test (alias)",
    status_code=status.HTTP_200_OK,
)
async def gnani_live_diagnostic_test() -> dict[str, Any]:
    """Sends 1 lightweight verification request to the configured Gnani STT endpoint and returns live metrics."""
    import struct
    import time

    effective_key = settings.get_effective_gnani_key()
    has_key = bool(effective_key)
    masked_key = (effective_key[:6] + "..." + effective_key[-4:]) if len(effective_key) > 10 else ("***" if effective_key else "NOT_SET")
    base_url = (getattr(settings, "gnani_base_url", None) or "https://api.vachana.ai").rstrip("/")
    endpoint = f"{base_url}/stt/v3"

    res_data: dict[str, Any] = {
        "gnani_api_key_detected": has_key,
        "key_preview": masked_key,
        "key_length": len(effective_key),
        "active_provider_mode": settings.AI_PROVIDER,
        "base_url": base_url,
        "endpoint_called": endpoint,
        "http_status_code": None,
        "latency_ms": None,
        "sent_headers": {
            "X-API-Key-ID": masked_key,
            "X-API-Key": masked_key,
            "Authorization": f"Bearer {masked_key}",
        },
        "response_body": None,
        "live_connection_success": False,
        "message": "",
    }

    if not has_key:
        res_data["message"] = "No active GNANI_API_KEY detected in environment variables. Set GNANI_API_KEY on Render."
        return res_data

    # Generate minimal 0.1s 16kHz mono silence WAV (3,244 bytes)
    sample_rate = 16000
    num_samples = 1600
    data_size = num_samples * 2
    tiny_wav = (
        b"RIFF"
        + struct.pack("<I", 36 + data_size)
        + b"WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00"
        + struct.pack("<I", sample_rate)
        + struct.pack("<I", sample_rate * 2)
        + b"\x02\x00\x10\x00data"
        + struct.pack("<I", data_size)
        + (b"\x00" * data_size)
    )

    headers = {
        "X-API-Key-ID": effective_key,
        "X-API-Key": effective_key,
        "Authorization": f"Bearer {effective_key}",
        "Accept": "application/json",
    }
    files = {"audio_file": ("test_silence.wav", tiny_wav, "audio/wav")}
    data = {
        "model": "prisma-v3.0",
        "language_code": "indic-auto",
        "format": "transcribe",
    }

    t0 = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(endpoint, headers=headers, files=files, data=data)
            latency_ms = round((time.perf_counter() - t0) * 1000, 2)
            res_data["latency_ms"] = latency_ms
            res_data["http_status_code"] = response.status_code
            try:
                res_data["response_body"] = response.json()
            except Exception:
                res_data["response_body"] = response.text[:300]

            res_data["live_connection_success"] = response.status_code == 200
            res_data["message"] = (
                "Gnani STT API live verified successfully!"
                if response.status_code == 200
                else f"Gnani STT returned HTTP {response.status_code}"
            )
    except Exception as exc:
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        res_data["latency_ms"] = latency_ms
        res_data["message"] = f"Connection failed: {exc}"

    return res_data


@app.get("/", include_in_schema=False)
async def root_redirect() -> JSONResponse:
    return JSONResponse(
        content={
            "message": "Welcome to ArogyaScribe B2B Healthcare SaaS API",
            "docs_url": "/docs",
            "health_url": "/api/v1/health",
        }
    )
