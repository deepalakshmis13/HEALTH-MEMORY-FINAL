"""Append-only audit trail (§46)."""

from typing import Optional

from database import Session

from models import AuditEvent

ACTIONS = [
    "LOGIN", "LOGOUT", "REGISTER", "DOCUMENT_UPLOAD", "OCR_PROCESSING",
    "HEALTH_MEMORY_CREATE", "HEALTH_MEMORY_MODIFY", "DOCTOR_ROUTING",
    "CONSENT_GRANT", "CONSENT_REVOKE", "RAG_RETRIEVAL", "AI_SUMMARY_GENERATION",
    "MEDICATION_VERIFICATION", "SHIFT_HANDOVER_GENERATION", "VERIFICATION_VERIFY",
    "VERIFICATION_CORRECT", "VERIFICATION_REJECT", "EMERGENCY_ACCESS",
    "ACCESS_DENIED", "CHAT_QUERY", "SHIFT_START",
]


def log(
    db: Session,
    action: str,
    actor=None,
    patient_id: Optional[int] = None,
    target: Optional[str] = None,
    detail: Optional[str] = None,
    commit: bool = True,
) -> AuditEvent:
    event = AuditEvent(
        actor_user_id=getattr(getattr(actor, "user", None), "id", None),
        actor_name=getattr(actor, "name", None) or "system",
        actor_role=getattr(actor, "role", None) or "system",
        action=action,
        patient_id=patient_id,
        target=target,
        detail=(detail or "")[:2000] or None,
    )
    db.add(event)
    if commit:
        db.commit()
    return event


def recent(db: Session, limit: int = 100, patient_id: Optional[int] = None):
    query = db.query(AuditEvent)
    if patient_id:
        query = query.filter(AuditEvent.patient_id == patient_id)
    return query.order_by(AuditEvent.created_at.desc()).limit(limit).all()
