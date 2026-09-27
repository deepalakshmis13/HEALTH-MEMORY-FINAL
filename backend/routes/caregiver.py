"""Caregiver / Old Age Home dashboard routes (§23–§28)."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from database import Session

from auth import Principal, require_roles
from config import SHIFT_DEFINITIONS
from database import get_db
from models import (
    CareAssignment,
    CareTask,
    Caregiver,
    CaregiverObservation,
    Medication,
    MedicationAdministration,
    OldAgeHome,
    Patient,
    Shift,
    ShiftHandover,
)
from schemas import (
    CareTaskUpdate,
    HandoverRequest,
    MedicationVerifyRequest,
    ObservationRequest,
    SaveHandoverRequest,
    ShiftStartRequest,
)
from services import audit_service, memory_service, summarization_service
from services.authorization_service import (
    accessible_patient_ids,
    require_patient_access,
)
from utils.helpers import human_datetime, iso

router = APIRouter(prefix="/api/caregiver", tags=["caregiver"])

DEFAULT_TASKS = [
    ("Morning hygiene and grooming assistance", "hygiene", "07:30"),
    ("Breakfast and fluid intake", "meal", "08:30"),
    ("Blood pressure check", "vitals", "09:30"),
    ("Mobility / walking assistance", "mobility", "11:00"),
    ("Lunch and fluid intake", "meal", "13:00"),
    ("Afternoon rest and comfort check", "rest", "15:30"),
    ("Evening tea and snack", "meal", "17:00"),
    ("Evening vitals check", "vitals", "19:00"),
    ("Dinner and fluid intake", "meal", "20:00"),
    ("Night comfort and safety round", "safety", "23:00"),
]


def _shift_definition(code: str) -> dict:
    for definition in SHIFT_DEFINITIONS:
        if definition["id"] == code.upper():
            return definition
    raise HTTPException(status_code=400, detail="Unknown shift.")


def _in_window(time_str: str, start: str, end: str) -> bool:
    if not time_str:
        return False
    if start <= end:
        return start <= time_str < end
    return time_str >= start or time_str < end  # night shift wraps midnight


@router.get("/config")
def caregiver_config(
    principal: Principal = Depends(require_roles("caregiver")),
    db: Session = Depends(get_db),
):
    caregiver: Caregiver = principal.profile
    homes = db.query(OldAgeHome).all()
    patient_ids = accessible_patient_ids(db, principal)
    patients = (
        db.query(Patient).filter(Patient.id.in_(patient_ids)).all()
        if patient_ids else []
    )
    active_shift = (
        db.query(Shift)
        .filter(Shift.caregiver_id == caregiver.id, Shift.status == "ACTIVE")
        .order_by(Shift.created_at.desc())
        .first()
    )
    return {
        "caregiver": {
            "id": caregiver.id,
            "name": caregiver.full_name,
            "care_type": caregiver.care_type,
            "staff_code": caregiver.staff_code,
            "old_age_home_id": caregiver.old_age_home_id,
            "old_age_home": (
                caregiver.old_age_home.name if caregiver.old_age_home else None
            ),
        },
        "care_types": [
            {"key": "INDIVIDUAL", "label": "Individual Caregiver"},
            {"key": "OLD_AGE_HOME", "label": "Old Age Home"},
        ],
        "shifts": SHIFT_DEFINITIONS,
        "facilities": [
            {"id": home.id, "name": home.name, "address": home.address}
            for home in homes
        ],
        "patients": [
            {
                "id": patient.id,
                "full_name": patient.full_name,
                "age": patient.age,
                "room_number": patient.room_number,
                "old_age_home_id": patient.old_age_home_id,
            }
            for patient in patients
        ],
        "active_shift": _serialize_shift(db, active_shift) if active_shift else None,
    }


@router.post("/care-type")
def set_care_type(
    care_type: str = Query(...),
    facility_id: Optional[int] = Query(None),
    principal: Principal = Depends(require_roles("caregiver")),
    db: Session = Depends(get_db),
):
    if care_type not in {"INDIVIDUAL", "OLD_AGE_HOME"}:
        raise HTTPException(status_code=400, detail="Unknown care type.")
    caregiver: Caregiver = principal.profile
    caregiver.care_type = care_type
    if care_type == "OLD_AGE_HOME" and facility_id:
        caregiver.old_age_home_id = facility_id
    db.commit()
    return {
        "ok": True,
        "care_type": caregiver.care_type,
        "old_age_home_id": caregiver.old_age_home_id,
    }


def _serialize_shift(db: Session, shift: Shift) -> dict:
    return {
        "id": shift.id,
        "shift_code": shift.shift_code,
        "shift_date": shift.shift_date,
        "start_time": shift.start_time,
        "end_time": shift.end_time,
        "status": shift.status,
        "facility_id": shift.facility_id,
        "assigned_patient_ids": shift.assigned_patient_ids or [],
        "created_at": iso(shift.created_at),
    }


def _seed_shift_work(db: Session, shift: Shift, patient_ids: List[int]):
    """Create the medication rounds and care tasks that belong to this shift."""
    for patient_id in patient_ids:
        medications = (
            db.query(Medication)
            .filter(Medication.patient_id == patient_id, Medication.status == "ACTIVE")
            .all()
        )
        for medication in medications:
            for time_str in medication.schedule_times or ["08:00"]:
                if not _in_window(time_str, shift.start_time, shift.end_time):
                    continue
                exists = (
                    db.query(MedicationAdministration)
                    .filter(
                        MedicationAdministration.shift_id == shift.id,
                        MedicationAdministration.medication_id == medication.id,
                        MedicationAdministration.scheduled_time == time_str,
                    )
                    .first()
                )
                if exists:
                    continue
                needs_attention = (
                    medication.verification_status == "PENDING_VERIFICATION"
                )
                db.add(
                    MedicationAdministration(
                        patient_id=patient_id,
                        medication_id=medication.id,
                        caregiver_id=shift.caregiver_id,
                        shift_id=shift.id,
                        scheduled_time=time_str,
                        scheduled_date=shift.shift_date,
                        status="Needs Attention" if needs_attention else "Pending",
                        notes=(
                            "Awaiting reviewer verification — do not administer "
                            "until confirmed."
                            if needs_attention else None
                        ),
                    )
                )
        for title, category, due_time in DEFAULT_TASKS:
            if not _in_window(due_time, shift.start_time, shift.end_time):
                continue
            exists = (
                db.query(CareTask)
                .filter(
                    CareTask.shift_id == shift.id,
                    CareTask.patient_id == patient_id,
                    CareTask.title == title,
                )
                .first()
            )
            if exists:
                continue
            db.add(
                CareTask(
                    patient_id=patient_id,
                    shift_id=shift.id,
                    caregiver_id=shift.caregiver_id,
                    title=title,
                    category=category,
                    due_time=due_time,
                )
            )
    db.flush()


@router.post("/shift/start")
def start_shift(
    payload: ShiftStartRequest,
    principal: Principal = Depends(require_roles("caregiver")),
    db: Session = Depends(get_db),
):
    caregiver: Caregiver = principal.profile
    definition = _shift_definition(payload.shift_code)

    caregiver.care_type = payload.care_type
    if payload.care_type == "OLD_AGE_HOME" and payload.facility_id:
        caregiver.old_age_home_id = payload.facility_id
    db.flush()

    allowed = set(accessible_patient_ids(db, principal))
    patient_ids = [pid for pid in payload.patient_ids if pid in allowed]
    if not patient_ids:
        patient_ids = sorted(allowed)[:1] if payload.care_type == "INDIVIDUAL" else sorted(allowed)
    if not patient_ids:
        raise HTTPException(
            status_code=400,
            detail="No patients are assigned to you. Ask the facility to assign one.",
        )

    for shift in db.query(Shift).filter(
        Shift.caregiver_id == caregiver.id, Shift.status == "ACTIVE"
    ):
        shift.status = "CLOSED"

    shift = Shift(
        facility_id=caregiver.old_age_home_id
        if payload.care_type == "OLD_AGE_HOME" else None,
        caregiver_id=caregiver.id,
        shift_code=definition["id"],
        shift_date=payload.shift_date or datetime.utcnow().strftime("%Y-%m-%d"),
        start_time=definition["start"],
        end_time=definition["end"],
        status="ACTIVE",
        assigned_patient_ids=patient_ids,
    )
    db.add(shift)
    db.flush()
    _seed_shift_work(db, shift, patient_ids)

    audit_service.log(
        db, "SHIFT_START", principal, target=f"shift:{shift.id}",
        detail=(
            f"care_type={payload.care_type}; shift={definition['id']}; "
            f"patients={patient_ids}"
        ),
        commit=False,
    )
    db.commit()
    db.refresh(shift)
    return {"shift": _serialize_shift(db, shift), "patients": patient_ids}


@router.get("/shift/{shift_id}")
def shift_detail(
    shift_id: int,
    principal: Principal = Depends(require_roles("caregiver")),
    db: Session = Depends(get_db),
):
    shift = db.query(Shift).filter(Shift.id == shift_id).first()
    if not shift or shift.caregiver_id != principal.profile_id:
        raise HTTPException(status_code=404, detail="Shift not found.")

    patients = []
    for patient_id in shift.assigned_patient_ids or []:
        try:
            context = require_patient_access(db, principal, patient_id)
        except HTTPException:
            continue
        administrations = (
            db.query(MedicationAdministration)
            .filter(
                MedicationAdministration.shift_id == shift.id,
                MedicationAdministration.patient_id == patient_id,
            )
            .order_by(MedicationAdministration.scheduled_time)
            .all()
        )
        tasks = (
            db.query(CareTask)
            .filter(CareTask.shift_id == shift.id, CareTask.patient_id == patient_id)
            .order_by(CareTask.due_time)
            .all()
        )
        observations = (
            db.query(CaregiverObservation)
            .filter(
                CaregiverObservation.shift_id == shift.id,
                CaregiverObservation.patient_id == patient_id,
            )
            .order_by(CaregiverObservation.observed_at.desc())
            .all()
        )
        overview = memory_service.overview(db, patient_id)
        patients.append(
            {
                "patient": overview.get("patient", {}),
                "alerts": overview.get("alerts", []),
                "allergies": overview.get("allergies", []),
                "medications": overview.get("medications", []),
                "administrations": [
                    {
                        "id": item.id,
                        "medication_id": item.medication_id,
                        "medication": item.medication.name,
                        "dose": item.medication.dose,
                        "frequency": item.medication.frequency,
                        "prescriber": (
                            item.medication.prescriber.full_name
                            if item.medication.prescriber else None
                        ),
                        "verification_status": item.medication.verification_status,
                        "scheduled_time": item.scheduled_time,
                        "status": item.status,
                        "notes": item.notes,
                        "administered_at": iso(item.administered_at),
                    }
                    for item in administrations
                ],
                "tasks": [
                    {
                        "id": task.id, "title": task.title, "category": task.category,
                        "due_time": task.due_time, "status": task.status,
                        "notes": task.notes,
                    }
                    for task in tasks
                ],
                "observations": [
                    {
                        "id": observation.id,
                        "category": observation.category,
                        "observation": observation.observation,
                        "severity": observation.severity,
                        "observed_at": iso(observation.observed_at),
                        "observed_at_label": human_datetime(observation.observed_at),
                    }
                    for observation in observations
                ],
            }
        )
    return {"shift": _serialize_shift(db, shift), "patients": patients}


@router.get("/shifts")
def list_shifts(
    principal: Principal = Depends(require_roles("caregiver")),
    db: Session = Depends(get_db),
):
    shifts = (
        db.query(Shift)
        .filter(Shift.caregiver_id == principal.profile_id)
        .order_by(Shift.created_at.desc())
        .limit(12)
        .all()
    )
    return {"shifts": [_serialize_shift(db, shift) for shift in shifts]}


@router.post("/medication/verify")
def verify_medication(
    payload: MedicationVerifyRequest,
    principal: Principal = Depends(require_roles("caregiver")),
    db: Session = Depends(get_db),
):
    """§27 — record medication administration into persistent health memory."""
    administration = None
    if payload.administration_id:
        administration = (
            db.query(MedicationAdministration)
            .filter(MedicationAdministration.id == payload.administration_id)
            .first()
        )
    if not administration:
        if not (payload.patient_id and payload.medication_id):
            raise HTTPException(status_code=400, detail="Medication task not found.")
        administration = MedicationAdministration(
            patient_id=payload.patient_id,
            medication_id=payload.medication_id,
            caregiver_id=principal.profile_id,
            shift_id=payload.shift_id,
            scheduled_time=payload.scheduled_time or datetime.utcnow().strftime("%H:%M"),
            scheduled_date=datetime.utcnow().strftime("%Y-%m-%d"),
        )
        db.add(administration)
        db.flush()

    context = require_patient_access(db, principal, administration.patient_id)
    medication = (
        db.query(Medication)
        .filter(Medication.id == administration.medication_id)
        .first()
    )
    if (
        medication
        and medication.verification_status == "PENDING_VERIFICATION"
        and payload.status == "Administered"
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                f"{medication.name} is still awaiting reviewer verification and "
                "must not be recorded as administered."
            ),
        )

    administration.status = payload.status
    administration.notes = payload.notes
    administration.caregiver_id = principal.profile_id
    if payload.status == "Administered":
        administration.administered_at = datetime.utcnow()

    event = memory_service.create_event(
        db, administration.patient_id,
        event_type="MEDICATION_ADMINISTRATION",
        title=(
            f"{medication.name} {medication.dose or ''} — {payload.status}".strip()
        ),
        content=(
            f"{medication.name} {medication.dose or ''} scheduled at "
            f"{administration.scheduled_time} recorded as {payload.status} by "
            f"{principal.name}."
            + (f" Note: {payload.notes}" if payload.notes else "")
        ),
        source_type="CAREGIVER_RECORDED",
        trust_level="Caregiver Recorded",
        event_date=datetime.utcnow(),
        author_role="caregiver",
        author_name=principal.name,
        author_user_id=principal.id,
        confidence=1.0,
        severity="attention" if payload.status in {"Missed", "Needs Attention"} else "normal",
        tags=["medication-administration", payload.status.lower().replace(" ", "-")],
        extra={
            "medication_id": medication.id,
            "shift_id": administration.shift_id,
            "scheduled_time": administration.scheduled_time,
        },
        commit=False,
    )
    administration.memory_event_id = event.id

    audit_service.log(
        db, "MEDICATION_VERIFICATION", principal,
        patient_id=administration.patient_id,
        target=f"medication:{medication.id}",
        detail=f"status={payload.status}; shift={administration.shift_id}",
        commit=False,
    )
    db.commit()
    return {
        "ok": True,
        "administration_id": administration.id,
        "status": administration.status,
        "memory_event_id": event.id,
        "message": f"Recorded as {payload.status} in the patient's health memory.",
    }


@router.post("/observation")
def add_observation(
    payload: ObservationRequest,
    principal: Principal = Depends(require_roles("caregiver")),
    db: Session = Depends(get_db),
):
    require_patient_access(db, principal, payload.patient_id)
    event = memory_service.create_event(
        db, payload.patient_id,
        event_type="OBSERVATION",
        title=f"Caregiver observation ({payload.category})",
        content=payload.observation,
        source_type="CAREGIVER_RECORDED",
        trust_level="Caregiver Recorded",
        event_date=datetime.utcnow(),
        author_role="caregiver",
        author_name=principal.name,
        author_user_id=principal.id,
        confidence=1.0,
        severity=payload.severity,
        tags=["observation", payload.category],
        commit=False,
    )
    observation = CaregiverObservation(
        patient_id=payload.patient_id,
        caregiver_id=principal.profile_id,
        shift_id=payload.shift_id,
        memory_event_id=event.id,
        category=payload.category,
        observation=payload.observation,
        severity=payload.severity,
    )
    db.add(observation)
    audit_service.log(
        db, "HEALTH_MEMORY_CREATE", principal, patient_id=payload.patient_id,
        target="caregiver_observation", detail=payload.observation[:200], commit=False,
    )
    db.commit()
    db.refresh(observation)
    return {
        "ok": True,
        "observation_id": observation.id,
        "memory_event_id": event.id,
        "message": "Observation saved to the resident's health memory.",
    }


@router.post("/task/{task_id}")
def update_task(
    task_id: int,
    payload: CareTaskUpdate,
    principal: Principal = Depends(require_roles("caregiver")),
    db: Session = Depends(get_db),
):
    task = db.query(CareTask).filter(CareTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Care task not found.")
    require_patient_access(db, principal, task.patient_id)
    task.status = payload.status
    task.notes = payload.notes
    if payload.status == "Done":
        task.completed_at = datetime.utcnow()
    db.commit()
    return {"ok": True, "task_id": task.id, "status": task.status}


@router.get("/insights")
def insights(
    patient_id: Optional[int] = Query(None),
    principal: Principal = Depends(require_roles("caregiver")),
    db: Session = Depends(get_db),
):
    ids = (
        [patient_id] if patient_id else accessible_patient_ids(db, principal)
    )
    authorized = []
    for candidate in ids:
        try:
            require_patient_access(db, principal, candidate)
            authorized.append(candidate)
        except HTTPException:
            continue
    feed = memory_service.caregiver_insight_feed(db, authorized)
    return {"insights": feed, "count": len(feed), "patient_ids": authorized}


@router.post("/shift-handover")
def shift_handover(
    payload: HandoverRequest,
    principal: Principal = Depends(require_roles("caregiver")),
    db: Session = Depends(get_db),
):
    shift = db.query(Shift).filter(Shift.id == payload.shift_id).first()
    if not shift or shift.caregiver_id != principal.profile_id:
        raise HTTPException(status_code=404, detail="Shift not found.")
    result = summarization_service.generate_shift_handover(
        db, principal, payload.shift_id, payload.patient_ids or None
    )
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/shift-handover/save")
def save_handover(
    payload: SaveHandoverRequest,
    principal: Principal = Depends(require_roles("caregiver")),
    db: Session = Depends(get_db),
):
    handover = summarization_service.save_shift_handover(
        db, principal, payload.handover_id, payload.content
    )
    if not handover:
        raise HTTPException(status_code=404, detail="Handover not found.")
    return {
        "ok": True,
        "handover_id": handover.id,
        "status": handover.status,
        "saved_at": iso(handover.saved_at),
        "message": "Handover reviewed and saved to health memory.",
    }


@router.get("/handovers")
def list_handovers(
    principal: Principal = Depends(require_roles("caregiver")),
    db: Session = Depends(get_db),
):
    handovers = (
        db.query(ShiftHandover)
        .filter(ShiftHandover.caregiver_id == principal.profile_id)
        .order_by(ShiftHandover.generated_at.desc())
        .limit(10)
        .all()
    )
    return {
        "handovers": [
            {
                "id": handover.id,
                "shift_id": handover.shift_id,
                "status": handover.status,
                "content": handover.content,
                "generated_at": iso(handover.generated_at),
                "saved_at": iso(handover.saved_at),
                "patient_ids": handover.patient_ids or [],
            }
            for handover in handovers
        ]
    }
