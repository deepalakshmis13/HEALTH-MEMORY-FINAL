"""Patient / Guardian agent — "My Health Memory Assistant" (§22)."""

from datetime import datetime
from typing import Any, Dict, List

from database import Session

from agents import memory_agent
from agents.memory_agent import MemoryBundle, format_medication_line
from utils.helpers import human_date, truncate

NAME = "My Health Memory Assistant"

SYSTEM_PROMPT = (
    "You are My Health Memory Assistant, speaking directly to an elderly "
    "patient or their guardian. Use short sentences and everyday words. Never "
    "use medical jargon without explaining it. Never give medical advice, "
    "never suggest a dose change, and always tell the person to ask their "
    "doctor for decisions. Say clearly when something is still waiting to be "
    "checked by a reviewer."
)

QUICK_ACTIONS = [
    "What medicines am I taking?",
    "What happened during my last visit?",
    "What did my doctor recommend?",
    "What health information was recently added?",
    "What allergies are recorded?",
]


def compose(db: Session, bundle: MemoryBundle) -> str:
    intent = bundle.intent
    overview = bundle.overview

    if intent == "medications":
        medications = overview.get("medications", [])
        if not medications:
            return (
                "I do not have any medicines saved in your health memory yet. "
                "You can add them with Text, Voice, or by scanning your "
                "prescription."
            )
        lines = ["Here are the medicines recorded in your health memory:", ""]
        for medication in medications:
            lines.append(f"• {format_medication_line(medication, plain=True)}")
        pending = [
            m for m in medications
            if m.get("verification_status") == "PENDING_VERIFICATION"
        ]
        if pending:
            lines += [
                "",
                f"{len(pending)} of these came from a scanned document and is "
                "still being checked by a reviewer. Please do not change how "
                "you take it until it is confirmed.",
            ]
        lines += ["", "Always take your medicines exactly as your doctor told you."]
        return "\n".join(lines)

    if intent == "allergies":
        allergies = overview.get("allergies", [])
        if not allergies:
            return "No allergies are recorded in your health memory."
        lines = ["These allergies are recorded in your health memory:", ""]
        for allergy in allergies:
            detail = f" — reaction: {allergy['reaction']}" if allergy.get("reaction") else ""
            lines.append(f"• {allergy['substance']}{detail}")
        lines += ["", "Please tell any new doctor about these before treatment."]
        return "\n".join(lines)

    if intent in {"last_visit", "recommendations"}:
        visits = [
            item for item in bundle.retrieved
            if item.chunk.source_type in {
                "DOCTOR_DOCUMENT", "HANDWRITTEN_DOCUMENT", "DOCTOR_RECORDED",
                "SCANNED_DOCUMENT", "PATIENT_TEXT", "PATIENT_VOICE",
            }
            and ("consult" in (item.chunk.title or "").lower()
                 or "doctor" in (item.chunk.text or "").lower())
        ]
        if not visits:
            visits = bundle.retrieved[:3]
        if not visits:
            return memory_agent.no_records_message("patient")
        lines = ["Here is what your health memory has about your recent visit:", ""]
        for item in visits[:3]:
            chunk = item.chunk
            lines.append(f"• {human_date(chunk.event_date)} — {chunk.title}")
            lines.append(f"  {truncate(chunk.text, 260)}")
        advice = [
            item for item in bundle.retrieved
            if any(
                word in (item.chunk.text or "").lower()
                for word in ("advis", "recommend", "review", "monitor", "continue")
            )
        ]
        if advice and intent == "recommendations":
            lines += ["", "What your doctor asked you to do:"]
            for item in advice[:3]:
                lines.append(f"• {truncate(item.chunk.text, 200)}")
        lines += ["", "If anything here looks wrong, please tell your doctor."]
        return "\n".join(lines)

    if intent == "recent_additions":
        recent = sorted(
            bundle.retrieved,
            key=lambda item: item.chunk.event_date or datetime.min,
            reverse=True,
        )[:6]
        if not recent:
            return memory_agent.no_records_message("patient")
        lines = ["This is what was added to your health memory most recently:", ""]
        for item in recent:
            chunk = item.chunk
            source = {
                "PATIENT_TEXT": "you typed it",
                "PATIENT_VOICE": "you recorded it by voice",
                "HANDWRITTEN_DOCUMENT": "a handwritten doctor's note you scanned",
                "SCANNED_DOCUMENT": "a document you uploaded",
                "DOCTOR_DOCUMENT": "a doctor's report",
                "DOCTOR_RECORDED": "your doctor",
                "CAREGIVER_RECORDED": "your caregiver",
                "REVIEWER_VERIFIED": "a reviewer check",
            }.get(chunk.source_type, chunk.source_type.replace("_", " ").lower())
            lines.append(
                f"• {human_date(chunk.event_date)} — {chunk.title} (from {source})"
            )
        return "\n".join(lines)

    if intent == "labs":
        labs = overview.get("lab_results", [])
        if not labs:
            return "There are no laboratory results in your health memory yet."
        lines = ["Your most recent test results:", ""]
        for lab in labs[:6]:
            flag = "" if lab["flag"] == "normal" else f" ({lab['flag']})"
            lines.append(
                f"• {lab['test_name']}: {lab['value']} {lab.get('unit') or ''}{flag}"
            )
        lines += ["", "Your doctor is the right person to explain what these mean."]
        return "\n".join(lines)

    if intent == "emergency":
        patient = bundle.patient
        lines = [
            "Your emergency information:",
            "",
            f"• Name: {patient.full_name}",
            f"• Age: {patient.age}",
            f"• Blood group: {patient.blood_group or 'not recorded'}",
        ]
        allergies = overview.get("allergies", [])
        lines.append(
            "• Allergies: "
            + (", ".join(a["substance"] for a in allergies) if allergies else "none recorded")
        )
        if patient.emergency_contact_name:
            lines.append(
                f"• Emergency contact: {patient.emergency_contact_name} "
                f"({patient.emergency_contact_relation}) — "
                f"{patient.emergency_contact_phone}"
            )
        return "\n".join(lines)

    # general
    if not bundle.has_records():
        return memory_agent.no_records_message("patient")
    lines = ["Here is what your health memory has about that:", ""]
    for item in bundle.retrieved[:4]:
        chunk = item.chunk
        lines.append(f"• {human_date(chunk.event_date)} — {chunk.title}")
        lines.append(f"  {truncate(chunk.text, 240)}")
    lines += ["", "For anything medical, please check with your doctor."]
    return "\n".join(lines)


def build(db: Session, bundle: MemoryBundle) -> Dict[str, Any]:
    return {
        "agent": NAME,
        "system_prompt": SYSTEM_PROMPT,
        "grounded_draft": compose(db, bundle),
        "quick_actions": QUICK_ACTIONS,
    }
