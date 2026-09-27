"""Doctor agent — "Clinical Health Memory Assistant" (§22, §29)."""

from datetime import datetime, timedelta
from typing import Any, Dict, List

from database import Session

from agents import memory_agent
from agents.memory_agent import MemoryBundle, format_medication_line
from models import (
    CaregiverObservation,
    DoctorConsultation,
    MemoryEvent,
    VerificationTask,
)
from utils.helpers import human_date, percent, truncate

NAME = "Clinical Health Memory Assistant"

SYSTEM_PROMPT = (
    "You are the Clinical Health Memory Assistant for a treating physician. "
    "Write in concise clinical register with clear headings. Distinguish "
    "explicitly between doctor-recorded findings, reviewer-verified data, "
    "OCR-extracted data pending verification, caregiver observations and "
    "patient-reported information. Do not diagnose, do not prescribe, and do "
    "not present any AI-assembled statement as a confirmed medical record."
)

QUICK_ACTIONS = [
    "Summarize this patient's recent history.",
    "What changed since the last visit?",
    "Show recent medication changes.",
    "What caregiver observations are important?",
    "Generate a visit summary.",
]


def _last_consultation(db: Session, patient_id: int):
    return (
        db.query(DoctorConsultation)
        .filter(DoctorConsultation.patient_id == patient_id)
        .order_by(DoctorConsultation.consulted_on.desc())
        .first()
    )


def compose(db: Session, bundle: MemoryBundle) -> str:
    intent = bundle.intent
    overview = bundle.overview
    patient_id = bundle.context.patient_id

    if intent in {"medication_changes", "medications"}:
        changes = (
            db.query(MemoryEvent)
            .filter(
                MemoryEvent.patient_id == patient_id,
                MemoryEvent.event_type.in_(["MEDICATION_CHANGE", "MEDICATION"]),
            )
            .order_by(MemoryEvent.event_date.desc())
            .limit(8)
            .all()
        )
        lines = ["CURRENT MEDICATIONS", ""]
        medications = overview.get("medications", [])
        if medications:
            for medication in medications:
                lines.append(f"• {format_medication_line(medication)}")
        else:
            lines.append("• None recorded in health memory.")
        lines += ["", "RECENT MEDICATION EVENTS", ""]
        if changes:
            for event in changes:
                marker = (
                    " [PENDING VERIFICATION]"
                    if event.verification_status == "PENDING_VERIFICATION"
                    else ""
                )
                lines.append(
                    f"• {human_date(event.event_date)} — {event.title}"
                    f" ({event.trust_level}, {percent(event.confidence)}){marker}"
                )
        else:
            lines.append("• No medication events in the retrieved window.")
        return "\n".join(lines)

    if intent in {"changes_since", "last_visit", "summary"}:
        last = _last_consultation(db, patient_id)
        cutoff = last.consulted_on if last else datetime.utcnow() - timedelta(days=45)
        since_events = (
            db.query(MemoryEvent)
            .filter(
                MemoryEvent.patient_id == patient_id,
                MemoryEvent.event_date >= cutoff,
            )
            .order_by(MemoryEvent.event_date.desc())
            .limit(20)
            .all()
        )
        lines = []
        if last:
            lines += [
                f"REFERENCE VISIT — {human_date(last.consulted_on)}",
                f"Reason: {last.reason or 'not recorded'}",
                f"Findings: {truncate(last.findings or 'not recorded', 240)}",
                "",
            ]
        lines.append(
            "CHANGES SINCE THAT VISIT" if last else "RECENT LONGITUDINAL ACTIVITY"
        )
        lines.append("")
        if not since_events:
            lines.append("• No new health-memory entries in this window.")
        grouped: Dict[str, List[MemoryEvent]] = {}
        for event in since_events:
            grouped.setdefault(event.event_type, []).append(event)
        order = [
            "MEDICATION_CHANGE", "MEDICATION", "DIAGNOSIS", "LAB_RESULT",
            "SYMPTOM", "OBSERVATION", "CONSULTATION", "DOCUMENT",
            "MEDICATION_ADMINISTRATION", "VOICE_ENTRY", "ALLERGY", "NOTE",
        ]
        for event_type in order:
            events = grouped.get(event_type)
            if not events:
                continue
            lines.append(f"{event_type.replace('_', ' ').title()}:")
            for event in events[:4]:
                flag = (
                    " [unverified OCR]"
                    if event.verification_status == "PENDING_VERIFICATION"
                    else ""
                )
                lines.append(
                    f"  • {human_date(event.event_date)} — {event.title} "
                    f"({event.trust_level}){flag}"
                )
            lines.append("")
        return "\n".join(lines).strip()

    if intent == "observations":
        observations = (
            db.query(CaregiverObservation)
            .filter(CaregiverObservation.patient_id == patient_id)
            .order_by(CaregiverObservation.observed_at.desc())
            .limit(10)
            .all()
        )
        if not observations:
            return "No caregiver observations are recorded for this patient."
        lines = ["CAREGIVER OBSERVATIONS (most recent first)", ""]
        for observation in observations:
            marker = "  ** " if observation.severity != "normal" else "  • "
            lines.append(
                f"{marker}{human_date(observation.observed_at)} "
                f"[{observation.category}] {observation.observation}"
            )
        flagged = [o for o in observations if o.severity != "normal"]
        if flagged:
            lines += [
                "",
                f"{len(flagged)} observation(s) flagged for attention — marked **.",
            ]
        return "\n".join(lines)

    if intent == "labs":
        labs = overview.get("lab_results", [])
        if not labs:
            return "No laboratory results are recorded in this patient's health memory."
        lines = ["LABORATORY RESULTS", ""]
        for lab in labs:
            flag = f"  [{lab['flag'].upper()}]" if lab["flag"] != "normal" else ""
            reference = lab.get("reference_range")
            reference_text = f" (ref {reference})" if reference else ""
            tested_on = human_date(
                datetime.fromisoformat(lab["tested_on"]) if lab.get("tested_on") else None
            )
            lines.append(
                f"• {tested_on} — {lab['test_name']}: "
                f"{lab['value']} {lab.get('unit') or ''}{reference_text}{flag}"
            )
        return "\n".join(lines)

    if intent == "verification":
        tasks = (
            db.query(VerificationTask)
            .filter(VerificationTask.patient_id == patient_id)
            .order_by(VerificationTask.created_at.desc())
            .limit(10)
            .all()
        )
        if not tasks:
            return "No OCR fields for this patient required reviewer verification."
        lines = ["OCR VERIFICATION ACTIVITY", ""]
        for task in tasks:
            resolution = (
                f"{task.result.action} -> '{task.result.corrected_value}' "
                f"by {task.result.reviewer_name}"
                if task.result
                else "pending"
            )
            lines.append(
                f"• {task.field_label}: OCR read '{task.extracted_value}' at "
                f"{percent(task.confidence)} — {resolution}"
            )
        return "\n".join(lines)

    if not bundle.has_records():
        return memory_agent.no_records_message("doctor")

    lines = ["RETRIEVED HEALTH MEMORY", ""]
    for item in bundle.retrieved[:6]:
        chunk = item.chunk
        lines.append(
            f"• {human_date(chunk.event_date)} — {chunk.title} "
            f"({chunk.trust_level}, {percent(chunk.confidence)})"
        )
        lines.append(f"  {truncate(chunk.text, 260)}")
    return "\n".join(lines)


def build(db: Session, bundle: MemoryBundle) -> Dict[str, Any]:
    return {
        "agent": NAME,
        "system_prompt": SYSTEM_PROMPT,
        "grounded_draft": compose(db, bundle),
        "quick_actions": QUICK_ACTIONS,
    }
