"""Doctor dashboard routes (§18, §29)."""

from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from database import Session

from auth import Principal, require_roles
from database import get_db
from models import (
    CaregiverObservation,
    DoctorAssignment,
    MemoryEvent,
    Patient,
    VisitSummary,
)
from schemas import SaveVisitSummaryRequest, VisitSummaryRequest
from services import memory_service, summarization_service
from services.authorization_service import (
    accessible_patient_ids,
    require_patient_access,
)
from utils.helpers import human_date, iso

router = APIRouter(prefix="/api/doctor", tags=["doctor"])


@router.get("/routing")
def routing_feed(
    principal: Principal = Depends(require_roles("doctor")),
    db: Session = Depends(get_db),
):
    """§18 — new health-memory updates routed to this doctor."""
    assignments = (
        db.query(DoctorAssignment)
        .filter(
            DoctorAssignment.doctor_id == principal.profile_id,
            DoctorAssignment.status == "ACTIVE",
        )
        .order_by(DoctorAssignment.created_at.desc())
        .all()
    )
    feed = []
    for assignment in assignments:
        patient = db.query(Patient).filter(Patient.id == assignment.patient_id).first()
        if not patient:
            continue
        context = None
        try:
            context = require_patient_access(db, principal, patient.id)
        except HTTPException:
            continue
        events = (
            db.query(MemoryEvent)
            .filter(
                MemoryEvent.patient_id == patient.id,
                MemoryEvent.doctor_id == principal.profile_id,
            )
            .order_by(MemoryEvent.event_date.desc())
            .limit(4)
            .all()
        )
        feed.append(
            {
                "patient_id": patient.id,
                "patient_name": patient.full_name,
                "relationship": assignment.relationship_type,
                "routed_from_document_id": assignment.routed_from_document_id,
                "routed_at": iso(assignment.created_at),
                "consent": "Granted" if context.scopes else "Not granted",
                "source_confidence": max(
                    [e.confidence or 0 for e in events], default=None
                ),
                "updates": [
                    {
                        "id": event.id,
                        "title": event.title,
                        "event_type": event.event_type,
                        "date": human_date(event.event_date),
                        "source_type": event.source_type,
                        "trust_level": event.trust_level,
                        "confidence": event.confidence,
                        "verification_status": event.verification_status,
                        "document_id": event.document_id,
                    }
                    for event in events
                ],
            }
        )
    return {"routed": feed, "count": len(feed)}


@router.get("/insights/{patient_id}")
def clinical_insights(
    patient_id: int,
    principal: Principal = Depends(require_roles("doctor")),
    db: Session = Depends(get_db),
):
    context = require_patient_access(db, principal, patient_id)
    overview = memory_service.overview(db, patient_id)

    window = datetime.utcnow() - timedelta(days=90)
    events = (
        db.query(MemoryEvent)
        .filter(
            MemoryEvent.patient_id == patient_id, MemoryEvent.event_date >= window
        )
        .all()
    )
    by_type: dict = {}
    by_source: dict = {}
    for event in events:
        by_type[event.event_type] = by_type.get(event.event_type, 0) + 1
        by_source[event.trust_level] = by_source.get(event.trust_level, 0) + 1

    symptom_events = [e for e in events if e.event_type == "SYMPTOM"]
    symptom_counts: dict = {}
    for event in symptom_events:
        key = event.title.replace("Reported symptom: ", "")
        symptom_counts[key] = symptom_counts.get(key, 0) + 1

    return {
        "patient_id": patient_id,
        "window_days": 90,
        "activity_by_type": by_type,
        "activity_by_trust_level": by_source,
        "recurring_symptoms": sorted(
            [{"symptom": k, "count": v} for k, v in symptom_counts.items()],
            key=lambda item: item["count"], reverse=True,
        )[:6],
        "alerts": overview.get("alerts", []),
        "medication_count": len(overview.get("medications", [])),
        "pending_verification": overview["counts"]["pending_verification"],
        "unverified_medications": [
            m for m in overview.get("medications", [])
            if m.get("verification_status") == "PENDING_VERIFICATION"
        ],
        "access": context.as_dict(),
    }


@router.get("/caregiver-feed/{patient_id}")
def caregiver_feed(
    patient_id: int,
    principal: Principal = Depends(require_roles("doctor")),
    db: Session = Depends(get_db),
):
    context = require_patient_access(db, principal, patient_id)
    if not ({"CAREGIVER_NOTES", "FULL_HEALTH_MEMORY"} & context.scopes):
        raise HTTPException(
            status_code=403,
            detail="Caregiver notes have not been shared for this patient.",
        )
    observations = (
        db.query(CaregiverObservation)
        .filter(CaregiverObservation.patient_id == patient_id)
        .order_by(CaregiverObservation.observed_at.desc())
        .limit(40)
        .all()
    )
    return {
        "patient_id": patient_id,
        "observations": [
            {
                "id": observation.id,
                "category": observation.category,
                "observation": observation.observation,
                "severity": observation.severity,
                "observed_at": iso(observation.observed_at),
                "observed_at_label": human_date(observation.observed_at),
                "source": "Caregiver Recorded",
            }
            for observation in observations
        ],
        "count": len(observations),
    }


@router.post("/visit-summary")
def visit_summary(
    payload: VisitSummaryRequest,
    principal: Principal = Depends(require_roles("doctor")),
    db: Session = Depends(get_db),
):
    return summarization_service.generate_visit_summary(
        db, principal, payload.patient_id
    )


@router.post("/visit-summary/save")
def save_summary(
    payload: SaveVisitSummaryRequest,
    principal: Principal = Depends(require_roles("doctor")),
    db: Session = Depends(get_db),
):
    summary = summarization_service.save_visit_summary(
        db, principal, payload.summary_id, payload.content
    )
    if not summary:
        raise HTTPException(status_code=404, detail="Visit summary not found.")
    return {
        "summary_id": summary.id,
        "status": summary.status,
        "saved_at": iso(summary.saved_at),
        "message": "Visit summary saved to the patient's health memory.",
    }


@router.get("/visit-summaries/{patient_id}")
def list_summaries(
    patient_id: int,
    principal: Principal = Depends(require_roles("doctor")),
    db: Session = Depends(get_db),
):
    require_patient_access(db, principal, patient_id)
    summaries = (
        db.query(VisitSummary)
        .filter(VisitSummary.patient_id == patient_id)
        .order_by(VisitSummary.generated_at.desc())
        .limit(20)
        .all()
    )
    return {
        "patient_id": patient_id,
        "summaries": [
            {
                "id": summary.id,
                "status": summary.status,
                "content": summary.content,
                "generated_at": iso(summary.generated_at),
                "saved_at": iso(summary.saved_at),
                "sources": summary.sources or [],
                "is_ai_generated": summary.is_ai_generated,
            }
            for summary in summaries
        ],
    }
