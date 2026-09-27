"""
Chunking + index writing (§21).

Every chunk keeps the metadata the retriever needs to filter *before* the
model ever sees text: patient, source, date, author, confidence, verification
status and consent scope.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from database import Session

from config import RAG_CHUNK_OVERLAP, RAG_CHUNK_SIZE
from models import MemoryChunk
from rag.embeddings import embed


def split_text(text: str, size: int = RAG_CHUNK_SIZE, overlap: int = RAG_CHUNK_OVERLAP):
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]

    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        if end < len(text):
            window = text.rfind(". ", start + int(size * 0.5), end)
            if window == -1:
                window = text.rfind("\n", start + int(size * 0.5), end)
            if window != -1:
                end = window + 1
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return [chunk for chunk in chunks if chunk]


def index_text(
    db: Session,
    patient_id: int,
    source_id: str,
    source_type: str,
    text: str,
    title: str,
    event_date: Optional[datetime] = None,
    author: Optional[str] = None,
    doctor_id: Optional[int] = None,
    confidence: float = 1.0,
    verification_status: str = "NOT_REQUIRED",
    consent_scope: str = "FULL_HEALTH_MEMORY",
    trust_level: str = "AI Extracted",
    source_kind: str = "memory_event",
    commit: bool = True,
) -> List[MemoryChunk]:
    """(Re)index one source. Existing chunks for the same source_id are replaced."""
    db.query(MemoryChunk).filter(
        MemoryChunk.patient_id == patient_id,
        MemoryChunk.source_id == source_id,
    ).delete(synchronize_session=False)

    created: List[MemoryChunk] = []
    header = f"{title}. " if title else ""
    for index, piece in enumerate(split_text(text)):
        body = f"{header}{piece}" if index == 0 else piece
        chunk = MemoryChunk(
            patient_id=patient_id,
            source_id=source_id,
            source_type=source_type,
            source_kind=source_kind,
            text=body,
            title=title,
            event_date=event_date or datetime.utcnow(),
            author=author,
            doctor_id=doctor_id,
            confidence=confidence,
            verification_status=verification_status,
            consent_scope=consent_scope,
            trust_level=trust_level,
            vector=embed(f"{title} {body}"),
        )
        db.add(chunk)
        created.append(chunk)

    if commit:
        db.commit()
    return created


def remove_source(db: Session, patient_id: int, source_id: str, commit: bool = True):
    db.query(MemoryChunk).filter(
        MemoryChunk.patient_id == patient_id,
        MemoryChunk.source_id == source_id,
    ).delete(synchronize_session=False)
    if commit:
        db.commit()


def index_stats(db: Session, patient_id: Optional[int] = None) -> Dict[str, Any]:
    query = db.query(MemoryChunk)
    if patient_id:
        query = query.filter(MemoryChunk.patient_id == patient_id)
    chunks = query.all()
    by_type: Dict[str, int] = {}
    for chunk in chunks:
        by_type[chunk.source_type] = by_type.get(chunk.source_type, 0) + 1
    return {
        "chunks": len(chunks),
        "sources": len({c.source_id for c in chunks}),
        "by_source_type": by_type,
    }
