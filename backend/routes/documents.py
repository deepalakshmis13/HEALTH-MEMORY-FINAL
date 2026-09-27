"""Document management routes (§32)."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from database import Session

from auth import Principal, get_current_user
from database import get_db
from models import Document
from services import document_service
from services.authorization_service import require_patient_access

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("/patient/{patient_id}")
def list_patient_documents(
    patient_id: int,
    principal: Principal = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    context = require_patient_access(db, principal, patient_id)
    if principal.role != "patient" and not (
        {"DOCUMENTS", "FULL_HEALTH_MEMORY"} & context.scopes
    ):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view this information.",
        )
    documents = document_service.list_documents(db, patient_id)
    return {"patient_id": patient_id, "documents": documents, "count": len(documents)}


@router.get("/{document_id}")
def get_document(
    document_id: int,
    principal: Principal = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    require_patient_access(db, principal, document.patient_id)
    return document_service.serialize_document(db, document)


@router.get("/{document_id}/file")
def download_document(
    document_id: int,
    principal: Principal = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    require_patient_access(db, principal, document.patient_id)

    path = document_service.file_response_path(document)
    if not path:
        raise HTTPException(
            status_code=404, detail="The stored file for this document is unavailable."
        )
    if path.suffix.lower() == ".txt":
        return PlainTextResponse(path.read_text(encoding="utf-8", errors="ignore"))
    return FileResponse(
        str(path),
        media_type=document.mime_type or "application/octet-stream",
        filename=document.filename,
    )
