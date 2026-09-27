"""Document storage, retrieval and doctor routing (§17, §18, §32)."""

import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from database import Session

from config import STORAGE_DIR
from models import Doctor, DoctorAssignment, Document, Patient
from services import audit_service, consent_service, doctor_relationship_service
from utils.helpers import iso
from utils.security import sanitize_filename

DOCUMENT_TYPE_HINTS = [
    (r"prescription|rx\b", "PRESCRIPTION"),
    (r"lab|report|test|blood|pathology|diagnostic", "LAB_REPORT"),
    (r"discharge|admission|summary", "DISCHARGE_SUMMARY"),
    (r"scan|x[- ]?ray|mri|ct\b|ultrasound|echo", "IMAGING_REPORT"),
    (r"handwritten|note", "HANDWRITTEN_NOTE"),
]


def store_upload(patient_id: int, filename: str, data: bytes) -> Dict[str, Any]:
    safe = sanitize_filename(filename)
    folder = STORAGE_DIR / f"patient_{patient_id}"
    folder.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex[:10]}_{safe}"
    path = folder / stored_name
    path.write_bytes(data)
    return {"path": str(path), "stored_name": stored_name, "size": len(data)}


def guess_document_type(filename: str, text: str = "") -> str:
    haystack = f"{filename} {text[:500]}".lower()
    for pattern, label in DOCUMENT_TYPE_HINTS:
        if re.search(pattern, haystack):
            return label
    return "OTHER"


def create_document(
    db: Session,
    patient_id: int,
    filename: str,
    stored_path: Optional[str],
    mime_type: str,
    size_bytes: int,
    uploaded_by_user_id: Optional[int],
    document_type: str = "OTHER",
    is_handwritten: bool = False,
    source_type: str = "SCANNED_DOCUMENT",
    notes: Optional[str] = None,
    commit: bool = True,
) -> Document:
    document = Document(
        patient_id=patient_id,
        filename=filename,
        stored_path=stored_path,
        mime_type=mime_type,
        size_bytes=size_bytes,
        document_type=document_type,
        is_handwritten=is_handwritten,
        source_type=source_type,
        uploaded_by_user_id=uploaded_by_user_id,
        notes=notes,
        ocr_status="PENDING",
    )
    db.add(document)
    db.flush()
    if commit:
        db.commit()
        db.refresh(document)
    return document


# ---------------------------------------------------------------------------
def route_to_doctor(
    db: Session,
    patient: Patient,
    doctor_entity: Optional[Dict[str, Any]],
    document: Optional[Document] = None,
    actor=None,
) -> Dict[str, Any]:
    """
    §17 / §18 — associate the record with the doctor named in it.

    A doctor account is never fabricated. If the named doctor is not a
    registered user, the record is linked to an EXTERNAL provider entry so the
    provenance is preserved and the doctor can be matched later.
    """
    if not doctor_entity or not doctor_entity.get("name"):
        return {"routed": False, "reason": "No doctor identified in the record."}

    raw_name = doctor_entity["name"].strip()
    normalised = re.sub(r"^dr\.?\s*", "", raw_name, flags=re.I).strip().lower()

    doctor = None
    for candidate in db.query(Doctor).all():
        candidate_name = re.sub(
            r"^dr\.?\s*", "", candidate.full_name or "", flags=re.I
        ).strip().lower()
        if candidate_name == normalised or (
            normalised and normalised in candidate_name
        ) or (candidate_name and candidate_name in normalised):
            doctor = candidate
            break

    created_external = False
    if not doctor:
        doctor = Doctor(
            full_name=raw_name if raw_name.lower().startswith("dr") else f"Dr. {raw_name}",
            specialty=doctor_entity.get("specialty"),
            hospital=doctor_entity.get("hospital"),
            registration_no=doctor_entity.get("registration_no"),
            is_registered=False,
        )
        db.add(doctor)
        db.flush()
        created_external = True
    else:
        doctor.specialty = doctor.specialty or doctor_entity.get("specialty")
        doctor.hospital = doctor.hospital or doctor_entity.get("hospital")

    if document is not None:
        document.doctor_id = doctor.id
        document.doctor_name_raw = raw_name

    consent_ok = "FULL_HEALTH_MEMORY" in consent_service.allowed_scopes(
        db, patient.id, "doctor"
    ) or "RECENT_HISTORY" in consent_service.allowed_scopes(db, patient.id, "doctor")

    # The doctor named in a record is never given access here. Only the patient
    # adds a doctor to their care team, so routing records a suggestion the
    # patient can accept (or an already-active relationship it belongs to).
    relationship = None
    if doctor.is_registered:
        relationship = doctor_relationship_service.suggest_doctor(
            db, patient, doctor, document_id=getattr(document, "id", None)
        )

    db.flush()
    if relationship == doctor_relationship_service.ACTIVE:
        status = "ASSIGNED"
    elif not doctor.is_registered:
        status = "EXTERNAL_NOT_REGISTERED"
    elif not consent_ok:
        status = "CONSENT_REQUIRED"
    else:
        status = "SUGGESTED_TO_PATIENT"
    assigned = status == "ASSIGNED"
    audit_service.log(
        db, "DOCTOR_ROUTING", actor, patient_id=patient.id,
        target=doctor.full_name,
        detail=f"status={status}; source_document={getattr(document, 'filename', None)}",
        commit=False,
    )
    return {
        "routed": assigned,
        "status": status,
        "doctor": {
            "id": doctor.id,
            "name": doctor.full_name,
            "specialty": doctor.specialty,
            "hospital": doctor.hospital,
            "is_registered": doctor.is_registered,
            "created_external": created_external,
        },
        "consent_granted": consent_ok,
        "message": {
            "ASSIGNED": (
                "Routed to a doctor already on the patient's care team."
            ),
            "SUGGESTED_TO_PATIENT": (
                "Doctor identified from the medical record and suggested to the "
                "patient. They receive nothing until the patient adds them."
            ),
            "EXTERNAL_NOT_REGISTERED": (
                "Doctor identified from the medical record. "
                "Status: External / Not Registered."
            ),
            "CONSENT_REQUIRED": (
                "Doctor is registered but the patient has not granted consent."
            ),
        }[status],
    }


# ---------------------------------------------------------------------------
def serialize_document(db: Session, document: Document) -> Dict[str, Any]:
    doctor = (
        db.query(Doctor).filter(Doctor.id == document.doctor_id).first()
        if document.doctor_id
        else None
    )
    ocr = document.ocr_result
    return {
        "document_id": document.id,
        "patient_id": document.patient_id,
        "filename": document.filename,
        "document_type": document.document_type,
        "is_handwritten": document.is_handwritten,
        "mime_type": document.mime_type,
        "size_bytes": document.size_bytes,
        "upload_date": iso(document.upload_date),
        "source": document.source_type,
        "ocr_status": document.ocr_status,
        "ocr_engine": document.ocr_engine,
        "confidence": document.confidence,
        "verification_status": document.verification_status,
        "doctor": doctor.full_name if doctor else document.doctor_name_raw,
        "doctor_id": document.doctor_id,
        "notes": document.notes,
        "has_file": bool(document.stored_path and Path(document.stored_path).exists()),
        "ocr": (
            {
                "engine": ocr.engine,
                "raw_text": ocr.raw_text,
                "overall_confidence": ocr.overall_confidence,
                "handwriting_detected": ocr.handwriting_detected,
                "fields": ocr.fields or [],
                "processed_at": iso(ocr.processed_at),
            }
            if ocr
            else None
        ),
    }


def list_documents(db: Session, patient_id: int) -> List[Dict[str, Any]]:
    documents = (
        db.query(Document)
        .filter(Document.patient_id == patient_id)
        .order_by(Document.upload_date.desc())
        .all()
    )
    return [serialize_document(db, document) for document in documents]


def file_response_path(document: Document) -> Optional[Path]:
    if not document.stored_path:
        return None
    path = Path(document.stored_path)
    return path if path.exists() else None
