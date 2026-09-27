"""Reviewer agent — "Medication Memory Assistant" (§22)."""

from typing import Any, Dict

from database import Session

from agents import memory_agent
from agents.memory_agent import MemoryBundle, format_medication_line
from models import Document, MemoryEvent, OCRResult, Prescription, VerificationTask
from utils.helpers import human_date, human_datetime, percent, truncate

NAME = "Medication Memory Assistant"

SYSTEM_PROMPT = (
    "You are the Medication Memory Assistant for a verifying reviewer. Be "
    "precise and factual about medication names, doses, frequencies, OCR "
    "readings and confidence scores. Always quote the original OCR text and "
    "its confidence next to any corrected value. Never guess what an illegible "
    "reading says — say it needs confirmation from the prescriber."
)

QUICK_ACTIONS = [
    "Which medication entries require verification?",
    "What medication changes are recorded?",
    "Show prescription history.",
    "What did the OCR extract?",
    "What needs confirmation?",
]


def compose(db: Session, bundle: MemoryBundle) -> str:
    intent = bundle.intent
    patient_id = bundle.context.patient_id
    overview = bundle.overview

    if intent == "verification" or "confirm" in (bundle.question or "").lower():
        tasks = (
            db.query(VerificationTask)
            .filter(VerificationTask.patient_id == patient_id)
            .order_by(VerificationTask.created_at.desc())
            .limit(20)
            .all()
        )
        pending = [t for t in tasks if t.status == "PENDING_VERIFICATION"]
        resolved = [t for t in tasks if t.status != "PENDING_VERIFICATION"]

        lines = [f"VERIFICATION STATUS — {bundle.patient.full_name}", ""]
        if pending:
            lines.append(f"PENDING ({len(pending)}):")
            for task in pending:
                lines.append(
                    f"  • [{task.priority}] {task.field_label}: OCR read "
                    f"'{task.extracted_value}' at {percent(task.confidence)}"
                )
                lines.append(f"    {task.reason}")
        else:
            lines.append("PENDING: none — the queue is clear for this patient.")

        if resolved:
            lines += ["", f"RESOLVED ({len(resolved)}):"]
            for task in resolved:
                result = task.result
                if not result:
                    continue
                lines.append(
                    f"  • {task.field_label}: '{result.original_value}' "
                    f"({percent(result.original_confidence)}) -> "
                    f"'{result.corrected_value or '—'}' — {result.action} by "
                    f"{result.reviewer_name} on "
                    f"{human_datetime(result.verified_at)}"
                )
        return "\n".join(lines)

    if intent in {"medications", "medication_changes"}:
        medications = overview.get("medications", [])
        lines = [f"MEDICATION RECORD — {bundle.patient.full_name}", ""]
        if medications:
            for medication in medications:
                lines.append(f"  • {format_medication_line(medication)}")
                if medication.get("prescriber"):
                    lines.append(f"    Prescriber: {medication['prescriber']}")
        else:
            lines.append("  • No active medications recorded.")

        changes = (
            db.query(MemoryEvent)
            .filter(
                MemoryEvent.patient_id == patient_id,
                MemoryEvent.event_type == "MEDICATION_CHANGE",
            )
            .order_by(MemoryEvent.event_date.desc())
            .limit(6)
            .all()
        )
        if changes:
            lines += ["", "RECORDED MEDICATION CHANGES:"]
            for event in changes:
                lines.append(
                    f"  • {human_date(event.event_date)} — {event.title} "
                    f"({event.trust_level}, {percent(event.confidence)})"
                )
        return "\n".join(lines)

    if "prescription" in (bundle.question or "").lower() or intent == "summary":
        prescriptions = (
            db.query(Prescription)
            .filter(Prescription.patient_id == patient_id)
            .order_by(Prescription.issued_on.desc())
            .limit(8)
            .all()
        )
        if not prescriptions:
            return "No prescriptions are recorded for this patient."
        lines = [f"PRESCRIPTION HISTORY — {bundle.patient.full_name}", ""]
        for prescription in prescriptions:
            lines.append(
                f"  • {human_date(prescription.issued_on)} "
                f"({prescription.source_type}, {prescription.verification_status})"
            )
            for item in prescription.items or []:
                bits = [item.get("name") or "?"]
                if item.get("dose"):
                    bits.append(item["dose"])
                if item.get("frequency"):
                    bits.append(item["frequency"])
                lines.append(
                    f"      – {' / '.join(bits)} "
                    f"({percent(item.get('confidence'))})"
                )
        return "\n".join(lines)

    if "ocr" in (bundle.question or "").lower() or intent == "labs":
        document_ids = [
            doc.id
            for doc in db.query(Document).filter(Document.patient_id == patient_id).all()
        ]
        results = (
            db.query(OCRResult)
            .filter(OCRResult.document_id.in_(document_ids))
            .order_by(OCRResult.processed_at.desc())
            .limit(4)
            .all()
        ) if document_ids else []
        if not results:
            return "No OCR-processed documents exist for this patient."
        lines = ["OCR EXTRACTION DETAIL", ""]
        for result in results:
            document = (
                db.query(Document).filter(Document.id == result.document_id).first()
            )
            lines.append(
                f"  Document: {document.filename if document else result.document_id}"
                f" ({'handwritten' if result.handwriting_detected else 'printed'})"
            )
            lines.append(f"  Engine: {result.engine}")
            lines.append(
                f"  Overall confidence: {percent(result.overall_confidence)}"
            )
            for field in (result.fields or [])[:8]:
                flag = " <-- needs verification" if field.get("needs_verification") else ""
                lines.append(
                    f"      {field['label']}: {field['value']} "
                    f"({percent(field['confidence'])}){flag}"
                )
            lines.append(f"  Raw text: {truncate(result.raw_text or '', 200)}")
            lines.append("")
        return "\n".join(lines).strip()

    if not bundle.has_records():
        return memory_agent.no_records_message("reviewer")

    lines = ["RETRIEVED MEDICATION MEMORY", ""]
    for item in bundle.retrieved[:5]:
        chunk = item.chunk
        lines.append(
            f"  • {human_date(chunk.event_date)} — {chunk.title} "
            f"({chunk.trust_level}, {percent(chunk.confidence)}, "
            f"{chunk.verification_status})"
        )
        lines.append(f"    {truncate(chunk.text, 220)}")
    return "\n".join(lines)


def build(db: Session, bundle: MemoryBundle) -> Dict[str, Any]:
    return {
        "agent": NAME,
        "system_prompt": SYSTEM_PROMPT,
        "grounded_draft": compose(db, bundle),
        "quick_actions": QUICK_ACTIONS,
    }
