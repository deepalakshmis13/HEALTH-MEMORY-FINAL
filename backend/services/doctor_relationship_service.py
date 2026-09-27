"""
Patient-controlled doctor relationships.

The patient owns their care team. They search the directory, add doctors,
remove them and choose which one is primary. A doctor can read the patients who
added them and nothing else — there is no code path anywhere in the backend
that lets a doctor add, remove or alter a relationship, including their own.

Removing a doctor never deletes clinical history. The relationship row is kept
with ``status="REMOVED"``, and every memory event, prescription, medication,
consultation, lab result, diagnosis, hospital visit and document that recorded
that doctor keeps pointing at them exactly as before. Removal only withdraws
the doctor's ongoing access and takes the patient off their active list.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from database import Session

from models import Doctor, DoctorAssignment, MemoryEvent, Patient
from services import audit_service
from utils.helpers import iso

ACTIVE = "ACTIVE"
SUGGESTED = "SUGGESTED"
REMOVED = "REMOVED"


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------
def active_doctor_ids(db: Session, patient_id: int) -> List[int]:
    """Doctors the patient currently shares their health memory with."""
    ids = {
        row.doctor_id
        for row in db.query(DoctorAssignment).filter(
            DoctorAssignment.patient_id == patient_id,
            DoctorAssignment.status == ACTIVE,
        )
    }
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if patient and patient.primary_doctor_id:
        ids.add(patient.primary_doctor_id)
    return sorted(ids)


def active_patient_ids(db: Session, doctor_id: int) -> List[int]:
    """Patients who have added this doctor to their care team."""
    ids = {
        row.patient_id
        for row in db.query(DoctorAssignment).filter(
            DoctorAssignment.doctor_id == doctor_id,
            DoctorAssignment.status == ACTIVE,
        )
    }
    ids |= {
        row.id
        for row in db.query(Patient).filter(Patient.primary_doctor_id == doctor_id)
    }
    return sorted(ids)


def _doctor_payload(db: Session, doctor: Doctor) -> Dict[str, Any]:
    return {
        "id": doctor.id,
        "name": doctor.full_name,
        "specialty": doctor.specialty,
        "hospital": doctor.hospital,
        "registration_no": doctor.registration_no,
        "phone": doctor.phone,
        "is_registered": bool(doctor.is_registered),
    }


def search_doctors(
    db: Session, query: str = "", limit: int = 20, patient_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Directory search a patient uses to find a doctor to add.

    Only registered doctors can be added — an external provider recognised from
    a scanned record has no account to receive the health memory.
    """
    needle = (query or "").strip().lower()
    already = set(active_doctor_ids(db, patient_id)) if patient_id else set()

    results = []
    for doctor in db.query(Doctor).filter(Doctor.is_registered == True).all():  # noqa: E712
        haystack = " ".join(
            filter(
                None,
                [doctor.full_name, doctor.specialty, doctor.hospital, doctor.registration_no],
            )
        ).lower()
        if needle and needle not in haystack:
            continue
        payload = _doctor_payload(db, doctor)
        payload["already_added"] = doctor.id in already
        results.append(payload)

    results.sort(key=lambda item: (item["already_added"], item["name"] or ""))
    return results[:limit]


def _history_counts(db: Session, patient_id: int, doctor_id: int) -> int:
    return (
        db.query(MemoryEvent)
        .filter(
            MemoryEvent.patient_id == patient_id,
            MemoryEvent.doctor_id == doctor_id,
        )
        .count()
    )


def list_for_patient(db: Session, patient_id: int) -> Dict[str, Any]:
    """The patient's care team: current doctors, suggestions and past doctors."""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    primary_id = patient.primary_doctor_id if patient else None

    rows = (
        db.query(DoctorAssignment)
        .filter(DoctorAssignment.patient_id == patient_id)
        .order_by(DoctorAssignment.created_at.desc())
        .all()
    )

    seen_active = set()
    current, suggested, past = [], [], []

    for row in rows:
        doctor = db.query(Doctor).filter(Doctor.id == row.doctor_id).first()
        if not doctor:
            continue
        entry = _doctor_payload(db, doctor)
        entry.update(
            {
                "assignment_id": row.id,
                "status": row.status,
                "relationship_type": row.relationship_type,
                "is_primary": doctor.id == primary_id,
                "added_at": iso(row.created_at),
                "removed_at": iso(row.removed_at),
                "added_by_role": row.added_by_role,
                "routed_from_document_id": row.routed_from_document_id,
                "records_contributed": _history_counts(db, patient_id, doctor.id),
            }
        )
        if row.status == ACTIVE:
            if doctor.id in seen_active:
                continue
            seen_active.add(doctor.id)
            current.append(entry)
        elif row.status == SUGGESTED:
            suggested.append(entry)
        else:
            past.append(entry)

    # A primary doctor set outside the join collection still belongs on the list.
    if primary_id and primary_id not in seen_active:
        doctor = db.query(Doctor).filter(Doctor.id == primary_id).first()
        if doctor:
            entry = _doctor_payload(db, doctor)
            entry.update(
                {
                    "assignment_id": None,
                    "status": ACTIVE,
                    "relationship_type": "PRIMARY",
                    "is_primary": True,
                    "added_at": None,
                    "removed_at": None,
                    "added_by_role": "patient",
                    "routed_from_document_id": None,
                    "records_contributed": _history_counts(db, patient_id, doctor.id),
                }
            )
            current.insert(0, entry)
            seen_active.add(primary_id)

    # Don't offer a suggestion for someone already on the team.
    suggested = [item for item in suggested if item["id"] not in seen_active]
    past = [item for item in past if item["id"] not in seen_active]

    current.sort(key=lambda item: (not item["is_primary"], item["name"] or ""))

    return {
        "patient_id": patient_id,
        "primary_doctor_id": primary_id,
        "doctors": current,
        "suggested": suggested,
        "past_doctors": past,
        "counts": {
            "active": len(current),
            "suggested": len(suggested),
            "past": len(past),
        },
    }


# ---------------------------------------------------------------------------
# Writing — patient-initiated only
# ---------------------------------------------------------------------------
def add_doctor(
    db: Session,
    patient: Patient,
    doctor_id: int,
    actor=None,
    make_primary: bool = False,
    commit: bool = True,
) -> Dict[str, Any]:
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        return {"ok": False, "message": "That doctor could not be found."}
    if not doctor.is_registered:
        return {
            "ok": False,
            "message": (
                f"{doctor.full_name} was recognised from a medical record but does "
                "not have an account yet, so they cannot receive your health memory."
            ),
        }

    row = (
        db.query(DoctorAssignment)
        .filter(
            DoctorAssignment.patient_id == patient.id,
            DoctorAssignment.doctor_id == doctor.id,
        )
        .order_by(DoctorAssignment.created_at.desc())
        .first()
    )

    if row and row.status == ACTIVE:
        message = f"{doctor.full_name} is already one of your doctors."
    else:
        if row is not None:
            # Re-adding a previously removed or suggested doctor reuses the row,
            # which keeps the original relationship history intact.
            row.status = ACTIVE
            row.removed_at = None
            row.added_by_role = getattr(actor, "role", "patient") if actor else "patient"
            row.added_by_user_id = getattr(actor, "user_id", None) if actor else None
            if row.relationship_type in (None, "", "ROUTED"):
                row.relationship_type = "TREATING"
        else:
            db.add(
                DoctorAssignment(
                    doctor_id=doctor.id,
                    patient_id=patient.id,
                    relationship_type="TREATING",
                    status=ACTIVE,
                    added_by_role=getattr(actor, "role", "patient") if actor else "patient",
                    added_by_user_id=getattr(actor, "user_id", None) if actor else None,
                )
            )
        message = f"{doctor.full_name} can now see your health memory."

    if make_primary or patient.primary_doctor_id is None:
        patient.primary_doctor_id = doctor.id

    db.flush()
    audit_service.log(
        db,
        "CARE_TEAM_DOCTOR_ADDED",
        actor,
        patient_id=patient.id,
        target=doctor.full_name,
        detail=f"doctor_id={doctor.id}; primary={patient.primary_doctor_id == doctor.id}",
        commit=False,
    )
    if commit:
        db.commit()
    return {"ok": True, "message": message, "doctor": _doctor_payload(db, doctor)}


def remove_doctor(
    db: Session, patient: Patient, doctor_id: int, actor=None, commit: bool = True
) -> Dict[str, Any]:
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        return {"ok": False, "message": "That doctor could not be found."}

    rows = (
        db.query(DoctorAssignment)
        .filter(
            DoctorAssignment.patient_id == patient.id,
            DoctorAssignment.doctor_id == doctor.id,
        )
        .all()
    )
    was_linked = patient.primary_doctor_id == doctor.id or any(
        row.status == ACTIVE for row in rows
    )
    if not was_linked:
        return {"ok": False, "message": f"{doctor.full_name} is not on your care team."}

    now = datetime.utcnow()
    for row in rows:
        if row.status != REMOVED:
            row.status = REMOVED
            row.removed_at = now
            row.is_primary = False

    if patient.primary_doctor_id == doctor.id:
        patient.primary_doctor_id = None
        remaining = [
            other
            for other in active_doctor_ids(db, patient.id)
            if other != doctor.id
        ]
        if remaining:
            patient.primary_doctor_id = remaining[0]

    db.flush()
    kept = _history_counts(db, patient.id, doctor.id)
    audit_service.log(
        db,
        "CARE_TEAM_DOCTOR_REMOVED",
        actor,
        patient_id=patient.id,
        target=doctor.full_name,
        detail=f"doctor_id={doctor.id}; history_records_kept={kept}",
        commit=False,
    )
    if commit:
        db.commit()
    return {
        "ok": True,
        "message": (
            f"{doctor.full_name} no longer has access to your health memory. "
            f"Your past records with them are kept."
        ),
        "history_records_kept": kept,
    }


def set_primary_doctor(
    db: Session, patient: Patient, doctor_id: int, actor=None, commit: bool = True
) -> Dict[str, Any]:
    """Change which of the patient's doctors is the primary one."""
    if doctor_id not in active_doctor_ids(db, patient.id):
        result = add_doctor(db, patient, doctor_id, actor=actor, make_primary=True, commit=commit)
        return result

    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    patient.primary_doctor_id = doctor_id
    for row in db.query(DoctorAssignment).filter(
        DoctorAssignment.patient_id == patient.id
    ):
        row.is_primary = row.doctor_id == doctor_id and row.status == ACTIVE
    db.flush()
    audit_service.log(
        db,
        "CARE_TEAM_PRIMARY_CHANGED",
        actor,
        patient_id=patient.id,
        target=doctor.full_name if doctor else str(doctor_id),
        detail=f"doctor_id={doctor_id}",
        commit=False,
    )
    if commit:
        db.commit()
    return {
        "ok": True,
        "message": f"{doctor.full_name if doctor else 'That doctor'} is now your primary doctor.",
    }


def suggest_doctor(
    db: Session,
    patient: Patient,
    doctor: Doctor,
    document_id: Optional[int] = None,
) -> str:
    """Record a doctor named in an uploaded record as a suggestion.

    This grants no access. It only surfaces the doctor in the patient's care
    team screen so the patient can decide whether to add them.
    """
    existing = (
        db.query(DoctorAssignment)
        .filter(
            DoctorAssignment.patient_id == patient.id,
            DoctorAssignment.doctor_id == doctor.id,
        )
        .order_by(DoctorAssignment.created_at.desc())
        .first()
    )
    if existing and existing.status == ACTIVE:
        return ACTIVE
    if existing and existing.status == REMOVED:
        # The patient already decided; don't nag them with it again.
        return REMOVED
    if existing:
        existing.routed_from_document_id = document_id or existing.routed_from_document_id
        return SUGGESTED

    db.add(
        DoctorAssignment(
            doctor_id=doctor.id,
            patient_id=patient.id,
            relationship_type="ROUTED",
            status=SUGGESTED,
            routed_from_document_id=document_id,
            added_by_role="system",
        )
    )
    return SUGGESTED
