from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, status
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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown events handler: auto-provisions schema, ensures essential plans, and purges mock clinics."""
    Base.metadata.create_all(bind=engine)
    try:
        from scripts.seed_demo import seed_essentials, clean_mock_data
        seed_essentials()
        clean_mock_data()
    except Exception as e:
        print(f"Startup database initialization notice: {e}")
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="ArogyaScribe — B2B Healthcare SaaS Platform for AI-Assisted Clinical Documentation in India",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins if isinstance(settings.allowed_origins, list) else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        "version": "0.1.0",
        "environment": settings.app_env,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ai_provider_mode": settings.ai_provider_mode,
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

