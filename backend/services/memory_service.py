"""
Persistent health memory — creation, timeline and overview.

Every write goes through `create_event()` so that provenance and the RAG index
can never drift apart from the record itself.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from database import Session

from models import (
    Allergy,
    CaregiverObservation,
    Diagnosis,
    Document,
    Doctor,
    HospitalVisit,
    LabResult,
    Medication,
    MedicationAdministration,
    MemoryEvent,
    Patient,
    Prescription,
    VerificationTask,
    VoiceEntry,
)
from rag import chunker
from services import consent_service
from services.authorization_service import AccessContext
from utils.helpers import human_date, iso, parse_date

TRUST_BY_SOURCE = {
    "PATIENT_TEXT": "Patient Reported",
    "PATIENT_VOICE": "Patient Reported",
    "DOCTOR_DOCUMENT": "OCR Extracted",
    "SCANNED_DOCUMENT": "OCR Extracted",
    "HANDWRITTEN_DOCUMENT": "OCR Extracted",
    "OCR": "OCR Extracted",
    "DOCTOR_RECORDED": "Doctor Recorded",
    "CAREGIVER_RECORDED": "Caregiver Recorded",
    "REVIEWER_VERIFIED": "Reviewer Verified",
    "AI_GENERATED": "AI Extracted",
}

EVENT_SCOPE = {
    "MEDICATION": "MEDICATION_INFORMATION",
    "PRESCRIPTION": "MEDICATION_INFORMATION",
    "MEDICATION_CHANGE": "MEDICATION_INFORMATION",
    "MEDICATION_ADMINISTRATION": "MEDICATION_INFORMATION",
    "ALLERGY": "MEDICATION_INFORMATION",
    "OBSERVATION": "CAREGIVER_NOTES",
    "VOICE_ENTRY": "VOICE_DIARY",
    "DOCUMENT": "DOCUMENTS",
    "CONSULTATION": "RECENT_HISTORY",
    "DIAGNOSIS": "RECENT_HISTORY",
    "SYMPTOM": "RECENT_HISTORY",
    "LAB_RESULT": "RECENT_HISTORY",
    "HOSPITAL_VISIT": "RECENT_HISTORY",
    "NOTE": "RECENT_HISTORY",
}


# ---------------------------------------------------------------------------
def create_event(
    db: Session,
    patient_id: int,
    event_type: str,
    title: str,
    content: str,
    source_type: str,
    event_date: Optional[datetime] = None,
    author_role: Optional[str] = None,
    author_name: Optional[str] = None,
    author_user_id: Optional[int] = None,
    doctor_id: Optional[int] = None,
    document_id: Optional[int] = None,
    confidence: float = 1.0,
    verification_status: str = "NOT_REQUIRED",
    original_text: Optional[str] = None,
    severity: str = "normal",
    tags: Optional[List[str]] = None,
    extra: Optional[Dict[str, Any]] = None,
    trust_level: Optional[str] = None,
    index: bool = True,
    commit: bool = True,
) -> MemoryEvent:
    event = MemoryEvent(
        patient_id=patient_id,
        event_type=event_type,
        title=title[:240],
        content=content,
        event_date=event_date or datetime.utcnow(),
        source_type=source_type,
        trust_level=trust_level or TRUST_BY_SOURCE.get(source_type, "AI Extracted"),
        author_role=author_role,
        author_name=author_name,
        author_user_id=author_user_id,
        doctor_id=doctor_id,
        document_id=document_id,
        confidence=confidence,
        verification_status=verification_status,
        original_text=original_text,
        consent_scope=EVENT_SCOPE.get(event_type, "RECENT_HISTORY"),
        severity=severity,
        tags=tags or [],
        extra=extra or {},
    )
    db.add(event)
    db.flush()

    if index:
        index_event(db, event, commit=False)
    if commit:
        db.commit()
        db.refresh(event)
    return event


def index_event(db: Session, event: MemoryEvent, commit: bool = True):
    doctor_name = None
    if event.doctor_id:
        doctor = db.query(Doctor).filter(Doctor.id == event.doctor_id).first()
        doctor_name = doctor.full_name if doctor else None

    body = event.content
    if doctor_name:
        body = f"{body}\nDoctor: {doctor_name}"
    if event.original_text and event.original_text != event.content:
        body = f"{body}\nOriginal source text: {event.original_text[:400]}"

    chunker.index_text(
        db,
        patient_id=event.patient_id,
        source_id=f"memory_event:{event.id}",
        source_type=event.source_type,
        source_kind="memory_event",
        text=body,
        title=event.title,
        event_date=event.event_date,
        author=event.author_name or doctor_name,
        doctor_id=event.doctor_id,
        confidence=event.confidence if event.confidence is not None else 1.0,
        verification_status=event.verification_status or "NOT_REQUIRED",
        consent_scope=event.consent_scope or "RECENT_HISTORY",
        trust_level=event.trust_level,
        commit=commit,
    )


def update_event(db: Session, event: MemoryEvent, **changes) -> MemoryEvent:
    for key, value in changes.items():
        if hasattr(event, key):
            setattr(event, key, value)
    db.flush()
    index_event(db, event, commit=False)
    db.commit()
    db.refresh(event)
    return event


# ---------------------------------------------------------------------------
def serialize_event(db: Session, event: MemoryEvent) -> Dict[str, Any]:
    doctor_name = None
    if event.doctor_id:
        doctor = db.query(Doctor).filter(Doctor.id == event.doctor_id).first()
        doctor_name = doctor.full_name if doctor else None
    document = None
    if event.document_id:
        doc = db.query(Document).filter(Document.id == event.document_id).first()
        if doc:
            document = {
                "id": doc.id,
                "filename": doc.filename,
                "document_type": doc.document_type,
                "is_handwritten": doc.is_handwritten,
                "confidence": doc.confidence,
            }
    return {
        "id": event.id,
        "patient_id": event.patient_id,
        "event_type": event.event_type,
        "title": event.title,
        "content": event.content,
        "event_date": iso(event.event_date),
        "event_date_label": human_date(event.event_date),
        "source_type": event.source_type,
        "trust_level": event.trust_level,
        "author_role": event.author_role,
        "author_name": event.author_name,
        "doctor_name": doctor_name,
        "confidence": event.confidence,
        "verification_status": event.verification_status,
        "severity": event.severity,
        "tags": event.tags or [],
        "document_id": event.document_id,
        "document": document,
        "original_text": event.original_text,
        "extra": event.extra or {},
    }


def timeline(
    db: Session,
    context: AccessContext,
    event_types: Optional[List[str]] = None,
    source_types: Optional[List[str]] = None,
    search: Optional[str] = None,
    since: Optional[datetime] = None,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    query = (
        db.query(MemoryEvent)
        .filter(
            MemoryEvent.patient_id == context.patient_id,
            MemoryEvent.is_active.is_(True),
        )
        .order_by(MemoryEvent.event_date.desc(), MemoryEvent.id.desc())
    )
    if event_types:
        query = query.filter(MemoryEvent.event_type.in_(event_types))
    if source_types:
        query = query.filter(MemoryEvent.source_type.in_(source_types))
    if since:
        query = query.filter(MemoryEvent.event_date >= since)

    events = query.limit(limit * 2).all()
    visible = []
    for event in events:
        if context.role != "patient" and not consent_service.event_visible(
            event.event_type, context.scopes
        ):
            continue
        if context.role == "caregiver" and event.event_type == "VOICE_ENTRY":
            continue
        if search:
            haystack = f"{event.title} {event.content}".lower()
            if search.lower() not in haystack:
                continue
        visible.append(serialize_event(db, event))
        if len(visible) >= limit:
            break
    return visible


# ---------------------------------------------------------------------------
def overview(db: Session, patient_id: int) -> Dict[str, Any]:
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        return {}

    medications = (
        db.query(Medication)
        .filter(Medication.patient_id == patient_id, Medication.status == "ACTIVE")
        .order_by(Medication.name)
        .all()
    )
    allergies = db.query(Allergy).filter(Allergy.patient_id == patient_id).all()
    diagnoses = (
        db.query(Diagnosis)
        .filter(Diagnosis.patient_id == patient_id, Diagnosis.status == "ACTIVE")
        .all()
    )
    labs = (
        db.query(LabResult)
        .filter(LabResult.patient_id == patient_id)
        .order_by(LabResult.tested_on.desc())
        .limit(8)
        .all()
    )
    visits = (
        db.query(HospitalVisit)
        .filter(HospitalVisit.patient_id == patient_id)
        .order_by(HospitalVisit.admitted_on.desc())
        .limit(4)
        .all()
    )
    pending = (
        db.query(VerificationTask)
        .filter(
            VerificationTask.patient_id == patient_id,
            VerificationTask.status == "PENDING_VERIFICATION",
        )
        .count()
    )
    last_event = (
        db.query(MemoryEvent)
        .filter(MemoryEvent.patient_id == patient_id)
        .order_by(MemoryEvent.event_date.desc())
        .first()
    )
    total_events = (
        db.query(MemoryEvent).filter(MemoryEvent.patient_id == patient_id).count()
    )
    documents = db.query(Document).filter(Document.patient_id == patient_id).count()

    recent_window = datetime.utcnow() - timedelta(days=30)
    recent_changes = (
        db.query(MemoryEvent)
        .filter(
            MemoryEvent.patient_id == patient_id,
            MemoryEvent.event_type.in_(["MEDICATION_CHANGE", "MEDICATION"]),
            MemoryEvent.event_date >= recent_window,
        )
        .count()
    )

    alerts: List[Dict[str, str]] = []
    if pending:
        alerts.append({
            "level": "attention",
            "title": f"{pending} medication detail(s) awaiting reviewer verification",
            "detail": "Low-confidence extraction has been routed for human review.",
        })
    for lab in labs:
        if lab.flag in {"high", "low", "critical"}:
            alerts.append({
                "level": "critical" if lab.flag == "critical" else "attention",
                "title": f"{lab.test_name} {lab.flag}: {lab.value} {lab.unit or ''}".strip(),
                "detail": f"Recorded {human_date(lab.tested_on)}",
            })
    missed = (
        db.query(MedicationAdministration)
        .filter(
            MedicationAdministration.patient_id == patient_id,
            MedicationAdministration.status.in_(["Missed", "Needs Attention"]),
        )
        .count()
    )
    if missed:
        alerts.append({
            "level": "attention",
            "title": f"{missed} medication dose(s) recorded as missed",
            "detail": "Review the medication administration record.",
        })

    return {
        "patient": {
            "id": patient.id,
            "full_name": patient.full_name,
            "age": patient.age,
            "gender": patient.gender,
            "blood_group": patient.blood_group,
            "room_number": patient.room_number,
            "guardian_name": patient.guardian_name,
            "primary_doctor": (
                patient.primary_doctor.full_name if patient.primary_doctor else None
            ),
            "old_age_home": (
                patient.old_age_home.name if patient.old_age_home else None
            ),
        },
        "counts": {
            "memory_events": total_events,
            "documents": documents,
            "active_medications": len(medications),
            "pending_verification": pending,
            "recent_medication_changes": recent_changes,
        },
        "medications": [
            {
                "id": m.id, "name": m.name, "dose": m.dose, "frequency": m.frequency,
                "instruction": m.instruction, "status": m.status,
                "source_type": m.source_type, "confidence": m.confidence,
                "verification_status": m.verification_status,
                "schedule_times": m.schedule_times or [],
                "prescriber": m.prescriber.full_name if m.prescriber else None,
                "started_on": iso(m.started_on),
            }
            for m in medications
        ],
        "allergies": [
            {
                "id": a.id, "substance": a.substance, "reaction": a.reaction,
                "severity": a.severity, "source_type": a.source_type,
                "verification_status": a.verification_status,
            }
            for a in allergies
        ],
        "conditions": [
            {
                "id": d.id, "name": d.name, "is_critical": d.is_critical,
                "diagnosed_on": iso(d.diagnosed_on), "source_type": d.source_type,
            }
            for d in diagnoses
        ],
        "lab_results": [
            {
                "id": l.id, "test_name": l.test_name, "value": l.value,
                "unit": l.unit, "reference_range": l.reference_range,
                "flag": l.flag, "tested_on": iso(l.tested_on), "lab_name": l.lab_name,
            }
            for l in labs
        ],
        "hospital_visits": [
            {
                "id": v.id, "hospital": v.hospital, "reason": v.reason,
                "admitted_on": iso(v.admitted_on), "discharged_on": iso(v.discharged_on),
                "summary": v.summary,
            }
            for v in visits
        ],
        "alerts": alerts,
        "last_updated": iso(last_event.event_date) if last_event else None,
    }


def emergency_card(db: Session, patient_id: int) -> Dict[str, Any]:
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        return {}
    data = overview(db, patient_id)
    critical_meds = [
        m for m in data.get("medications", [])
        if m["verification_status"] in {"VERIFIED", "CORRECTED", "NOT_REQUIRED"}
    ][:6]
    return {
        "patient_name": patient.full_name,
        "age": patient.age,
        "gender": patient.gender,
        "blood_group": patient.blood_group,
        "room_number": patient.room_number,
        "allergies": data.get("allergies", []),
        "critical_conditions": [
            c for c in data.get("conditions", []) if c["is_critical"]
        ] or data.get("conditions", [])[:3],
        "critical_medications": critical_meds,
        "emergency_contact": {
            "name": patient.emergency_contact_name,
            "phone": patient.emergency_contact_phone,
            "relation": patient.emergency_contact_relation,
        },
        "primary_doctor": (
            {
                "name": patient.primary_doctor.full_name,
                "specialty": patient.primary_doctor.specialty,
                "hospital": patient.primary_doctor.hospital,
                "phone": patient.primary_doctor.phone,
            }
            if patient.primary_doctor
            else None
        ),
        "facility": (
            {
                "name": patient.old_age_home.name,
                "phone": patient.old_age_home.phone,
            }
            if patient.old_age_home
            else None
        ),
        "generated_at": iso(datetime.utcnow()),
    }


def caregiver_insight_feed(
    db: Session, patient_ids: List[int], limit: int = 40
) -> List[Dict[str, Any]]:
    """§28 — observations, symptoms, medication issues, recent changes."""
    if not patient_ids:
        return []
    events = (
        db.query(MemoryEvent)
        .filter(
            MemoryEvent.patient_id.in_(patient_ids),
            MemoryEvent.event_type.in_([
                "OBSERVATION", "SYMPTOM", "MEDICATION_CHANGE",
                "MEDICATION_ADMINISTRATION", "VOICE_ENTRY", "CONSULTATION",
            ]),
        )
        .order_by(MemoryEvent.event_date.desc())
        .limit(limit)
        .all()
    )
    feed = []
    for event in events:
        patient = db.query(Patient).filter(Patient.id == event.patient_id).first()
        payload = serialize_event(db, event)
        payload["patient_name"] = patient.full_name if patient else "Unknown"
        feed.append(payload)
    return feed
