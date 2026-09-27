"""
The single ingestion pipeline shared by TEXT, VOICE and SCAN & UPLOAD (§6–§13).

    input -> normalisation -> entity extraction -> confidence analysis
          -> health memory (+ structured records)
          -> verification routing -> doctor routing -> RAG index

Nothing here upgrades a patient statement into a confirmed diagnosis: a
symptom the patient mentions is stored as `Patient Reported`, and an OCR
reading stays `OCR Extracted` until a reviewer verifies it.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from database import Session

from config import HIGH_CONFIDENCE_THRESHOLD
from models import (
    Allergy,
    CaregiverObservation,
    Diagnosis,
    Document,
    DoctorConsultation,
    LabResult,
    Medication,
    MemoryEvent,
    OCRResult,
    Patient,
    Prescription,
    VoiceEntry,
)
from ocr import confidence as conf
from ocr.ocr_service import build_fields, ocr_service
from services import (
    audit_service,
    document_service,
    language_service,
    memory_service,
    verification_service,
)
from services.extraction_service import extract_entities, summarise_entities
from utils.helpers import human_date, parse_date, percent
from utils.security import clean_text

VOICE_DISCLAIMER = (
    "Recorded by the patient/guardian in their own words. "
    "Not a clinical diagnosis."
)


# ---------------------------------------------------------------------------
def _field_confidence(fields: List[Dict[str, Any]], key: str, default: float) -> float:
    for field in fields:
        if field["field"] == key:
            return field["confidence"]
    return default


def _persist_entities(
    db: Session,
    patient: Patient,
    entities: Dict[str, Any],
    fields: List[Dict[str, Any]],
    *,
    source_type: str,
    trust_level: str,
    author_role: str,
    author_name: str,
    author_user_id: Optional[int],
    event_date: datetime,
    base_confidence: float,
    document: Optional[Document] = None,
    doctor_id: Optional[int] = None,
    original_text: Optional[str] = None,
    narrative: str = "",
    language: Optional[Dict[str, Any]] = None,
) -> List[MemoryEvent]:
    """Create the memory events and structured rows for one ingested source."""
    events: List[MemoryEvent] = []
    important_pending = any(f["needs_verification"] for f in fields)

    def status_for(field_key: str) -> str:
        for field in fields:
            if field["field"] == field_key and field["needs_verification"]:
                return "PENDING_VERIFICATION"
        return "NOT_REQUIRED"

    # --- consultation -----------------------------------------------------
    doctor = entities.get("doctor")
    if doctor or narrative:
        title = (
            f"Consultation with {doctor['name']}" if doctor
            else "Health information recorded"
        )
        detail = narrative or ""
        if doctor:
            bits = [f"Doctor: {doctor['name']}"]
            if doctor.get("specialty"):
                bits.append(f"Specialty: {doctor['specialty']}")
            if doctor.get("hospital"):
                bits.append(f"Hospital/Clinic: {doctor['hospital']}")
            detail = f"{detail}\n" + "\n".join(bits) if detail else "\n".join(bits)
        event = memory_service.create_event(
            db, patient.id,
            event_type="CONSULTATION" if doctor else "NOTE",
            title=title,
            content=detail.strip(),
            source_type=source_type,
            trust_level=trust_level,
            event_date=event_date,
            author_role=author_role,
            author_name=author_name,
            author_user_id=author_user_id,
            doctor_id=doctor_id,
            document_id=getattr(document, "id", None),
            confidence=_field_confidence(fields, "doctor_name", base_confidence),
            verification_status=status_for("doctor_name"),
            original_text=original_text,
            tags=["consultation"] if doctor else ["note"],
            commit=False,
        )
        events.append(event)
        if doctor and doctor_id:
            db.add(
                DoctorConsultation(
                    patient_id=patient.id,
                    doctor_id=doctor_id,
                    memory_event_id=event.id,
                    consulted_on=event_date,
                    reason=", ".join(entities.get("symptoms", [])) or None,
                    findings=narrative[:1000] or None,
                    advice=None,
                    source_type=source_type,
                )
            )

    # --- medications ------------------------------------------------------
    prescription_items = []
    for med in entities.get("medications", []):
        med_confidence = min(
            v for v in [
                med["confidence"].get("name") or base_confidence,
                med["confidence"].get("dose") or 1.0,
                med["confidence"].get("frequency") or 1.0,
            ]
        )
        med_status = "NOT_REQUIRED"
        for key in ("medication_name", "medication_dose", "medication_frequency"):
            if status_for(key) == "PENDING_VERIFICATION":
                med_status = "PENDING_VERIFICATION"
                break

        label_bits = [med["name"]]
        if med.get("dose"):
            label_bits.append(med["dose"])
        if med.get("frequency"):
            label_bits.append(med["frequency"])
        label = " — ".join(label_bits)

        event_type = "MEDICATION_CHANGE" if med.get("is_change") else "MEDICATION"
        event = memory_service.create_event(
            db, patient.id,
            event_type=event_type,
            title=(
                f"Medication change: {med['name']}" if med.get("is_change")
                else f"Medication: {label}"
            ),
            content=(
                f"{label}."
                f"{' Instruction: ' + med['instruction'] + '.' if med.get('instruction') else ''}"
                f"\nContext: {med.get('context', '')[:300]}"
            ),
            source_type=source_type,
            trust_level=trust_level,
            event_date=event_date,
            author_role=author_role,
            author_name=author_name,
            author_user_id=author_user_id,
            doctor_id=doctor_id,
            document_id=getattr(document, "id", None),
            confidence=med_confidence,
            verification_status=med_status,
            original_text=original_text,
            severity="attention" if med_status == "PENDING_VERIFICATION" else "normal",
            tags=["medication"] + (["change"] if med.get("is_change") else []),
            extra={
                "medication_name": med["name"],
                "dose": med.get("dose"),
                "frequency": med.get("frequency"),
                "instruction": med.get("instruction"),
            },
            commit=False,
        )
        events.append(event)

        existing = (
            db.query(Medication)
            .filter(
                Medication.patient_id == patient.id,
                Medication.name == med["name"],
                Medication.status == "ACTIVE",
            )
            .first()
        )
        if existing and med.get("is_change"):
            existing.status = "CHANGED"
            existing.stopped_on = event_date
            existing = None

        if not existing:
            medication = Medication(
                patient_id=patient.id,
                memory_event_id=event.id,
                name=med["name"],
                dose=med.get("dose"),
                frequency=med.get("frequency"),
                instruction=med.get("instruction"),
                started_on=event_date,
                status="ACTIVE",
                prescriber_doctor_id=doctor_id,
                source_type=source_type,
                confidence=med_confidence,
                verification_status=med_status,
                schedule_times=_schedule_for(med.get("frequency")),
            )
            db.add(medication)
        prescription_items.append(
            {
                "name": med["name"],
                "dose": med.get("dose"),
                "frequency": med.get("frequency"),
                "instruction": med.get("instruction"),
                "confidence": med_confidence,
            }
        )

    if prescription_items and source_type in {
        "DOCTOR_DOCUMENT", "HANDWRITTEN_DOCUMENT", "SCANNED_DOCUMENT"
    }:
        db.add(
            Prescription(
                patient_id=patient.id,
                doctor_id=doctor_id,
                document_id=getattr(document, "id", None),
                issued_on=event_date,
                items=prescription_items,
                instruction=narrative[:500] or None,
                source_type=source_type,
                verification_status=(
                    "PENDING_VERIFICATION" if important_pending else "NOT_REQUIRED"
                ),
            )
        )

    # --- symptoms ---------------------------------------------------------
    for symptom in entities.get("symptoms", []):
        events.append(
            memory_service.create_event(
                db, patient.id,
                event_type="SYMPTOM",
                title=f"Reported symptom: {symptom.title()}",
                content=(
                    f"{symptom.title()} noted in the {source_type.replace('_', ' ').lower()}."
                    f"\n{VOICE_DISCLAIMER if source_type.startswith('PATIENT') else ''}"
                ).strip(),
                source_type=source_type,
                trust_level=trust_level,
                event_date=event_date,
                author_role=author_role,
                author_name=author_name,
                author_user_id=author_user_id,
                document_id=getattr(document, "id", None),
                confidence=_field_confidence(fields, "symptom", base_confidence - 0.04),
                original_text=original_text,
                tags=["symptom"],
                commit=False,
            )
        )

    # --- diagnoses --------------------------------------------------------
    for diagnosis in entities.get("diagnoses", []):
        is_clinical = source_type in {
            "DOCTOR_DOCUMENT", "HANDWRITTEN_DOCUMENT", "DOCTOR_RECORDED",
            "SCANNED_DOCUMENT",
        }
        event = memory_service.create_event(
            db, patient.id,
            event_type="DIAGNOSIS",
            title=f"Condition mentioned: {diagnosis.title()}",
            content=(
                f"{diagnosis.title()} appears in this source. "
                + (
                    "Recorded from a medical document."
                    if is_clinical
                    else "Mentioned by the patient/guardian — not a confirmed diagnosis."
                )
            ),
            source_type=source_type,
            trust_level=trust_level,
            event_date=event_date,
            author_role=author_role,
            author_name=author_name,
            author_user_id=author_user_id,
            document_id=getattr(document, "id", None),
            confidence=_field_confidence(fields, "diagnosis", base_confidence - 0.03),
            original_text=original_text,
            tags=["condition"],
            commit=False,
        )
        events.append(event)
        if is_clinical:
            already = (
                db.query(Diagnosis)
                .filter(
                    Diagnosis.patient_id == patient.id,
                    Diagnosis.name.ilike(diagnosis),
                )
                .first()
            )
            if not already:
                db.add(
                    Diagnosis(
                        patient_id=patient.id,
                        memory_event_id=event.id,
                        name=diagnosis.title(),
                        diagnosed_on=event_date,
                        doctor_id=doctor_id,
                        source_type=source_type,
                    )
                )

    # --- allergies --------------------------------------------------------
    for allergy in entities.get("allergies", []):
        event = memory_service.create_event(
            db, patient.id,
            event_type="ALLERGY",
            title=f"Allergy: {allergy['substance']}",
            content=f"Allergy to {allergy['substance']} recorded from this source.",
            source_type=source_type,
            trust_level=trust_level,
            event_date=event_date,
            author_role=author_role,
            author_name=author_name,
            author_user_id=author_user_id,
            document_id=getattr(document, "id", None),
            confidence=allergy.get("confidence", base_confidence),
            verification_status=status_for("allergy"),
            original_text=original_text,
            severity="attention",
            tags=["allergy"],
            commit=False,
        )
        events.append(event)
        existing = (
            db.query(Allergy)
            .filter(
                Allergy.patient_id == patient.id,
                Allergy.substance.ilike(allergy["substance"]),
            )
            .first()
        )
        if not existing:
            db.add(
                Allergy(
                    patient_id=patient.id,
                    substance=allergy["substance"],
                    source_type=source_type,
                    verification_status=status_for("allergy"),
                )
            )

    # --- lab results ------------------------------------------------------
    for lab in entities.get("lab_results", []):
        event = memory_service.create_event(
            db, patient.id,
            event_type="LAB_RESULT",
            title=f"Lab result: {lab['test_name']}",
            content=(
                f"{lab['test_name']}: {lab.get('value') or 'value not recognised'} "
                f"{lab.get('unit') or ''}".strip()
            ),
            source_type=source_type,
            trust_level=trust_level,
            event_date=event_date,
            author_role=author_role,
            author_name=author_name,
            author_user_id=author_user_id,
            document_id=getattr(document, "id", None),
            confidence=lab.get("confidence", base_confidence),
            original_text=original_text,
            tags=["lab"],
            commit=False,
        )
        events.append(event)
        db.add(
            LabResult(
                patient_id=patient.id,
                memory_event_id=event.id,
                test_name=lab["test_name"],
                value=lab.get("value"),
                unit=lab.get("unit"),
                tested_on=event_date,
                document_id=getattr(document, "id", None),
            )
        )

    # Tamil / mixed entries carry their assisted English reading as provenance,
    # so anyone reading the record later can see the patient's own words and
    # how they were read — and that it was never treated as a diagnosis.
    if language and language.get("is_assisted"):
        for event in events:
            extra = dict(event.extra or {})
            extra.update(
                {
                    "language": language["language"],
                    "assisted_reading": language["assisted_reading"],
                    "recognised_terms": language["terms"],
                    "assisted_reading_note": language.get("note"),
                }
            )
            event.extra = extra

    db.flush()
    return events


def _schedule_for(frequency: Optional[str]) -> List[str]:
    mapping = {
        "Once daily": ["08:00"],
        "Twice daily": ["08:00", "20:00"],
        "Three times daily": ["08:00", "14:00", "20:00"],
        "Four times daily": ["06:00", "12:00", "18:00", "22:00"],
        "At night": ["21:00"],
        "Every morning": ["08:00"],
        "Once weekly": ["09:00"],
        "Alternate days": ["09:00"],
    }
    return mapping.get(frequency or "", ["08:00"])


def _language_payload(language: Dict[str, Any]) -> Dict[str, Any]:
    """What the UI shows about a Tamil or mixed entry."""
    return {
        "detected": language["language"],
        "assisted_reading": language["assisted_reading"],
        "recognised_terms": language["terms"],
        "note": language.get("note"),
    }


# ---------------------------------------------------------------------------
def ingest_text(
    db: Session,
    patient: Patient,
    text: str,
    actor,
    entry_date: Optional[str] = None,
) -> Dict[str, Any]:
    text = clean_text(text)
    # Tamil and mixed Tamil-English entries get an assisted English reading so
    # extraction can work; the patient's own wording is what is stored.
    language = language_service.normalise(text)
    base_confidence = 0.93  # typed text: no recognition error, but still extraction
    if language["is_assisted"]:
        # An assisted reading is an aid, not a certainty — say so in the score.
        base_confidence = 0.88
    entities = extract_entities(
        language["text_for_extraction"], base_confidence=base_confidence
    )
    fields = build_fields(entities, base_confidence, text)
    event_date = (
        parse_date(entry_date) or entities.get("event_date") or datetime.utcnow()
    )

    routing = document_service.route_to_doctor(
        db, patient, entities.get("doctor"), None, actor
    )
    doctor_id = routing.get("doctor", {}).get("id") if routing.get("doctor") else None

    events = _persist_entities(
        db, patient, entities, fields,
        source_type="PATIENT_TEXT",
        trust_level="Patient Reported",
        author_role=actor.role,
        author_name=actor.name,
        author_user_id=actor.id,
        event_date=event_date,
        base_confidence=base_confidence,
        doctor_id=doctor_id,
        original_text=text,
        narrative=text,
        language=language,
    )

    tasks = []
    for event in events:
        tasks += verification_service.create_tasks(
            db, patient.id, _fields_for_event(fields, event), memory_event=event,
            commit=False,
        )

    audit_service.log(
        db, "HEALTH_MEMORY_CREATE", actor, patient_id=patient.id,
        target="ingestion/text",
        detail=f"{len(events)} event(s); entities: {summarise_entities(entities)}",
        commit=False,
    )
    db.commit()

    return {
        "memory_event_ids": [event.id for event in events],
        "entities": _public_entities(entities),
        "fields": fields,
        "confidence": base_confidence,
        "verification_tasks": [task.id for task in tasks],
        "doctor_routing": routing,
        "source": "Patient/Guardian entered",
        "language": _language_payload(language),
        "message": (
            f"Added {len(events)} entry(ies) to your health memory "
            f"({summarise_entities(entities)})."
        ),
    }


def ingest_voice(
    db: Session,
    patient: Patient,
    transcript: str,
    actor,
    duration_seconds: Optional[float] = None,
    recognition_confidence: Optional[float] = 0.9,
    audio_ref: Optional[str] = None,
) -> Dict[str, Any]:
    transcript = clean_text(transcript)
    # Speech in Tamil, English or a mixture of the two. The transcript is kept
    # exactly as spoken; an assisted English reading is derived for extraction.
    language = language_service.normalise(transcript)
    base_confidence = round(min(0.95, max(0.45, recognition_confidence or 0.9)), 4)
    if language["is_assisted"]:
        base_confidence = round(min(base_confidence, 0.88), 4)
    entities = extract_entities(
        language["text_for_extraction"], base_confidence=base_confidence
    )
    fields = build_fields(entities, base_confidence, transcript)
    event_date = entities.get("event_date") or datetime.utcnow()

    routing = document_service.route_to_doctor(
        db, patient, entities.get("doctor"), None, actor
    )
    doctor_id = routing.get("doctor", {}).get("id") if routing.get("doctor") else None

    diary_event = memory_service.create_event(
        db, patient.id,
        event_type="VOICE_ENTRY",
        title="Voice health diary entry",
        content=transcript,
        source_type="PATIENT_VOICE",
        trust_level="Patient Reported",
        event_date=event_date,
        author_role=actor.role,
        author_name=actor.name,
        author_user_id=actor.id,
        confidence=base_confidence,
        original_text=transcript,
        tags=["voice"],
        extra={"speech_recognition_confidence": base_confidence,
               "duration_seconds": duration_seconds,
               "language": language["language"],
               "assisted_reading": language["assisted_reading"],
               "recognised_terms": language["terms"]},
        commit=False,
    )
    db.add(
        VoiceEntry(
            patient_id=patient.id,
            memory_event_id=diary_event.id,
            transcript=transcript,
            audio_ref=audio_ref,
            duration_seconds=duration_seconds,
            recorded_at=datetime.utcnow(),
            confidence=base_confidence,
            extracted_entities=_public_entities(entities),
        )
    )

    events = [diary_event] + _persist_entities(
        db, patient, entities, fields,
        source_type="PATIENT_VOICE",
        trust_level="Patient Reported",
        author_role=actor.role,
        author_name=actor.name,
        author_user_id=actor.id,
        event_date=event_date,
        base_confidence=base_confidence,
        doctor_id=doctor_id,
        original_text=transcript,
        narrative=transcript,
        language=language,
    )

    tasks = []
    for event in events:
        tasks += verification_service.create_tasks(
            db, patient.id, _fields_for_event(fields, event), memory_event=event,
            commit=False,
        )

    audit_service.log(
        db, "HEALTH_MEMORY_CREATE", actor, patient_id=patient.id,
        target="ingestion/voice",
        detail=f"transcript {len(transcript)} chars; {summarise_entities(entities)}",
        commit=False,
    )
    db.commit()

    return {
        "memory_event_ids": [event.id for event in events],
        "entities": _public_entities(entities),
        "fields": fields,
        "confidence": base_confidence,
        "verification_tasks": [task.id for task in tasks],
        "doctor_routing": routing,
        "source": "Patient Reported (voice)",
        "transcript": transcript,
        "language": _language_payload(language),
        "message": (
            "Voice entry saved to your health memory. "
            "It is recorded as patient-reported information."
        ),
    }


def ingest_document(
    db: Session,
    patient: Patient,
    document: Document,
    actor,
    declared_handwritten: Optional[bool] = None,
) -> Dict[str, Any]:
    path = Path(document.stored_path) if document.stored_path else None
    if not path or not path.exists():
        document.ocr_status = "FAILED"
        db.commit()
        return {
            "ok": False,
            "message": "Unable to process document. The stored file is missing.",
        }

    result = ocr_service.process(
        path, document.filename, declared_handwritten=declared_handwritten
    )

    document.ocr_status = result["ocr_status"]
    document.ocr_engine = result["engine"]
    document.is_handwritten = result["handwriting_detected"]
    document.confidence = result["overall_confidence"]
    document.source_type = (
        "HANDWRITTEN_DOCUMENT" if result["handwriting_detected"] else "SCANNED_DOCUMENT"
    )
    document.document_type = document_service.guess_document_type(
        document.filename, result["raw_text"]
    )

    ocr_row = OCRResult(
        document_id=document.id,
        engine=result["engine"],
        raw_text=result["raw_text"],
        overall_confidence=result["overall_confidence"],
        fields=result["fields"],
        handwriting_detected=result["handwriting_detected"],
    )
    db.add(ocr_row)
    db.flush()

    audit_service.log(
        db, "OCR_PROCESSING", actor, patient_id=patient.id,
        target=document.filename,
        detail=(
            f"engine={result['engine']}; handwriting={result['handwriting_detected']}; "
            f"confidence={percent(result['overall_confidence'])}"
        ),
        commit=False,
    )

    entities = result["entities"]
    fields = result["fields"]
    event_date = entities.get("event_date") or datetime.utcnow()

    routing = document_service.route_to_doctor(
        db, patient, entities.get("doctor"), document, actor
    )
    doctor_id = routing.get("doctor", {}).get("id") if routing.get("doctor") else None

    document_event = memory_service.create_event(
        db, patient.id,
        event_type="DOCUMENT",
        title=(
            f"{'Handwritten' if document.is_handwritten else 'Scanned'} document: "
            f"{document.filename}"
        ),
        content=(
            f"Document type: {document.document_type}. "
            f"OCR engine: {result['engine']}. "
            f"Recognition confidence: {percent(result['overall_confidence'])}.\n"
            f"Extracted text:\n{result['raw_text'][:1500]}"
        ),
        source_type=document.source_type,
        event_date=event_date,
        author_role=actor.role,
        author_name=actor.name,
        author_user_id=actor.id,
        doctor_id=doctor_id,
        document_id=document.id,
        confidence=result["overall_confidence"],
        verification_status=(
            "PENDING_VERIFICATION"
            if any(f["needs_verification"] for f in fields)
            else "NOT_REQUIRED"
        ),
        original_text=result["raw_text"],
        tags=["document"] + (["handwritten"] if document.is_handwritten else []),
        extra={
            "ocr_engine": result["engine"],
            "handwriting_reason": result["handwriting_reason"],
            "fields": fields,
        },
        commit=False,
    )

    events = [document_event] + _persist_entities(
        db, patient, entities, fields,
        source_type=document.source_type,
        trust_level="OCR Extracted",
        author_role=actor.role,
        author_name=actor.name,
        author_user_id=actor.id,
        event_date=event_date,
        base_confidence=result["overall_confidence"],
        document=document,
        doctor_id=doctor_id,
        original_text=result["raw_text"],
        narrative=result["raw_text"][:900],
    )

    tasks = []
    for event in events:
        tasks += verification_service.create_tasks(
            db, patient.id, _fields_for_event(fields, event),
            document=document, ocr_result=ocr_row, memory_event=event, commit=False,
        )
    if tasks:
        document.verification_status = "PENDING_VERIFICATION"

    audit_service.log(
        db, "HEALTH_MEMORY_CREATE", actor, patient_id=patient.id,
        target=f"document:{document.id}",
        detail=f"{len(events)} event(s); {len(tasks)} verification task(s)",
        commit=False,
    )
    db.commit()
    db.refresh(document)

    flagged = [f for f in fields if f["needs_verification"]]
    return {
        "ok": True,
        "document": document_service.serialize_document(db, document),
        "ocr": {
            "engine": result["engine"],
            "engine_mode": result["engine_mode"],
            "handwriting_detected": result["handwriting_detected"],
            "handwriting_reason": result["handwriting_reason"],
            "document_type_label": result["document_type_label"],
            "raw_text": result["raw_text"],
            "recognition_confidence": result["recognition_confidence"],
            "overall_confidence": result["overall_confidence"],
            "fields": fields,
            "summary": result["summary"],
        },
        "memory_event_ids": [event.id for event in events],
        "verification_tasks": [task.id for task in tasks],
        "doctor_routing": routing,
        "entities": _public_entities(entities),
        "message": _document_message(result, flagged),
    }


def _document_message(result: Dict[str, Any], flagged: List[Dict[str, Any]]) -> str:
    confidence = percent(result["overall_confidence"])
    if not flagged:
        return (
            f"Document processed at {confidence} confidence and added to health "
            f"memory (at or above the "
            f"{int(HIGH_CONFIDENCE_THRESHOLD * 100)}% auto-accept threshold)."
        )
    high = sum(1 for f in flagged if f["priority"] == "HIGH")
    priority = "HIGH PRIORITY " if high else ""
    return (
        f"Document processed at {confidence} confidence. "
        f"{len(flagged)} clinically important field(s) need human confirmation — "
        f"a {priority}verification task has been sent to the reviewer."
    )


def _fields_for_event(
    fields: List[Dict[str, Any]], event: MemoryEvent
) -> List[Dict[str, Any]]:
    """Attach each flagged field to the memory event that carries it."""
    mapping = {
        "MEDICATION": {"medication_name", "medication_dose", "medication_frequency",
                       "prescription_instruction"},
        "MEDICATION_CHANGE": {"medication_change", "medication_name",
                              "medication_dose", "medication_frequency"},
        "ALLERGY": {"allergy"},
        "CONSULTATION": {"critical_instruction"},
        "DOCUMENT": set(),
    }
    keys = mapping.get(event.event_type)
    if keys is None:
        return []
    selected = []
    for field in fields:
        if field["field"] not in keys or not field["needs_verification"]:
            continue
        if event.event_type in {"MEDICATION", "MEDICATION_CHANGE"}:
            med_name = (event.extra or {}).get("medication_name", "")
            context = f"{field.get('value','')} {field.get('context','')}".lower()
            if med_name and med_name.lower() not in context:
                continue
        selected.append(field)
    return selected


def _public_entities(entities: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(entities)
    event_date = payload.get("event_date")
    payload["event_date"] = (
        event_date.isoformat() if isinstance(event_date, datetime) else None
    )
    payload["event_date_label"] = (
        human_date(event_date) if isinstance(event_date, datetime) else None
    )
    return payload
