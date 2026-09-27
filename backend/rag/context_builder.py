"""
Context assembly (§19).

Turns retrieved chunks into (a) a labelled text block for the agent and
(b) the evidence list the UI shows next to every answer. Provenance labels
travel with the text so a model can never present OCR uncertainty or a
patient-reported symptom as a doctor-confirmed fact.
"""

from typing import Any, Dict, List

from rag.retriever import RetrievedChunk
from utils.helpers import human_date, percent

MAX_CONTEXT_CHARS = 6000


def _label(chunk) -> str:
    bits = [chunk.trust_level or chunk.source_type]
    status = (chunk.verification_status or "NOT_REQUIRED").upper()
    if status == "PENDING_VERIFICATION":
        bits.append("UNVERIFIED — pending reviewer verification")
    elif status in {"VERIFIED", "CORRECTED"}:
        bits.append("reviewer verified")
    if chunk.confidence is not None and chunk.confidence < 0.85:
        bits.append(f"confidence {percent(chunk.confidence)}")
    if chunk.author:
        bits.append(f"recorded by {chunk.author}")
    return " | ".join(bits)


def build(
    retrieved: List[RetrievedChunk],
    patient: Any = None,
    header_extras: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    lines: List[str] = []
    if patient is not None:
        lines.append(
            f"PATIENT: {patient.full_name}"
            f"{f', age {patient.age}' if patient.age else ''}"
            f"{f', blood group {patient.blood_group}' if patient.blood_group else ''}"
        )
    for key, value in (header_extras or {}).items():
        lines.append(f"{key.upper()}: {value}")

    lines.append("")
    lines.append("RETRIEVED HEALTH MEMORY (authorized subset only):")

    used: List[RetrievedChunk] = []
    total = sum(len(line) for line in lines)
    for index, item in enumerate(retrieved, start=1):
        chunk = item.chunk
        block = (
            f"\n[{index}] {chunk.title or 'Health memory entry'}"
            f" — {human_date(chunk.event_date)}\n"
            f"    provenance: {_label(chunk)}\n"
            f"    {chunk.text.strip()}"
        )
        if total + len(block) > MAX_CONTEXT_CHARS:
            break
        lines.append(block)
        used.append(item)
        total += len(block)

    if not used:
        lines.append("\n(No authorized health-memory records matched this question.)")

    return {
        "context_text": "\n".join(lines),
        "sources": [item.to_source() for item in used],
        "chunks_used": len(used),
        "chunks_considered": len(retrieved),
    }


def evidence_panel(sources: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Compact 'Sources used' list for the UI."""
    panel = []
    for source in sources:
        panel.append(
            {
                "title": source.get("title") or "Health memory entry",
                "source_type": source.get("source_type", ""),
                "date": (source.get("date") or "")[:10],
                "trust_level": source.get("trust_level") or "",
                "confidence": percent(source.get("confidence")),
                "verification_status": source.get("verification_status") or "",
                "excerpt": source.get("excerpt") or "",
            }
        )
    return panel


def group_by_type(retrieved: List[RetrievedChunk]) -> Dict[str, List[RetrievedChunk]]:
    grouped: Dict[str, List[RetrievedChunk]] = {}
    for item in retrieved:
        grouped.setdefault(item.chunk.source_type, []).append(item)
    return grouped
