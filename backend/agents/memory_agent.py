"""
MemoryAgent — the shared reasoning layer under all four role chatbots.

It never talks to the model. Its job is to (1) classify what is being asked,
(2) run the consent-aware retrieval, and (3) hand the role agent a bundle of
*facts that actually exist in the health memory*. Role agents then compose a
grounded draft; the AI provider only changes the wording.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from database import Session

from models import Patient
from rag import context_builder, retriever
from services import audit_service, memory_service
from services.authorization_service import AccessContext
from utils.helpers import human_date, percent

INTENTS = {
    "medications": [
        "medicine", "medicines", "medication", "medications", "tablet", "tablets",
        "drug", "drugs", "dose", "dosage", "taking", "prescribed", "prescription",
    ],
    "medication_changes": [
        "change", "changed", "changes", "switch", "switched", "increase",
        "increased", "reduce", "reduced", "stopped", "started", "new medicine",
    ],
    "last_visit": [
        "last visit", "last consultation", "previous visit", "saw the doctor",
        "visit summary", "recent visit", "what happened",
    ],
    "recommendations": [
        "recommend", "recommended", "advice", "advised", "told me", "instruction",
        "follow up", "follow-up",
    ],
    "recent_additions": [
        "recently added", "recent", "new information", "latest", "what was added",
        "updates", "update",
    ],
    "allergies": ["allergy", "allergies", "allergic", "reaction"],
    "verification": [
        "verify", "verification", "verified", "confirm", "confirmation", "queue",
        "pending", "low confidence", "ocr", "extract", "extracted",
    ],
    "shift": [
        "shift", "handover", "hand over", "previous shift", "night shift",
        "morning shift", "afternoon shift",
    ],
    "watch": [
        "watch", "watch for", "monitor", "look out", "careful", "attention",
        "risk", "today",
    ],
    "due": ["due", "schedule", "scheduled", "when", "time", "next dose"],
    "summary": ["summarize", "summarise", "summary", "overview", "history", "brief"],
    "changes_since": [
        "since the last visit", "since last visit", "what changed", "changed since",
        "new since",
    ],
    "labs": ["lab", "labs", "test", "result", "results", "blood", "report", "hba1c"],
    "observations": [
        "observation", "observations", "caregiver", "nurse", "noted", "behaviour",
        "behavior", "mood", "sleep", "meal",
    ],
    "emergency": ["emergency", "blood group", "critical", "urgent", "contact"],
}


@dataclass
class MemoryBundle:
    question: str
    intent: str
    patient: Patient
    context: AccessContext
    retrieved: List[retriever.RetrievedChunk]
    built: Dict[str, Any]
    overview: Dict[str, Any]
    filters: Dict[str, Any]
    extras: Dict[str, Any] = field(default_factory=dict)

    @property
    def sources(self) -> List[Dict[str, Any]]:
        return self.built["sources"]

    @property
    def context_text(self) -> str:
        return self.built["context_text"]

    def has_records(self) -> bool:
        return bool(self.built["sources"])


def classify_intent(question: str) -> str:
    lowered = (question or "").lower()
    best, score = "general", 0
    for intent, keywords in INTENTS.items():
        hits = sum(1 for keyword in keywords if keyword in lowered)
        # multi-word keywords are stronger evidence
        weight = sum(
            len(keyword.split()) for keyword in keywords if keyword in lowered
        )
        total = hits + weight
        if total > score:
            best, score = intent, total
    return best


def gather(
    db: Session,
    context: AccessContext,
    question: str,
    actor=None,
    top_k: int = 8,
    source_types: Optional[List[str]] = None,
    since_days: Optional[int] = None,
    extras: Optional[Dict[str, Any]] = None,
) -> MemoryBundle:
    intent = classify_intent(question)
    since = (
        datetime.utcnow() - timedelta(days=since_days) if since_days else None
    )

    retrieved = retriever.retrieve(
        db, context, question, top_k=top_k,
        source_types=source_types, since=since,
    )
    if not retrieved:
        retrieved = retriever.retrieve_recent(db, context, limit=min(top_k, 8))

    built = context_builder.build(retrieved, context.patient)
    overview = memory_service.overview(db, context.patient_id)

    if actor is not None:
        audit_service.log(
            db, "RAG_RETRIEVAL", actor, patient_id=context.patient_id,
            target=f"intent:{intent}",
            detail=(
                f"question='{(question or '')[:120]}'; "
                f"chunks_used={built['chunks_used']}; "
                f"scopes={sorted(context.scopes)}"
            ),
        )

    return MemoryBundle(
        question=question,
        intent=intent,
        patient=context.patient,
        context=context,
        retrieved=retrieved,
        built=built,
        overview=overview,
        filters=retriever.describe_filters(db, context),
        extras=extras or {},
    )


# --------------------------------------------------------------------------
# Shared formatting helpers used by the role agents
# --------------------------------------------------------------------------
def format_medication_line(medication: Dict[str, Any], plain: bool = False) -> str:
    bits = [medication["name"]]
    if medication.get("dose"):
        bits.append(medication["dose"])
    if medication.get("frequency"):
        bits.append(medication["frequency"])
    line = " — ".join(bits)
    status = medication.get("verification_status")
    if status == "PENDING_VERIFICATION":
        line += (
            " (awaiting reviewer verification — not yet confirmed)"
            if plain
            else f" [PENDING VERIFICATION, {percent(medication.get('confidence'))}]"
        )
    elif status in {"VERIFIED", "CORRECTED"}:
        line += " (reviewer verified)" if plain else " [reviewer verified]"
    return line


def recent_events(bundle: MemoryBundle, types: List[str], limit: int = 5):
    events = []
    for item in bundle.retrieved:
        if item.chunk.source_kind != "memory_event":
            continue
        events.append(item)
    return events[:limit]


def no_records_message(role: str) -> str:
    return {
        "patient": (
            "There is nothing in your health memory about that yet. "
            "You can add information using Text, Voice or Scan & Upload."
        ),
        "doctor": (
            "No authorized health-memory records matched that question for this "
            "patient. Consent scope and verification status may be limiting "
            "retrieval."
        ),
        "caregiver": (
            "No authorized care information matched that question for this "
            "resident."
        ),
        "reviewer": (
            "No medication records matched that question within the consent "
            "granted to reviewers."
        ),
    }.get(role, "No authorized records matched that question.")


def evidence_footer(bundle: MemoryBundle) -> str:
    if not bundle.sources:
        return ""
    lines = ["", "Sources used:"]
    for source in bundle.sources[:6]:
        date = human_date(
            datetime.fromisoformat(source["date"]) if source.get("date") else None
        )
        lines.append(
            f"• {source['title']} — {date} "
            f"({source.get('trust_level') or source['source_type']})"
        )
    return "\n".join(lines)
