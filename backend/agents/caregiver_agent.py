"""Caregiver agent — "Care Companion" (§22, §26)."""

from datetime import datetime, timedelta
from typing import Any, Dict, List

from database import Session

from agents import memory_agent
from agents.memory_agent import MemoryBundle, format_medication_line
from models import (
    CareTask,
    CaregiverObservation,
    MedicationAdministration,
    MemoryEvent,
    Shift,
)
from utils.helpers import human_date, human_datetime, truncate

NAME = "Care Companion"

SYSTEM_PROMPT = (
    "You are Care Companion, assisting a caregiver or old-age-home staff "
    "member during a shift. Lead with what must be done and what must be "
    "watched. Be specific about medication, times and observations. Never "
    "give medical advice, never authorise a dose change, and always say when "
    "something must be escalated to the doctor or nurse-in-charge."
)

QUICK_ACTIONS = [
    "What medications are due?",
    "What happened during the previous shift?",
    "What should I watch today?",
    "Generate the shift handover.",
]


def _due_medications(db: Session, patient_id: int, shift_id=None):
    query = db.query(MedicationAdministration).filter(
        MedicationAdministration.patient_id == patient_id
    )
    if shift_id:
        query = query.filter(MedicationAdministration.shift_id == shift_id)
    return (
        query.order_by(MedicationAdministration.scheduled_time)
        .limit(40)
        .all()
    )


def compose(db: Session, bundle: MemoryBundle) -> str:
    intent = bundle.intent
    overview = bundle.overview
    patient_id = bundle.context.patient_id
    shift_id = bundle.extras.get("shift_id")

    if intent in {"due", "medications"}:
        administrations = _due_medications(db, patient_id, shift_id)
        pending = [a for a in administrations if a.status in {"Pending", "Delayed"}]
        lines = [f"MEDICATION FOR {bundle.patient.full_name.upper()}", ""]
        if pending:
            lines.append("Due / not yet given:")
            for item in pending:
                medication = item.medication
                lines.append(
                    f"  • {item.scheduled_time} — {medication.name} "
                    f"{medication.dose or ''} ({item.status})"
                )
        else:
            lines.append("No doses are currently pending for this shift.")

        done = [a for a in administrations if a.status == "Administered"]
        missed = [a for a in administrations if a.status in {"Missed", "Needs Attention"}]
        if done:
            lines += ["", f"Already administered this shift: {len(done)} dose(s)."]
        if missed:
            lines += ["", "NEEDS ATTENTION:"]
            for item in missed:
                lines.append(
                    f"  • {item.scheduled_time} — {item.medication.name} "
                    f"({item.status}) {item.notes or ''}"
                )
            lines.append("  Escalate missed doses to the nurse-in-charge.")

        unverified = [
            m for m in overview.get("medications", [])
            if m.get("verification_status") == "PENDING_VERIFICATION"
        ]
        if unverified:
            lines += [
                "",
                "Do not administer these — still awaiting reviewer verification:",
            ]
            for medication in unverified:
                lines.append(f"  • {format_medication_line(medication)}")
        return "\n".join(lines)

    if intent == "shift":
        previous = (
            db.query(Shift)
            .filter(Shift.status == "CLOSED")
            .order_by(Shift.created_at.desc())
            .first()
        )
        window_start = (
            previous.created_at if previous else datetime.utcnow() - timedelta(hours=12)
        )
        observations = (
            db.query(CaregiverObservation)
            .filter(
                CaregiverObservation.patient_id == patient_id,
                CaregiverObservation.observed_at >= window_start - timedelta(hours=12),
            )
            .order_by(CaregiverObservation.observed_at.desc())
            .limit(12)
            .all()
        )
        lines = ["PREVIOUS SHIFT — WHAT HAPPENED", ""]
        if previous:
            lines.append(
                f"Shift: {previous.shift_code} on {previous.shift_date} "
                f"({previous.start_time}–{previous.end_time})"
            )
            lines.append("")
        if observations:
            for observation in observations:
                lines.append(
                    f"  • {human_datetime(observation.observed_at)} "
                    f"[{observation.category}] {observation.observation}"
                )
        else:
            lines.append("  • No observations were recorded in the previous shift.")

        administrations = (
            db.query(MedicationAdministration)
            .filter(
                MedicationAdministration.patient_id == patient_id,
                MedicationAdministration.administered_at.isnot(None),
            )
            .order_by(MedicationAdministration.administered_at.desc())
            .limit(8)
            .all()
        )
        if administrations:
            lines += ["", "Medication recorded:"]
            for item in administrations:
                lines.append(
                    f"  • {item.scheduled_time} {item.medication.name} — {item.status}"
                )
        return "\n".join(lines)

    if intent == "watch":
        lines = [f"WATCH LIST FOR {bundle.patient.full_name.upper()}", ""]
        alerts = overview.get("alerts", [])
        if alerts:
            for alert in alerts:
                lines.append(f"  • [{alert['level'].upper()}] {alert['title']}")
                lines.append(f"    {alert['detail']}")
        recent_symptoms = (
            db.query(MemoryEvent)
            .filter(
                MemoryEvent.patient_id == patient_id,
                MemoryEvent.event_type.in_(["SYMPTOM", "OBSERVATION"]),
                MemoryEvent.event_date >= datetime.utcnow() - timedelta(days=7),
            )
            .order_by(MemoryEvent.event_date.desc())
            .limit(6)
            .all()
        )
        if recent_symptoms:
            lines += ["", "Recently reported by the resident or previous shift:"]
            for event in recent_symptoms:
                lines.append(
                    f"  • {human_date(event.event_date)} — {event.title} "
                    f"({event.trust_level})"
                )
        allergies = overview.get("allergies", [])
        if allergies:
            lines += [
                "",
                "Allergies: " + ", ".join(a["substance"] for a in allergies),
            ]
        tasks = (
            db.query(CareTask)
            .filter(CareTask.patient_id == patient_id, CareTask.status == "Pending")
            .order_by(CareTask.due_time)
            .limit(8)
            .all()
        )
        if tasks:
            lines += ["", "Pending care tasks:"]
            for task in tasks:
                lines.append(f"  • {task.due_time or '--:--'} {task.title}")
        if len(lines) <= 2:
            lines.append("  • Nothing flagged. Continue the routine care plan.")
        lines += ["", "Escalate anything new or worsening to the doctor on call."]
        return "\n".join(lines)

    if intent == "observations":
        observations = (
            db.query(CaregiverObservation)
            .filter(CaregiverObservation.patient_id == patient_id)
            .order_by(CaregiverObservation.observed_at.desc())
            .limit(10)
            .all()
        )
        if not observations:
            return "No observations are recorded for this resident yet."
        lines = ["RECENT OBSERVATIONS", ""]
        for observation in observations:
            lines.append(
                f"  • {human_datetime(observation.observed_at)} "
                f"[{observation.category}] {observation.observation}"
            )
        return "\n".join(lines)

    if not bundle.has_records():
        return memory_agent.no_records_message("caregiver")

    lines = [f"CARE INFORMATION — {bundle.patient.full_name}", ""]
    for item in bundle.retrieved[:5]:
        chunk = item.chunk
        lines.append(f"  • {human_date(chunk.event_date)} — {chunk.title}")
        lines.append(f"    {truncate(chunk.text, 220)}")
    return "\n".join(lines)


def build(db: Session, bundle: MemoryBundle) -> Dict[str, Any]:
    return {
        "agent": NAME,
        "system_prompt": SYSTEM_PROMPT,
        "grounded_draft": compose(db, bundle),
        "quick_actions": QUICK_ACTIONS,
    }
