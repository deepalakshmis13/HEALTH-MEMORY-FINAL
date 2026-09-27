"""
Reviewer verification workflow (§13–§16).

Tasks are created only where the routing rule says they should be, and a
verification never destroys the original: the OCR text, the original
confidence, the correction, the reviewer and the timestamp are all kept.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from database import Session

from ocr import confidence as conf
from models import (
    Allergy,
    Document,
    Medication,
    MemoryEvent,
    OCRResult,
    Patient,
    Reviewer,
    VerificationResult,
    VerificationTask,
)
from services import audit_service, memory_service
from utils.helpers import human_datetime, iso, percent

FIELD_TO_MEDICATION_ATTR = {
    "medication_name": "name",
    "medication_dose": "dose",
    "medication_frequency": "frequency",
    "prescription_instruction": "instruction",
}


# ---------------------------------------------------------------------------
def create_tasks(
    db: Session,
    patient_id: int,
    fields: List[Dict[str, Any]],
    document: Optional[Document] = None,
    ocr_result: Optional[OCRResult] = None,
    memory_event: Optional[MemoryEvent] = None,
    commit: bool = True,
) -> List[VerificationTask]:
    """Apply the §13 rule and create only the tasks that qualify."""
    created: List[VerificationTask] = []
    for field in fields:
        if not field.get("needs_verification"):
            continue
        task = VerificationTask(
            patient_id=patient_id,
            document_id=getattr(document, "id", None),
            ocr_result_id=getattr(ocr_result, "id", None),
            memory_event_id=getattr(memory_event, "id", None),
            field_key=field["field"],
            field_label=field["label"],
            extracted_value=field.get("value"),
            confidence=field.get("confidence"),
            priority=field.get("priority", "NORMAL"),
            status="PENDING_VERIFICATION",
            reason=(
                f"{field['label']} extracted at {percent(field.get('confidence'))} "
                f"— below the {int(conf.HIGH_CONFIDENCE_THRESHOLD * 100)}% "
                f"auto-accept threshold and clinically important."
            ),
        )
        db.add(task)
        created.append(task)
    if created:
        db.flush()
    if commit:
        db.commit()
    return created


# ---------------------------------------------------------------------------
def serialize_task(db: Session, task: VerificationTask) -> Dict[str, Any]:
    patient = db.query(Patient).filter(Patient.id == task.patient_id).first()
    document = (
        db.query(Document).filter(Document.id == task.document_id).first()
        if task.document_id
        else None
    )
    ocr = (
        db.query(OCRResult).filter(OCRResult.id == task.ocr_result_id).first()
        if task.ocr_result_id
        else None
    )
    result = task.result
    return {
        "id": task.id,
        "patient_id": task.patient_id,
        "patient_name": patient.full_name if patient else "Unknown patient",
        "patient_age": patient.age if patient else None,
        "document_id": task.document_id,
        "document_name": document.filename if document else None,
        "document_type": document.document_type if document else None,
        "is_handwritten": document.is_handwritten if document else False,
        "field_key": task.field_key,
        "field_label": task.field_label,
        "extracted_value": task.extracted_value,
        "confidence": task.confidence,
        "confidence_percent": percent(task.confidence),
        "band": conf.band(task.confidence or 0),
        "priority": task.priority,
        "status": task.status,
        "reason": task.reason,
        "created_at": iso(task.created_at),
        "ocr_raw_text": ocr.raw_text if ocr else None,
        "ocr_engine": ocr.engine if ocr else None,
        "ocr_fields": (ocr.fields or []) if ocr else [],
        "memory_event_id": task.memory_event_id,
        "result": (
            {
                "action": result.action,
                "original_value": result.original_value,
                "original_confidence": result.original_confidence,
                "original_confidence_percent": percent(result.original_confidence),
                "corrected_value": result.corrected_value,
                "clarification": result.clarification,
                "reviewer_name": result.reviewer_name,
                "verified_at": iso(result.verified_at),
                "verified_at_label": human_datetime(result.verified_at),
            }
            if result
            else None
        ),
    }


def queue(
    db: Session,
    status: Optional[str] = "PENDING_VERIFICATION",
    patient_id: Optional[int] = None,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    query = db.query(VerificationTask)
    if status and status != "ALL":
        query = query.filter(VerificationTask.status == status)
    if patient_id:
        query = query.filter(VerificationTask.patient_id == patient_id)
    tasks = query.limit(limit * 2).all()
    # High priority first, then least-confident first — the queue must surface
    # the most dangerous readings at the top.
    tasks.sort(
        key=lambda task: (
            0 if task.priority == "HIGH" else 1,
            task.confidence if task.confidence is not None else 1.0,
            -(task.id or 0),
        )
    )
    return [serialize_task(db, task) for task in tasks[:limit]]


def queue_stats(db: Session) -> Dict[str, int]:
    tasks = db.query(VerificationTask).all()
    return {
        "pending": sum(1 for t in tasks if t.status == "PENDING_VERIFICATION"),
        "high_priority": sum(
            1 for t in tasks
            if t.status == "PENDING_VERIFICATION" and t.priority == "HIGH"
        ),
        "verified": sum(1 for t in tasks if t.status == "VERIFIED"),
        "corrected": sum(1 for t in tasks if t.status == "CORRECTED"),
        "rejected": sum(1 for t in tasks if t.status == "REJECTED"),
        "total": len(tasks),
    }


# ---------------------------------------------------------------------------
def _apply_to_structured_records(
    db: Session, task: VerificationTask, final_value: str
):
    """Push the verified value into the structured medication/allergy record."""
    attr = FIELD_TO_MEDICATION_ATTR.get(task.field_key)
    if attr:
        medications = (
            db.query(Medication)
            .filter(Medication.memory_event_id == task.memory_event_id)
            .all()
        )
        for medication in medications:
            setattr(medication, attr, final_value)
            medication.verification_status = task.status
            medication.confidence = 1.0
            medication.source_type = "REVIEWER_VERIFIED"
    if task.field_key == "allergy":
        allergies = (
            db.query(Allergy)
            .filter(Allergy.patient_id == task.patient_id)
            .all()
        )
        for allergy in allergies:
            if (allergy.substance or "").lower() == (
                task.extracted_value or ""
            ).lower():
                allergy.substance = final_value
                allergy.verification_status = task.status
                allergy.source_type = "REVIEWER_VERIFIED"


def _promote_memory_event(
    db: Session,
    task: VerificationTask,
    final_value: str,
    reviewer_name: str,
    action: str,
):
    if not task.memory_event_id:
        return None
    event = (
        db.query(MemoryEvent).filter(MemoryEvent.id == task.memory_event_id).first()
    )
    if not event:
        return None

    original_text = event.original_text or event.content
    extra = dict(event.extra or {})
    extra.setdefault("original_ocr_value", task.extracted_value)
    extra.setdefault("original_confidence", task.confidence)
    extra["verified_field"] = task.field_label
    extra["verified_value"] = final_value
    extra["verified_by"] = reviewer_name
    extra["verified_at"] = iso(datetime.utcnow())
    extra["verification_action"] = action

    content = event.content
    if action == "CORRECTED" and task.extracted_value:
        content = content.replace(task.extracted_value, final_value)
        if final_value not in content:
            content = f"{content}\n{task.field_label} corrected to: {final_value}"
    content = (
        f"{content}\n[Reviewer {action.lower()}: {task.field_label} = "
        f"{final_value}; original OCR '{task.extracted_value}' at "
        f"{percent(task.confidence)}]"
    )

    memory_service.update_event(
        db,
        event,
        content=content,
        original_text=original_text,
        verification_status=action,
        trust_level="Reviewer Verified",
        source_type="REVIEWER_VERIFIED",
        confidence=1.0,
        extra=extra,
    )
    return event


def _finish(
    db: Session,
    task: VerificationTask,
    reviewer: Optional[Reviewer],
    actor,
    action: str,
    final_value: Optional[str],
    clarification: Optional[str] = None,
) -> Dict[str, Any]:
    reviewer_name = (
        reviewer.full_name if reviewer else getattr(actor, "name", "Reviewer")
    )
    result = VerificationResult(
        task_id=task.id,
        reviewer_id=getattr(reviewer, "id", None),
        reviewer_name=reviewer_name,
        action=action,
        original_value=task.extracted_value,
        original_confidence=task.confidence,
        corrected_value=final_value,
        clarification=clarification,
    )
    db.add(result)
    task.status = action

    if action in {"VERIFIED", "CORRECTED"} and final_value:
        _apply_to_structured_records(db, task, final_value)
        _promote_memory_event(db, task, final_value, reviewer_name, action)
    elif action == "REJECTED":
        if task.memory_event_id:
            event = (
                db.query(MemoryEvent)
                .filter(MemoryEvent.id == task.memory_event_id)
                .first()
            )
            if event:
                extra = dict(event.extra or {})
                extra["rejected_reason"] = clarification
                extra["rejected_by"] = reviewer_name
                memory_service.update_event(
                    db, event,
                    verification_status="REJECTED",
                    severity="attention",
                    extra=extra,
                    content=(
                        f"{event.content}\n[Reviewer rejected this extraction: "
                        f"{clarification}]"
                    ),
                )

    if task.document_id:
        document = db.query(Document).filter(Document.id == task.document_id).first()
        if document:
            remaining = (
                db.query(VerificationTask)
                .filter(
                    VerificationTask.document_id == document.id,
                    VerificationTask.status == "PENDING_VERIFICATION",
                    VerificationTask.id != task.id,
                )
                .count()
            )
            document.verification_status = (
                "PENDING_VERIFICATION" if remaining else action
            )

    audit_service.log(
        db, f"VERIFICATION_{action}", actor, patient_id=task.patient_id,
        target=f"task:{task.id}",
        detail=(
            f"{task.field_label}: '{task.extracted_value}' "
            f"({percent(task.confidence)}) -> '{final_value}'"
        ),
        commit=False,
    )
    db.commit()
    db.refresh(task)
    return serialize_task(db, task)


def verify(db: Session, task: VerificationTask, reviewer, actor, note=None):
    return _finish(db, task, reviewer, actor, "VERIFIED", task.extracted_value, note)


def correct(db: Session, task: VerificationTask, reviewer, actor,
            corrected_value: str, clarification=None):
    return _finish(
        db, task, reviewer, actor, "CORRECTED", corrected_value, clarification
    )


def reject(db: Session, task: VerificationTask, reviewer, actor, reason: str):
    return _finish(db, task, reviewer, actor, "REJECTED", None, reason)
