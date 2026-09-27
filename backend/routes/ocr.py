"""OCR routes — reprocess a document and inspect its extraction."""

from fastapi import APIRouter, Depends, HTTPException
from database import Session

from auth import Principal, get_current_user
from config import HIGH_CONFIDENCE_THRESHOLD, MEDIUM_CONFIDENCE_THRESHOLD
from database import get_db
from models import Document, OCRResult
from ocr.ocr_service import ocr_service
from services import ingestion_service
from services.authorization_service import require_patient_access

router = APIRouter(prefix="/api/ocr", tags=["ocr"])


@router.get("/engines")
def engines():
    return {
        "engines": ocr_service.engines,
        "thresholds": {
            "high_confidence": HIGH_CONFIDENCE_THRESHOLD,
            "medium_confidence": MEDIUM_CONFIDENCE_THRESHOLD,
        },
        "note": (
            "PrintedOCR and HandwritingOCR use pytesseract when it is installed; "
            "otherwise they run in a clearly-labelled demo mode that reproduces "
            "realistic recognition noise and confidence."
        ),
    }


@router.post("/process")
def process_document(
    document_id: int,
    is_handwritten: bool | None = None,
    principal: Principal = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    context = require_patient_access(db, principal, document.patient_id)

    if document.ocr_result:
        db.delete(document.ocr_result)
        db.flush()

    result = ingestion_service.ingest_document(
        db, context.patient, document, principal, declared_handwritten=is_handwritten
    )
    if not result.get("ok"):
        raise HTTPException(status_code=422, detail=result.get("message"))
    return result


@router.get("/{document_id}")
def get_ocr_result(
    document_id: int,
    principal: Principal = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    require_patient_access(db, principal, document.patient_id)

    result = (
        db.query(OCRResult).filter(OCRResult.document_id == document_id).first()
    )
    if not result:
        raise HTTPException(
            status_code=404, detail="This document has not been processed yet."
        )
    return {
        "document_id": document_id,
        "filename": document.filename,
        "document_type": document.document_type,
        "document_type_label": (
            "Handwritten Doctor Report" if result.handwriting_detected
            else "Printed Document"
        ),
        "ocr_status": document.ocr_status,
        "engine": result.engine,
        "handwriting_detected": result.handwriting_detected,
        "recognition_confidence": result.overall_confidence,
        "raw_text": result.raw_text,
        "fields": result.fields or [],
        "verification_status": document.verification_status,
        "processed_at": result.processed_at.isoformat() if result.processed_at else None,
    }
