"""Patient directory and profile routes."""

from fastapi import APIRouter, Depends
from database import Session

from auth import Principal, get_current_user
from database import get_db
from models import Patient
from services import memory_service
from services.authorization_service import (
    accessible_patient_ids,
    relationship_reason,
    require_patient_access,
)

router = APIRouter(prefix="/api/patients", tags=["patients"])


@router.get("")
def list_patients(
    principal: Principal = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Only patients the signed-in user has an authorized care relationship with."""
    ids = accessible_patient_ids(db, principal)
    patients = db.query(Patient).filter(Patient.id.in_(ids)).all() if ids else []
    payload = []
    for patient in patients:
        overview = memory_service.overview(db, patient.id)
        payload.append(
            {
                "id": patient.id,
                "full_name": patient.full_name,
                "age": patient.age,
                "gender": patient.gender,
                "blood_group": patient.blood_group,
                "room_number": patient.room_number,
                "old_age_home": patient.old_age_home.name if patient.old_age_home else None,
                "old_age_home_id": patient.old_age_home_id,
                "primary_doctor": (
                    patient.primary_doctor.full_name if patient.primary_doctor else None
                ),
                "guardian_name": patient.guardian_name,
                "relationship": relationship_reason(db, principal, patient),
                "counts": overview.get("counts", {}),
                "alerts": len(overview.get("alerts", [])),
            }
        )
    return {"patients": payload, "count": len(payload)}


@router.get("/{patient_id}")
def get_patient(
    patient_id: int,
    principal: Principal = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    context = require_patient_access(db, principal, patient_id)
    patient = context.patient
    return {
        "patient": {
            "id": patient.id,
            "full_name": patient.full_name,
            "age": patient.age,
            "date_of_birth": patient.date_of_birth,
            "gender": patient.gender,
            "blood_group": patient.blood_group,
            "phone": patient.phone,
            "address": patient.address,
            "room_number": patient.room_number,
            "guardian_name": patient.guardian_name,
            "guardian_phone": patient.guardian_phone,
            "emergency_contact": {
                "name": patient.emergency_contact_name,
                "phone": patient.emergency_contact_phone,
                "relation": patient.emergency_contact_relation,
            },
            "primary_doctor": (
                {
                    "id": patient.primary_doctor.id,
                    "name": patient.primary_doctor.full_name,
                    "specialty": patient.primary_doctor.specialty,
                    "hospital": patient.primary_doctor.hospital,
                }
                if patient.primary_doctor
                else None
            ),
            "old_age_home": (
                {"id": patient.old_age_home.id, "name": patient.old_age_home.name}
                if patient.old_age_home
                else None
            ),
        },
        "access": context.as_dict(),
    }


@router.get("/{patient_id}/overview")
def patient_overview(
    patient_id: int,
    principal: Principal = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    context = require_patient_access(db, principal, patient_id)
    data = memory_service.overview(db, patient_id)
    data["access"] = context.as_dict()
    if principal.role != "patient":
        # Strip sections the viewer has no consent scope for.
        if "MEDICATION_INFORMATION" not in context.scopes and (
            "FULL_HEALTH_MEMORY" not in context.scopes
        ):
            data["medications"] = []
            data["allergies"] = []
        if "RECENT_HISTORY" not in context.scopes and (
            "FULL_HEALTH_MEMORY" not in context.scopes
        ):
            data["lab_results"] = []
            data["hospital_visits"] = []
            data["conditions"] = []
    return data
