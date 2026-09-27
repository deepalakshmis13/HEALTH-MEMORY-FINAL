"""
FastAPI application entry point.

    uvicorn main:app --reload
"""

import logging
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from database import Session

from agents import ai_provider
from auth import Principal, get_current_user, require_roles
from config import (
    APP_NAME,
    APP_SHORT_NAME,
    APP_VERSION,
    CLINICALLY_IMPORTANT_FIELDS,
    CONSENT_SCOPES,
    CORS_ORIGINS,
    HIGH_CONFIDENCE_THRESHOLD,
    MEDIUM_CONFIDENCE_THRESHOLD,
    SHIFT_DEFINITIONS,
    SOURCE_TYPES,
    TRUST_LEVELS,
    VERIFICATION_STATUSES,
)
from database import (
    get_db,
    init_db,
    is_seeded,
    store_counts,
    store_description,
)
from ocr.ocr_service import ocr_service
from rag import chunker
from routes import (
    auth as auth_routes,
    care_team,
    caregiver,
    chatbot,
    consent,
    documents,
    doctor,
    emergency,
    ingestion,
    memory,
    ocr as ocr_routes,
    patients,
    reviewer,
    voice,
)
from services import audit_service
from utils.helpers import iso

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("elder-health-memory")

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=(
        "A persistent, longitudinal, consent-aware, provenance-preserving "
        "health-memory layer for elderly patients."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in CORS_ORIGINS if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()
    logger.info("%s v%s ready", APP_SHORT_NAME, APP_VERSION)

    store = store_description()
    logger.info("Database: %s (%s)", store["store"], store["detail"])

    # An unseeded database is indistinguishable from a broken one in the UI —
    # every dashboard simply looks empty. Say which it is, once, at startup.
    if not is_seeded():
        logger.warning(
            "\n"
            "==========================================================================\n"
            "  THE DATABASE IS EMPTY — no users, so no one can sign in.\n"
            "  Every dashboard will load and show nothing.\n"
            "\n"
            "  Create the demo environment:      python seed.py\n"
            "  Or import a legacy SQLite build:  python migrate_sqlite_to_mongo.py\n"
            "\n"
            "  Store in use: %s (%s)\n"
            "%s"
            "==========================================================================",
            store["store"], store["detail"],
            ""
            if store["persistent"]
            else "  This store is PROCESS-LOCAL: seeding from another terminal will not\n"
                 "  reach this server. Install 'montydb', or set MONGODB_URI.\n",
        )
    else:
        counts = store_counts()
        logger.info(
            "Demo data present: %s user(s), %s patient(s), %s memory event(s)",
            counts["users"], counts["patients"], counts["memory_events"],
        )

    logger.info("OCR engines: %s", ocr_service.engines)
    logger.info("AI provider: %s", ai_provider.provider_status()["provider"])


# --------------------------------------------------------------------------
# Friendly errors — never leak a raw backend exception (§48)
# --------------------------------------------------------------------------
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "path": request.url.path},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "detail": (
                "Something went wrong while processing that request. "
                "Please try again."
            ),
            "path": request.url.path,
        },
    )


# --------------------------------------------------------------------------
app.include_router(auth_routes.router)
app.include_router(patients.router)
app.include_router(care_team.router)
app.include_router(memory.router)
app.include_router(ingestion.router)
app.include_router(documents.router)
app.include_router(ocr_routes.router)
app.include_router(consent.router)
app.include_router(emergency.router)
app.include_router(voice.router)
app.include_router(doctor.router)
app.include_router(caregiver.router)
app.include_router(reviewer.router)
app.include_router(reviewer.verification_router)
app.include_router(chatbot.router)


@app.get("/")
def root():
    return {
        "app": APP_NAME,
        "version": APP_VERSION,
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    return {
        "status": "ok",
        "app": APP_SHORT_NAME,
        "version": APP_VERSION,
        "ocr_engines": ocr_service.engines,
        "ai_provider": ai_provider.provider_status(),
        "rag_index": chunker.index_stats(db),
        "database": {
            **store_description(),
            "seeded": is_seeded(),
            "counts": store_counts(),
        },
    }


@app.get("/api/system/config")
def system_config():
    """The vocabulary and thresholds the UI renders — one source of truth."""
    return {
        "app": APP_NAME,
        "version": APP_VERSION,
        "thresholds": {
            "high_confidence": HIGH_CONFIDENCE_THRESHOLD,
            "medium_confidence": MEDIUM_CONFIDENCE_THRESHOLD,
        },
        "clinically_important_fields": sorted(CLINICALLY_IMPORTANT_FIELDS),
        "source_types": SOURCE_TYPES,
        "trust_levels": TRUST_LEVELS,
        "verification_statuses": VERIFICATION_STATUSES,
        "consent_scopes": CONSENT_SCOPES,
        "shifts": SHIFT_DEFINITIONS,
        "ocr_engines": ocr_service.engines,
        "ai_provider": ai_provider.provider_status(),
    }


@app.get("/api/audit")
def audit_log(
    patient_id: Optional[int] = Query(None),
    limit: int = Query(100, le=500),
    principal: Principal = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if principal.role == "patient":
        patient_id = principal.patient_id
    events = audit_service.recent(db, limit=limit, patient_id=patient_id)
    return {
        "events": [
            {
                "id": event.id,
                "action": event.action,
                "actor_name": event.actor_name,
                "actor_role": event.actor_role,
                "patient_id": event.patient_id,
                "target": event.target,
                "detail": event.detail,
                "created_at": iso(event.created_at),
            }
            for event in events
        ],
        "count": len(events),
    }
