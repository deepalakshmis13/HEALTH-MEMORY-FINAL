"""
Central configuration for the Elder Health Memory platform.

Every tunable constant lives here — most importantly the OCR confidence
thresholds that decide whether extracted medical data enters health memory
directly or is routed to the reviewer verification queue.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def _env(key: str, default: str) -> str:
    return os.environ.get(key, default)


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.environ.get(key, default))
    except (TypeError, ValueError):
        return default


# --------------------------------------------------------------------------
# Application
# --------------------------------------------------------------------------
APP_NAME = "AI-Agent-Powered Persistent Health Memory Layer for Elderly Patients"
APP_SHORT_NAME = "Elder Health Memory"
APP_VERSION = "1.0.0"

# --------------------------------------------------------------------------
# Database (MongoDB)
#
# Point MONGODB_URI at your deployment — a local server, a replica set or an
# Atlas cluster. Credentials belong in the environment, never in this file.
#   export MONGODB_URI="mongodb://localhost:27017"
#   export MONGODB_DB_NAME="health_memory"
# --------------------------------------------------------------------------
MONGODB_URI = _env("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME = _env("MONGODB_DB_NAME", "health_memory")
MONGODB_TIMEOUT_MS = int(_env("MONGODB_TIMEOUT_MS", "3000"))
# When the server is unreachable, fall back to a local MongoDB-compatible store
# so a fresh checkout still runs. Always set this to 0 in production.
MONGODB_FALLBACK_ENABLED = _env("MONGODB_LOCAL_FALLBACK", "1") not in {
    "0",
    "false",
    "False",
    "no",
}
MONGODB_LOCAL_PATH = Path(_env("MONGODB_LOCAL_PATH", str(BASE_DIR / ".mongo-local")))

STORAGE_DIR = Path(_env("STORAGE_DIR", str(BASE_DIR / "storage")))
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

CORS_ORIGINS = _env(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173",
).split(",")

# --------------------------------------------------------------------------
# Security
# --------------------------------------------------------------------------
SECRET_KEY = _env("SECRET_KEY", "dev-only-change-me-elder-health-memory")
TOKEN_TTL_SECONDS = int(_env("TOKEN_TTL_SECONDS", str(60 * 60 * 12)))
PASSWORD_HASH_ITERATIONS = 120_000

MAX_UPLOAD_BYTES = int(_env("MAX_UPLOAD_BYTES", str(15 * 1024 * 1024)))
ALLOWED_UPLOAD_EXTENSIONS = {
    ".pdf", ".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff",
    ".txt", ".doc", ".docx",
}

# --------------------------------------------------------------------------
# CONFIDENCE THRESHOLDS  (single source of truth — §12 of the spec)
# --------------------------------------------------------------------------
#   confidence >= HIGH_CONFIDENCE_THRESHOLD   -> auto-accept into health memory
#   MEDIUM <= confidence < HIGH               -> "Needs Verification"
#   confidence <  MEDIUM_CONFIDENCE_THRESHOLD -> "High Priority Verification"
HIGH_CONFIDENCE_THRESHOLD = _env_float("HIGH_CONFIDENCE_THRESHOLD", 0.85)
MEDIUM_CONFIDENCE_THRESHOLD = _env_float("MEDIUM_CONFIDENCE_THRESHOLD", 0.60)

# Fields considered clinically important. Only these create reviewer
# verification tasks when confidence falls below HIGH_CONFIDENCE_THRESHOLD.
CLINICALLY_IMPORTANT_FIELDS = {
    "medication_name",
    "medication_dose",
    "medication_frequency",
    "prescription_instruction",
    "medication_change",
    "allergy",
    "critical_instruction",
}

# --------------------------------------------------------------------------
# RAG
# --------------------------------------------------------------------------
RAG_CHUNK_SIZE = int(_env("RAG_CHUNK_SIZE", "480"))
RAG_CHUNK_OVERLAP = int(_env("RAG_CHUNK_OVERLAP", "60"))
RAG_TOP_K = int(_env("RAG_TOP_K", "8"))
RAG_RECENCY_HALFLIFE_DAYS = float(_env("RAG_RECENCY_HALFLIFE_DAYS", "120"))
EMBEDDING_DIM = int(_env("EMBEDDING_DIM", "256"))

# --------------------------------------------------------------------------
# AI provider
# --------------------------------------------------------------------------
AI_PROVIDER = _env("AI_PROVIDER", "auto")  # auto | mock | llm
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_API_URL = _env("LLM_API_URL", "https://api.anthropic.com/v1/messages")
LLM_MODEL = _env("LLM_MODEL", "claude-sonnet-4-5")

# --------------------------------------------------------------------------
# Shifts (§24 — configurable)
# --------------------------------------------------------------------------
SHIFT_DEFINITIONS = [
    {"id": "MORNING", "label": "Morning Shift", "start": "06:00", "end": "14:00"},
    {"id": "AFTERNOON", "label": "Afternoon Shift", "start": "14:00", "end": "22:00"},
    {"id": "NIGHT", "label": "Night Shift", "start": "22:00", "end": "06:00"},
]

# --------------------------------------------------------------------------
# Vocabulary (§15, §16, §35)
# --------------------------------------------------------------------------
SOURCE_TYPES = [
    "PATIENT_TEXT",
    "PATIENT_VOICE",
    "DOCTOR_DOCUMENT",
    "SCANNED_DOCUMENT",
    "HANDWRITTEN_DOCUMENT",
    "OCR",
    "DOCTOR_RECORDED",
    "CAREGIVER_RECORDED",
    "REVIEWER_VERIFIED",
    "AI_GENERATED",
]

TRUST_LEVELS = [
    "Patient Reported",
    "AI Extracted",
    "OCR Extracted",
    "Doctor Recorded",
    "Reviewer Verified",
    "Caregiver Recorded",
]

VERIFICATION_STATUSES = [
    "PENDING_VERIFICATION",
    "VERIFIED",
    "CORRECTED",
    "REJECTED",
    "NOT_REQUIRED",
]

CONSENT_SCOPES = [
    "FULL_HEALTH_MEMORY",
    "MEDICATION_INFORMATION",
    "EMERGENCY_INFORMATION",
    "RECENT_HISTORY",
    "CAREGIVER_NOTES",
    "DOCUMENTS",
    "VOICE_DIARY",
]

ROLES = ["patient", "doctor", "caregiver", "reviewer"]

# The verification role was renamed Pharmacist -> Reviewer. Sign-in addresses
# issued before the rename still resolve to the same account, so nobody is
# locked out by a terminology change. The password is still verified against
# that account's own hash — this maps an address, it does not grant access.
LEGACY_EMAIL_ALIASES = {
    "pharmacist@demo.health": "reviewer@demo.health",
}
