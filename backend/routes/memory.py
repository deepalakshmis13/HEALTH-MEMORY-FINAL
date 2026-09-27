"""Health-memory timeline routes."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from database import Session

from auth import Principal, get_current_user
from database import get_db
from models import MemoryEvent
from rag import chunker
from schemas import MemoryEventCreate
from services import audit_service, memory_service
from services.authorization_service import require_patient_access
from utils.helpers import parse_date

router = APIRouter(prefix="/api/memory", tags=["health-memory"])


@router.get("/{patient_id}")
def get_memory(
    patient_id: int,
    event_types: Optional[str] = Query(None),
    source_types: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    days: Optional[int] = Query(None),
    limit: int = Query(200, le=500),
    principal: Principal = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    context = require_patient_access(db, principal, patient_id)
    events = memory_service.timeline(
        db, context,
        event_types=event_types.split(",") if event_types else None,
        source_types=source_types.split(",") if source_types else None,
        search=search,
        since=datetime.utcnow() - timedelta(days=days) if days else None,
        limit=limit,
    )
    return {
        "patient_id": patient_id,
        "events": events,
        "count": len(events),
        "access": context.as_dict(),
        "index": chunker.index_stats(db, patient_id),
    }


@router.get("/{patient_id}/timeline")
def get_timeline(
    patient_id: int,
    limit: int = Query(200, le=500),
    principal: Principal = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    context = require_patient_access(db, principal, patient_id)
    events = memory_service.timeline(db, context, limit=limit)
    grouped: dict = {}
    for event in events:
        key = (event["event_date"] or "")[:10]
        grouped.setdefault(key, []).append(event)
    return {
        "patient_id": patient_id,
        "groups": [
            {"date": date, "events": items} for date, items in sorted(
                grouped.items(), reverse=True
            )
        ],
        "count": len(events),
    }


@router.post("")
def create_memory(
    payload: MemoryEventCreate,
    principal: Principal = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    context = require_patient_access(db, principal, payload.patient_id)
    source_map = {
        "patient": "PATIENT_TEXT",
        "doctor": "DOCTOR_RECORDED",
        "caregiver": "CAREGIVER_RECORDED",
        "reviewer": "REVIEWER_VERIFIED",
    }
    event = memory_service.create_event(
        db, payload.patient_id,
        event_type=payload.event_type.upper(),
        title=payload.title,
        content=payload.content,
        source_type=source_map.get(principal.role, "PATIENT_TEXT"),
        event_date=parse_date(payload.event_date, datetime.utcnow()),
        author_role=principal.role,
        author_name=principal.name,
        author_user_id=principal.id,
        doctor_id=principal.profile_id if principal.role == "doctor" else None,
        confidence=1.0,
        severity=payload.severity or "normal",
        tags=payload.tags,
    )
    audit_service.log(
        db, "HEALTH_MEMORY_CREATE", principal, patient_id=payload.patient_id,
        target=f"memory_event:{event.id}", detail=payload.title,
    )
    return memory_service.serialize_event(db, event)


@router.get("/event/{event_id}")
def get_event(
    event_id: int,
    principal: Principal = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    event = db.query(MemoryEvent).filter(MemoryEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="No health memory available.")
    require_patient_access(db, principal, event.patient_id)
    return memory_service.serialize_event(db, event)
