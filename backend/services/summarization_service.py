"""
Doctor one-click visit summary (§29) and AI shift handover (§26).

Both are assembled from retrieved, consent-filtered health memory, are clearly
labelled AI-generated, and are saved only after the human reviews them — an
AI summary never becomes the final medical record on its own.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from database import Session

from agents import ai_provider, caregiver_agent, doctor_agent, memory_agent
from models import (
    Allergy,
    CareTask,
    CaregiverObservation,
    Diagnosis,
    DoctorConsultation,
    HospitalVisit,
    LabResult,
    Medication,
    MedicationAdministration,
    MemoryEvent,
    Patient,
    Shift,
    ShiftHandover,
    VerificationTask,
    VisitSummary,
)
from rag import context_builder
from services import audit_service, memory_service
from services.authorization_service import require_patient_access
from utils.helpers import human_date, human_datetime, percent, truncate

AI_LABEL = (
    "AI-GENERATED DRAFT — assembled from the patient's health memory. "
    "Review and edit before saving. This is not a medical record until a "
    "clinician saves it."
)


# ---------------------------------------------------------------------------
def _section(title: str, lines: List[str]) -> List[str]:
    body = lines or ["  • Nothing recorded in the authorized health memory."]
    return [title, *body, ""]


def build_visit_summary_draft(db: Session, context, bundle) -> str:
    patient: Patient = context.patient
    patient_id = patient.id
    overview = bundle.overview

    last_visit = (
        db.query(DoctorConsultation)
        .filter(DoctorConsultation.patient_id == patient_id)
        .order_by(DoctorConsultation.consulted_on.desc())
        .first()
    )
    cutoff = (
        last_visit.consulted_on if last_visit
        else datetime.utcnow() - timedelta(days=90)
    )

    out: List[str] = [AI_LABEL, "", f"VISIT SUMMARY — {patient.full_name}",
                      f"Generated {human_datetime(datetime.utcnow())}", ""]

    out += _section(
        "PATIENT OVERVIEW",
        [
            f"  • {patient.full_name}, {patient.age} years, {patient.gender or 'sex not recorded'}"
            f", blood group {patient.blood_group or 'not recorded'}",
            f"  • Primary doctor: {patient.primary_doctor.full_name if patient.primary_doctor else 'not recorded'}",
            f"  • Care setting: {patient.old_age_home.name if patient.old_age_home else 'living at home / with family'}",
            f"  • Health memory entries: {overview['counts']['memory_events']}"
            f" | documents: {overview['counts']['documents']}",
        ],
    )

    history = (
        db.query(MemoryEvent)
        .filter(
            MemoryEvent.patient_id == patient_id,
            MemoryEvent.event_type.in_(
                ["CONSULTATION", "DIAGNOSIS", "SYMPTOM", "HOSPITAL_VISIT"]
            ),
        )
        .order_by(MemoryEvent.event_date.desc())
        .limit(8)
        .all()
    )
    out += _section(
        "RECENT CLINICAL HISTORY",
        [
            f"  • {human_date(e.event_date)} — {e.title} ({e.trust_level})"
            for e in history
        ],
    )

    out += _section(
        "CURRENT MEDICATIONS",
        [
            f"  • {memory_agent.format_medication_line(m)}"
            for m in overview.get("medications", [])
        ],
    )

    changes = (
        db.query(MemoryEvent)
        .filter(
            MemoryEvent.patient_id == patient_id,
            MemoryEvent.event_type == "MEDICATION_CHANGE",
            MemoryEvent.event_date >= cutoff,
        )
        .order_by(MemoryEvent.event_date.desc())
        .all()
    )
    out += _section(
        "RECENT MEDICATION CHANGES",
        [
            f"  • {human_date(e.event_date)} — {e.title} "
            f"({e.trust_level}, {percent(e.confidence)}, {e.verification_status})"
            for e in changes
        ],
    )

    labs = (
        db.query(LabResult)
        .filter(LabResult.patient_id == patient_id)
        .order_by(LabResult.tested_on.desc())
        .limit(8)
        .all()
    )
    out += _section(
        "LAB RESULTS",
        [
            f"  • {human_date(l.tested_on)} — {l.test_name}: {l.value} "
            f"{l.unit or ''}"
            + (f" [{l.flag.upper()}]" if l.flag != "normal" else "")
            for l in labs
        ],
    )

    visits = (
        db.query(HospitalVisit)
        .filter(HospitalVisit.patient_id == patient_id)
        .order_by(HospitalVisit.admitted_on.desc())
        .limit(4)
        .all()
    )
    out += _section(
        "RECENT HOSPITAL VISITS",
        [
            f"  • {human_date(v.admitted_on)} — {v.hospital}: {v.reason}"
            for v in visits
        ],
    )

    patient_reported = (
        db.query(MemoryEvent)
        .filter(
            MemoryEvent.patient_id == patient_id,
            MemoryEvent.source_type.in_(["PATIENT_TEXT", "PATIENT_VOICE"]),
            MemoryEvent.event_date >= cutoff,
        )
        .order_by(MemoryEvent.event_date.desc())
        .limit(6)
        .all()
    )
    out += _section(
        "PATIENT-REPORTED INFORMATION (not clinically confirmed)",
        [
            f"  • {human_date(e.event_date)} — {truncate(e.content, 180)}"
            for e in patient_reported
        ],
    )

    observations = (
        db.query(CaregiverObservation)
        .filter(
            CaregiverObservation.patient_id == patient_id,
            CaregiverObservation.observed_at >= cutoff,
        )
        .order_by(CaregiverObservation.observed_at.desc())
        .limit(8)
        .all()
    )
    out += _section(
        "CAREGIVER OBSERVATIONS",
        [
            f"  • {human_date(o.observed_at)} [{o.category}] {o.observation}"
            + ("  **" if o.severity != "normal" else "")
            for o in observations
        ],
    )

    alerts = overview.get("alerts", [])
    out += _section(
        "IMPORTANT ALERTS",
        [f"  • [{a['level'].upper()}] {a['title']} — {a['detail']}" for a in alerts],
    )

    unresolved: List[str] = []
    pending_tasks = (
        db.query(VerificationTask)
        .filter(
            VerificationTask.patient_id == patient_id,
            VerificationTask.status == "PENDING_VERIFICATION",
        )
        .all()
    )
    for task in pending_tasks:
        unresolved.append(
            f"  • {task.field_label} from a scanned document reads "
            f"'{task.extracted_value}' at {percent(task.confidence)} — awaiting "
            f"reviewer verification."
        )
    missed = (
        db.query(MedicationAdministration)
        .filter(
            MedicationAdministration.patient_id == patient_id,
            MedicationAdministration.status.in_(["Missed", "Needs Attention"]),
        )
        .limit(5)
        .all()
    )
    for item in missed:
        unresolved.append(
            f"  • {item.medication.name} dose at {item.scheduled_time} recorded as "
            f"{item.status}."
        )
    out += _section("UNRESOLVED ISSUES", unresolved)

    questions = _suggested_questions(overview, observations, changes, pending_tasks)
    out += _section("SUGGESTED QUESTIONS FOR THIS CONSULTATION", questions)

    return "\n".join(out).strip()


def _suggested_questions(overview, observations, changes, pending_tasks) -> List[str]:
    questions: List[str] = []
    if changes:
        questions.append(
            "  • Has the recent medication change been tolerated without side effects?"
        )
    if pending_tasks:
        questions.append(
            "  • Confirm the prescription details still pending reviewer verification."
        )
    symptom_words = {"dizz", "fall", "pain", "breath", "sleep", "appetite", "confus"}
    for observation in observations:
        if any(word in (observation.observation or "").lower() for word in symptom_words):
            questions.append(
                f"  • Ask about: {truncate(observation.observation, 90)}"
            )
            break
    for lab in overview.get("lab_results", []):
        if lab["flag"] != "normal":
            questions.append(
                f"  • Review the {lab['flag']} {lab['test_name']} result "
                f"({lab['value']} {lab.get('unit') or ''})."
            )
            break
    if overview.get("allergies"):
        questions.append("  • Reconfirm recorded allergies before any new prescription.")
    if not questions:
        questions.append("  • Confirm adherence and review the current care plan.")
    return questions


def generate_visit_summary(
    db: Session, principal, patient_id: int
) -> Dict[str, Any]:
    context = require_patient_access(db, principal, patient_id)
    bundle = memory_agent.gather(
        db, context,
        "Full longitudinal clinical summary: history, medications, changes, "
        "labs, caregiver observations, patient-reported information, alerts",
        actor=principal, top_k=14,
    )
    draft = build_visit_summary_draft(db, context, bundle)

    provider = ai_provider.get_provider()
    generated = provider.generate(
        system_prompt=doctor_agent.SYSTEM_PROMPT,
        context_text=bundle.context_text,
        question="Generate a one-click visit summary for this consultation.",
        grounded_draft=draft,
    )

    summary = VisitSummary(
        patient_id=patient_id,
        doctor_id=principal.profile_id,
        content=generated["answer"],
        sources=bundle.sources,
        status="DRAFT",
        is_ai_generated=True,
    )
    db.add(summary)
    audit_service.log(
        db, "AI_SUMMARY_GENERATION", principal, patient_id=patient_id,
        target="visit_summary",
        detail=f"provider={generated['provider']}; sources={len(bundle.sources)}",
        commit=False,
    )
    db.commit()
    db.refresh(summary)

    return {
        "summary_id": summary.id,
        "content": summary.content,
        "status": summary.status,
        "is_ai_generated": True,
        "disclaimer": AI_LABEL,
        "provider": generated["provider"],
        "sources": bundle.sources,
        "evidence": context_builder.evidence_panel(bundle.sources),
        "explanation": (
            f"Assembled from {len(bundle.sources)} authorized health-memory "
            f"record(s). Access basis: {context.reason}."
        ),
        "generated_at": summary.generated_at.isoformat(),
    }


def save_visit_summary(db: Session, principal, summary_id: int, content: str):
    summary = db.query(VisitSummary).filter(VisitSummary.id == summary_id).first()
    if not summary:
        return None
    require_patient_access(db, principal, summary.patient_id)
    summary.content = content
    summary.status = "SAVED"
    summary.saved_at = datetime.utcnow()

    memory_service.create_event(
        db, summary.patient_id,
        event_type="CONSULTATION",
        title="Visit summary saved by doctor",
        content=content[:4000],
        source_type="DOCTOR_RECORDED",
        trust_level="Doctor Recorded",
        event_date=datetime.utcnow(),
        author_role="doctor",
        author_name=principal.name,
        author_user_id=principal.id,
        doctor_id=principal.profile_id,
        confidence=1.0,
        tags=["visit-summary", "doctor-reviewed"],
        extra={"origin": "AI draft reviewed and saved by the doctor"},
        commit=False,
    )
    audit_service.log(
        db, "HEALTH_MEMORY_MODIFY", principal, patient_id=summary.patient_id,
        target=f"visit_summary:{summary.id}",
        detail="Doctor reviewed and saved the visit summary.",
        commit=False,
    )
    db.commit()
    db.refresh(summary)
    return summary


# ---------------------------------------------------------------------------
def build_handover_draft(
    db: Session, shift: Shift, patients: List[Patient], contexts: Dict[int, Any]
) -> Dict[str, Any]:
    lines: List[str] = [
        AI_LABEL,
        "",
        "SHIFT HANDOVER",
        f"Shift: {shift.shift_code} ({shift.start_time}–{shift.end_time}) "
        f"on {shift.shift_date}",
        f"Generated {human_datetime(datetime.utcnow())}",
        "",
    ]
    all_sources: List[Dict[str, Any]] = []

    for patient in patients:
        context = contexts[patient.id]
        overview = memory_service.overview(db, patient.id)
        bundle = memory_agent.gather(
            db, context,
            "shift medication administration observations pending tasks alerts",
            top_k=6,
            extras={"shift_id": shift.id},
        )
        all_sources.extend(bundle.sources)

        administrations = (
            db.query(MedicationAdministration)
            .filter(
                MedicationAdministration.patient_id == patient.id,
                MedicationAdministration.shift_id == shift.id,
            )
            .order_by(MedicationAdministration.scheduled_time)
            .all()
        )
        observations = (
            db.query(CaregiverObservation)
            .filter(
                CaregiverObservation.patient_id == patient.id,
                CaregiverObservation.shift_id == shift.id,
            )
            .order_by(CaregiverObservation.observed_at)
            .all()
        )
        tasks = (
            db.query(CareTask)
            .filter(CareTask.patient_id == patient.id, CareTask.shift_id == shift.id)
            .order_by(CareTask.due_time)
            .all()
        )

        given = [a for a in administrations if a.status == "Administered"]
        missed = [
            a for a in administrations
            if a.status in {"Missed", "Skipped", "Delayed", "Needs Attention"}
        ]
        pending = [a for a in administrations if a.status == "Pending"]
        pending_tasks = [t for t in tasks if t.status == "Pending"]

        lines.append(f"── {patient.full_name}"
                     f"{f' (Room {patient.room_number})' if patient.room_number else ''}")
        lines.append("")
        lines.append("PATIENT STATUS")
        status_bits = [o.observation for o in observations[-2:]] or [
            "No new observations recorded this shift."
        ]
        for bit in status_bits:
            lines.append(f"  • {bit}")

        lines.append("")
        lines.append("MEDICATION ADMINISTRATION")
        if given:
            for item in given:
                lines.append(
                    f"  • {item.scheduled_time} {item.medication.name} "
                    f"{item.medication.dose or ''} — administered"
                    + (f" ({item.notes})" if item.notes else "")
                )
        else:
            lines.append("  • No doses recorded as administered this shift.")

        lines.append("")
        lines.append("MISSED / DELAYED MEDICATION")
        if missed:
            for item in missed:
                lines.append(
                    f"  • {item.scheduled_time} {item.medication.name} — "
                    f"{item.status}" + (f": {item.notes}" if item.notes else "")
                )
        else:
            lines.append("  • None.")

        lines.append("")
        lines.append("NEW OBSERVATIONS")
        if observations:
            for observation in observations:
                mark = " **" if observation.severity != "normal" else ""
                lines.append(
                    f"  • {human_datetime(observation.observed_at)} "
                    f"[{observation.category}] {observation.observation}{mark}"
                )
        else:
            lines.append("  • None recorded.")

        lines.append("")
        lines.append("IMPORTANT CHANGES")
        changes = (
            db.query(MemoryEvent)
            .filter(
                MemoryEvent.patient_id == patient.id,
                MemoryEvent.event_type.in_(
                    ["MEDICATION_CHANGE", "DIAGNOSIS", "CONSULTATION"]
                ),
                MemoryEvent.event_date >= datetime.utcnow() - timedelta(days=7),
            )
            .order_by(MemoryEvent.event_date.desc())
            .limit(4)
            .all()
        )
        if changes:
            for event in changes:
                lines.append(
                    f"  • {human_date(event.event_date)} — {event.title} "
                    f"({event.trust_level})"
                )
        else:
            lines.append("  • No clinical changes in the last 7 days.")

        lines.append("")
        lines.append("PENDING TASKS")
        if pending_tasks or pending:
            for task in pending_tasks:
                lines.append(f"  • {task.due_time or '--:--'} {task.title}")
            for item in pending:
                lines.append(
                    f"  • {item.scheduled_time} {item.medication.name} — dose not yet given"
                )
        else:
            lines.append("  • None.")

        lines.append("")
        lines.append("ALERTS")
        alerts = overview.get("alerts", [])
        if alerts:
            for alert in alerts:
                lines.append(f"  • [{alert['level'].upper()}] {alert['title']}")
        else:
            lines.append("  • None.")

        lines.append("")
        lines.append("NEXT SHIFT INSTRUCTIONS")
        instructions = []
        if missed:
            instructions.append(
                "Follow up the missed dose(s) with the nurse-in-charge before the "
                "next scheduled time."
            )
        if any(o.severity != "normal" for o in observations):
            instructions.append(
                "Continue monitoring the flagged observation and record any change."
            )
        if pending:
            instructions.append("Complete the doses still pending from this shift.")
        unverified = [
            m for m in overview.get("medications", [])
            if m.get("verification_status") == "PENDING_VERIFICATION"
        ]
        if unverified:
            instructions.append(
                "Do not administer medication still awaiting reviewer "
                "verification: "
                + ", ".join(m["name"] for m in unverified)
            )
        if not instructions:
            instructions.append("Continue the routine care plan.")
        for instruction in instructions:
            lines.append(f"  • {instruction}")
        lines.append("")

    return {"content": "\n".join(lines).strip(), "sources": all_sources}


def generate_shift_handover(
    db: Session, principal, shift_id: int, patient_ids: Optional[List[int]] = None
) -> Dict[str, Any]:
    shift = db.query(Shift).filter(Shift.id == shift_id).first()
    if not shift:
        return {"error": "Shift not found."}

    ids = patient_ids or shift.assigned_patient_ids or []
    patients, contexts = [], {}
    for patient_id in ids:
        context = require_patient_access(db, principal, patient_id)
        contexts[patient_id] = context
        patients.append(context.patient)

    draft = build_handover_draft(db, shift, patients, contexts)

    provider = ai_provider.get_provider()
    generated = provider.generate(
        system_prompt=caregiver_agent.SYSTEM_PROMPT,
        context_text=draft["content"],
        question="Generate the end-of-shift handover.",
        grounded_draft=draft["content"],
    )

    handover = ShiftHandover(
        shift_id=shift.id,
        caregiver_id=principal.profile_id,
        facility_id=shift.facility_id,
        patient_ids=ids,
        content=generated["answer"],
        sources=draft["sources"],
        status="DRAFT",
    )
    db.add(handover)
    audit_service.log(
        db, "SHIFT_HANDOVER_GENERATION", principal,
        target=f"shift:{shift.id}",
        detail=f"patients={ids}; provider={generated['provider']}",
        commit=False,
    )
    db.commit()
    db.refresh(handover)

    return {
        "handover_id": handover.id,
        "content": handover.content,
        "status": handover.status,
        "disclaimer": AI_LABEL,
        "provider": generated["provider"],
        "sources": draft["sources"],
        "evidence": context_builder.evidence_panel(draft["sources"]),
        "generated_at": handover.generated_at.isoformat(),
    }


def save_shift_handover(db: Session, principal, handover_id: int, content: str):
    handover = (
        db.query(ShiftHandover).filter(ShiftHandover.id == handover_id).first()
    )
    if not handover:
        return None
    handover.content = content
    handover.status = "SAVED"
    handover.saved_at = datetime.utcnow()

    for patient_id in handover.patient_ids or []:
        memory_service.create_event(
            db, patient_id,
            event_type="OBSERVATION",
            title="Shift handover recorded",
            content=truncate(content, 3000),
            source_type="CAREGIVER_RECORDED",
            trust_level="Caregiver Recorded",
            event_date=datetime.utcnow(),
            author_role="caregiver",
            author_name=principal.name,
            author_user_id=principal.id,
            confidence=1.0,
            tags=["handover"],
            extra={"handover_id": handover.id, "reviewed_by_caregiver": True},
            commit=False,
        )
    audit_service.log(
        db, "HEALTH_MEMORY_MODIFY", principal,
        target=f"handover:{handover.id}",
        detail="Caregiver reviewed and saved the shift handover.",
        commit=False,
    )
    db.commit()
    db.refresh(handover)
    return handover
