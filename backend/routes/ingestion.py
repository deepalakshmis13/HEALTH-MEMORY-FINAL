"""Ingestion routes — TEXT, VOICE and SCAN & UPLOAD enter the same pipeline."""

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from database import Session

from auth import Principal, get_current_user
from database import get_db
from schemas import TextIngestionRequest, VoiceIngestionRequest
from services import audit_service, document_service, ingestion_service
from services.authorization_service import require_patient_access
from utils.security import validate_upload

router = APIRouter(prefix="/api/ingestion", tags=["ingestion"])


@router.post("/text")
def ingest_text(
    payload: TextIngestionRequest,
    principal: Principal = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    context = require_patient_access(db, principal, payload.patient_id)
    return ingestion_service.ingest_text(
        db, context.patient, payload.text, principal, payload.entry_date
    )


@router.post("/voice")
def ingest_voice(
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


@router.post("/upload")
async def ingest_upload(
    patient_id: int = Form(...),
    file: UploadFile = File(...),
    is_handwritten: Optional[str] = Form(None),
    document_type: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    principal: Principal = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    context = require_patient_access(db, principal, patient_id)

    data = await file.read()
    ok, message = validate_upload(file.filename, len(data))
    if not ok:
        raise HTTPException(status_code=400, detail=message)

    stored = document_service.store_upload(patient_id, file.filename, data)
    declared = None
    if is_handwritten is not None and is_handwritten != "":
        declared = str(is_handwritten).lower() in {"true", "1", "yes", "on"}

    document = document_service.create_document(
        db, patient_id,
        filename=file.filename,
        stored_path=stored["path"],
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=stored["size"],
        uploaded_by_user_id=principal.id,
        document_type=document_type or document_service.guess_document_type(file.filename),
        is_handwritten=bool(declared),
        notes=notes,
        commit=False,
    )
    audit_service.log(
        db, "DOCUMENT_UPLOAD", principal, patient_id=patient_id,
        target=file.filename, detail=f"{stored['size']} bytes", commit=False,
    )
    db.commit()

    result = ingestion_service.ingest_document(
        db, context.patient, document, principal, declared_handwritten=declared
    )
    if not result.get("ok"):
        raise HTTPException(status_code=422, detail=result.get("message"))
    return result
