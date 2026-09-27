"""Voice Health Diary routes (§8)."""

from fastapi import APIRouter, Depends, HTTPException
from database import Session

from auth import Principal, get_current_user
from database import get_db
from models import VoiceEntry
from schemas import VoiceIngestionRequest
from services import ingestion_service
from services.authorization_service import require_patient_access
from utils.helpers import human_datetime, iso

router = APIRouter(prefix="/api/voice", tags=["voice"])


@router.post("/entry")
def add_voice_entry(
    payload: VoiceIngestionRequest,
    principal: Principal = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    context = require_patient_access(db, principal, payload.patient_id)
    return ingestion_service.ingest_voice(
        db, context.patient, payload.transcript, principal,
        duration_seconds=payload.duration_seconds,
        recognition_confidence=payload.recognition_confidence,
        audio_ref=payload.audio_ref,
    )


@router.get("/{patient_id}")
def list_voice_entries(
    patient_id: int,
    principal: Principal = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    context = require_patient_access(db, principal, patient_id)
    if principal.role == "caregiver" or (
        principal.role != "patient"
        and not ({"VOICE_DIARY", "FULL_HEALTH_MEMORY"} & context.scopes)
    ):
        raise HTTPException(
            status_code=403,
            detail="The voice diary has not been shared with your role.",
        )
    entries = (
        db.query(VoiceEntry)
        .filter(VoiceEntry.patient_id == patient_id)
        .order_by(VoiceEntry.recorded_at.desc())
        .all()
    )
    return {
        "patient_id": patient_id,
        "entries": [
            {
                "id": entry.id,
                "transcript": entry.transcript,
                "recorded_at": iso(entry.recorded_at),
                "recorded_at_label": human_datetime(entry.recorded_at),
                "duration_seconds": entry.duration_seconds,
                "confidence": entry.confidence,
                "source_type": entry.source_type,
                "entities": entry.extracted_entities or {},
                "memory_event_id": entry.memory_event_id,
            }
            for entry in entries
        ],
        "count": len(entries),
    }
