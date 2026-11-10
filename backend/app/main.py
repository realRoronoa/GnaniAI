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
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": "0.1.4",
        "build": "telemetry-live",
        "environment": settings.app_env,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ai_provider_mode": settings.ai_provider_mode,
        "has_gnani_key": bool(settings.gnani_api_key and settings.gnani_api_key.strip() and not settings.gnani_api_key.startswith("YOUR_")),
        "gnani_key_preview": (settings.gnani_api_key[:6] + "..." + settings.gnani_api_key[-4:]) if (settings.gnani_api_key and len(settings.gnani_api_key) > 10) else ("SET_SHORT" if settings.gnani_api_key else "NOT_SET"),
        "gnani_base_url": settings.gnani_base_url,
        "payment_mode": settings.payment_mode,
        "database_connected": bool(engine),
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
