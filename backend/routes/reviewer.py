"""Reviewer dashboard routes (§14, §15)."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from database import Session

from auth import Principal, require_roles
from database import get_db
from models import (
    Document,
    Medication,
    MemoryEvent,
    Patient,
    Prescription,
    VerificationTask,
)
from schemas import CorrectRequest, RejectRequest, VerifyRequest
from services import memory_service, verification_service
from services.authorization_service import require_patient_access
from utils.helpers import human_date, iso, percent

router = APIRouter(prefix="/api/reviewer", tags=["reviewer"])
verification_router = APIRouter(prefix="/api/verification", tags=["verification"])


def _load_task(db: Session, task_id: int) -> VerificationTask:
    task = db.query(VerificationTask).filter(VerificationTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Verification task not found.")
    return task


# --------------------------------------------------------------- queue
@verification_router.get("/queue")
def verification_queue(
    status: str = Query("PENDING_VERIFICATION"),
    patient_id: Optional[int] = Query(None),
    principal: Principal = Depends(require_roles("reviewer", "doctor")),
    db: Session = Depends(get_db),
):
    return {
        "queue": verification_service.queue(db, status, patient_id),
        "stats": verification_service.queue_stats(db),
        "status_filter": status,
    }


@verification_router.get("/{task_id}")
def verification_detail(
    task_id: int,
    principal: Principal = Depends(require_roles("reviewer", "doctor")),
    db: Session = Depends(get_db),
):
    task = _load_task(db, task_id)
    context = require_patient_access(db, principal, task.patient_id)
    payload = verification_service.serialize_task(db, task)

    overview = memory_service.overview(db, task.patient_id)
    payload["patient_context"] = {
        "medications": overview.get("medications", []),
        "allergies": overview.get("allergies", []),
        "conditions": overview.get("conditions", []),
        "access": context.as_dict(),
    }
    if task.memory_event_id:
        event = (
            db.query(MemoryEvent)
            .filter(MemoryEvent.id == task.memory_event_id)
            .first()
        )
        payload["memory_event"] = (
            memory_service.serialize_event(db, event) if event else None
        )
    return payload


@verification_router.post("/{task_id}/verify")
def verify_task(
    task_id: int,
    payload: VerifyRequest,
    principal: Principal = Depends(require_roles("reviewer")),
    db: Session = Depends(get_db),
):
    task = _load_task(db, task_id)
    require_patient_access(db, principal, task.patient_id)
    if task.status != "PENDING_VERIFICATION":
        raise HTTPException(
            status_code=409, detail="This item has already been reviewed."
        )
    return verification_service.verify(db, task, principal.profile, principal, payload.note)


@verification_router.post("/{task_id}/correct")
def correct_task(
    task_id: int,
    payload: CorrectRequest,
    principal: Principal = Depends(require_roles("reviewer")),
    db: Session = Depends(get_db),
):
    task = _load_task(db, task_id)
    require_patient_access(db, principal, task.patient_id)
    if task.status != "PENDING_VERIFICATION":
        raise HTTPException(
            status_code=409, detail="This item has already been reviewed."
        )
    if not payload.corrected_value.strip():
        raise HTTPException(status_code=400, detail="A corrected value is required.")
    return verification_service.correct(
        db, task, principal.profile, principal,
        payload.corrected_value.strip(), payload.clarification,
    )


@verification_router.post("/{task_id}/reject")
def reject_task(
    task_id: int,
    payload: RejectRequest,
    principal: Principal = Depends(require_roles("reviewer")),
    db: Session = Depends(get_db),
):
    task = _load_task(db, task_id)
    require_patient_access(db, principal, task.patient_id)
    if task.status != "PENDING_VERIFICATION":
        raise HTTPException(
            status_code=409, detail="This item has already been reviewed."
        )
    return verification_service.reject(
        db, task, principal.profile, principal, payload.reason
    )


# --------------------------------------------------------------- reviewer views
@router.get("/queue")
def reviewer_queue(
    status: str = Query("PENDING_VERIFICATION"),
    principal: Principal = Depends(require_roles("reviewer")),
    db: Session = Depends(get_db),
):
    return {
        "queue": verification_service.queue(db, status),
        "stats": verification_service.queue_stats(db),
    }


@router.get("/medications/{patient_id}")
def patient_medications(
    patient_id: int,
    principal: Principal = Depends(require_roles("reviewer")),
    db: Session = Depends(get_db),
):
    context = require_patient_access(db, principal, patient_id)
    if not ({"MEDICATION_INFORMATION", "FULL_HEALTH_MEMORY"} & context.scopes):
        raise HTTPException(
            status_code=403,
            detail="Medication information has not been shared with reviewers.",
        )
    medications = (
        db.query(Medication)
        .filter(Medication.patient_id == patient_id)
        .order_by(Medication.status, Medication.name)
        .all()
    )
    prescriptions = (
        db.query(Prescription)
        .filter(Prescription.patient_id == patient_id)
        .order_by(Prescription.issued_on.desc())
        .all()
    )
    history = (
        db.query(MemoryEvent)
        .filter(
            MemoryEvent.patient_id == patient_id,
            MemoryEvent.event_type.in_(
                ["MEDICATION", "MEDICATION_CHANGE", "MEDICATION_ADMINISTRATION"]
            ),
        )
        .order_by(MemoryEvent.event_date.desc())
        .limit(60)
        .all()
    )
    patient = context.patient
    return {
        "patient": {
            "id": patient.id,
            "full_name": patient.full_name,
            "age": patient.age,
            "blood_group": patient.blood_group,
        },
        "medications": [
            {
                "id": m.id, "name": m.name, "dose": m.dose, "frequency": m.frequency,
                "instruction": m.instruction, "status": m.status,
                "started_on": iso(m.started_on), "stopped_on": iso(m.stopped_on),
                "source_type": m.source_type, "confidence": m.confidence,
                "confidence_percent": percent(m.confidence),
                "verification_status": m.verification_status,
                "prescriber": m.prescriber.full_name if m.prescriber else None,
            }
            for m in medications
        ],
        "prescriptions": [
            {
                "id": p.id, "issued_on": iso(p.issued_on),
                "issued_on_label": human_date(p.issued_on),
                "items": p.items or [], "instruction": p.instruction,
                "source_type": p.source_type,
                "verification_status": p.verification_status,
                "document_id": p.document_id,
            }
            for p in prescriptions
        ],
        "medication_history": [
            memory_service.serialize_event(db, event) for event in history
        ],
        "access": context.as_dict(),
    }


@router.get("/insights")
def medication_insights(
    principal: Principal = Depends(require_roles("reviewer")),
    db: Session = Depends(get_db),
):
    stats = verification_service.queue_stats(db)
    tasks = db.query(VerificationTask).all()
    by_field: dict = {}
    for task in tasks:
        by_field[task.field_label] = by_field.get(task.field_label, 0) + 1

    handwritten = db.query(Document).filter(Document.is_handwritten.is_(True)).all()
    printed = db.query(Document).filter(Document.is_handwritten.is_(False)).all()

    def mean(values):
        values = [v for v in values if v is not None]
        return round(sum(values) / len(values), 4) if values else None

    pending = [t for t in tasks if t.status == "PENDING_VERIFICATION"]
    corrected = [t for t in tasks if t.status == "CORRECTED"]

    return {
        "stats": stats,
        "tasks_by_field": by_field,
        "average_confidence": {
            "handwritten_documents": mean([d.confidence for d in handwritten]),
            "printed_documents": mean([d.confidence for d in printed]),
            "flagged_fields": mean([t.confidence for t in tasks]),
        },
        "document_counts": {
            "handwritten": len(handwritten),
            "printed": len(printed),
        },
        "correction_rate": (
            round(len(corrected) / len(tasks), 3) if tasks else None
        ),
        "oldest_pending": (
            iso(min(pending, key=lambda t: t.created_at).created_at)
            if pending else None
        ),
        "patients_with_pending": sorted(
            {task.patient_id for task in pending}
        ),
    }


@router.get("/patients")
def reviewer_patients(
    principal: Principal = Depends(require_roles("reviewer")),
    db: Session = Depends(get_db),
):
    from services.authorization_service import accessible_patient_ids

    ids = accessible_patient_ids(db, principal)
    patients = db.query(Patient).filter(Patient.id.in_(ids)).all() if ids else []
    pending = {
        row.patient_id
        for row in db.query(VerificationTask).filter(
            VerificationTask.status == "PENDING_VERIFICATION"
        )
    }
    return {
        "patients": [
            {
                "id": patient.id,
                "full_name": patient.full_name,
                "age": patient.age,
                "has_pending_verification": patient.id in pending,
            }
            for patient in patients
        ]
    }
