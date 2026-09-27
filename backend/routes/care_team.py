"""
Care-team endpoints — the patient's control over which doctors treat them.

Every route here is guarded by ``require_roles("patient")`` and then by
``require_patient_access``, so a patient (or their guardian, who signs in with
the patient role) can only manage their own care team. Doctors, caregivers and
reviewers have no write path to these relationships anywhere in the backend.
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from database import Session

from auth import Principal, require_roles
from database import get_db
from models import Patient
from schemas import CareTeamDoctorRequest
from services import doctor_relationship_service
from services.authorization_service import require_patient_access

router = APIRouter(prefix="/api/care-team", tags=["care-team"])


def _patient_or_404(db: Session, principal: Principal, patient_id: int) -> Patient:
    require_patient_access(db, principal, patient_id)
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found.")
    return patient


@router.get("/search")
def search_doctors(
    q: str = Query("", description="Name, specialty, hospital or registration number"),
    patient_id: int = Query(None),
    principal: Principal = Depends(require_roles("patient")),
    db: Session = Depends(get_db),
):
    """Directory search a patient uses to find a doctor to add."""
    target = patient_id or principal.patient_id
    if target:
        _patient_or_404(db, principal, target)
    return {
        "query": q,
        "results": doctor_relationship_service.search_doctors(
            db, q, patient_id=target
        ),
    }


@router.get("/{patient_id}")
def my_doctors(
    patient_id: int,
    principal: Principal = Depends(require_roles("patient")),
    db: Session = Depends(get_db),
):
    """Current doctors, doctors suggested by uploaded records, and past doctors."""
    _patient_or_404(db, principal, patient_id)
    return doctor_relationship_service.list_for_patient(db, patient_id)


@router.post("/{patient_id}/doctors")
def add_doctor(
    patient_id: int,
    payload: CareTeamDoctorRequest,
    principal: Principal = Depends(require_roles("patient")),
    db: Session = Depends(get_db),
):
    """Add a doctor. The patient appears on that doctor's dashboard from now on."""
    patient = _patient_or_404(db, principal, patient_id)
    result = doctor_relationship_service.add_doctor(
        db, patient, payload.doctor_id, actor=principal,
        make_primary=bool(payload.make_primary),
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result["message"])
    result["care_team"] = doctor_relationship_service.list_for_patient(db, patient_id)
    return result


@router.delete("/{patient_id}/doctors/{doctor_id}")
def remove_doctor(
    patient_id: int,
    doctor_id: int,
    principal: Principal = Depends(require_roles("patient")),
    db: Session = Depends(get_db),
):
    """Remove a doctor. Medical history is kept in full; only access ends."""
    patient = _patient_or_404(db, principal, patient_id)
    result = doctor_relationship_service.remove_doctor(
        db, patient, doctor_id, actor=principal
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result["message"])
    result["care_team"] = doctor_relationship_service.list_for_patient(db, patient_id)
    return result


@router.post("/{patient_id}/doctors/{doctor_id}/primary")
def set_primary(
    patient_id: int,
    doctor_id: int,
    principal: Principal = Depends(require_roles("patient")),
    db: Session = Depends(get_db),
):
    """Change which doctor is primary (the one shown on the emergency card)."""
    patient = _patient_or_404(db, principal, patient_id)
    result = doctor_relationship_service.set_primary_doctor(
        db, patient, doctor_id, actor=principal
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result["message"])
    result["care_team"] = doctor_relationship_service.list_for_patient(db, patient_id)
    return result
