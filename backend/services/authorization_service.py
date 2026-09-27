"""
Patient-level authorization (§20, §45).

Two questions, answered before anything is read:

    can_access_patient() — is there a care relationship at all?
    access_context()     — combined relationship + consent view for retrieval.

Authorization is enforced in the backend, never in the UI, and never delegated
to the language model.
"""

from typing import List, Optional, Set

from fastapi import HTTPException
from database import Session

from models import (
    CareAssignment,
    Caregiver,
    Doctor,
    DoctorAssignment,
    Patient,
    Reviewer,
    VerificationTask,
)
from services import consent_service


class AccessContext:
    def __init__(self, patient: Patient, role: str, scopes: Set[str], reason: str):
        self.patient = patient
        self.role = role
        self.scopes = scopes
        self.reason = reason

    @property
    def patient_id(self) -> int:
        return self.patient.id

    def as_dict(self):
        return {
            "patient_id": self.patient.id,
            "role": self.role,
            "granted_scopes": sorted(self.scopes),
            "relationship": self.reason,
        }


# ---------------------------------------------------------------------------
def accessible_patient_ids(db: Session, principal) -> List[int]:
    role = principal.role

    if role == "patient":
        return [principal.patient_id] if principal.patient_id else []

    if role == "doctor":
        doctor_id = principal.profile_id
        # Only relationships the patient has actually activated. A doctor named
        # in an uploaded record sits at SUGGESTED and grants no access until the
        # patient adds them; a removed doctor keeps no access at all.
        via_assignment = [
            row.patient_id
            for row in db.query(DoctorAssignment).filter(
                DoctorAssignment.doctor_id == doctor_id,
                DoctorAssignment.status == "ACTIVE",
            )
        ]
        via_primary = [
            row.id
            for row in db.query(Patient).filter(Patient.primary_doctor_id == doctor_id)
        ]
        return sorted(set(via_assignment) | set(via_primary))

    if role == "caregiver":
        caregiver: Optional[Caregiver] = principal.profile
        if not caregiver:
            return []
        ids = {
            row.patient_id
            for row in db.query(CareAssignment).filter(
                CareAssignment.caregiver_id == caregiver.id,
                CareAssignment.active.is_(True),
            )
        }
        if caregiver.care_type == "OLD_AGE_HOME" and caregiver.old_age_home_id:
            ids |= {
                row.id
                for row in db.query(Patient).filter(
                    Patient.old_age_home_id == caregiver.old_age_home_id
                )
            }
        return sorted(ids)

    if role == "reviewer":
        # A reviewer sees only patients with medication consent granted, and
        # in practice only those with work in the verification queue or an
        # active medication record they are asked about.
        ids = set()
        for patient in db.query(Patient).all():
            scopes = consent_service.allowed_scopes(
                db, patient.id, "reviewer", principal.profile_id
            )
            if "MEDICATION_INFORMATION" in scopes or "FULL_HEALTH_MEMORY" in scopes:
                ids.add(patient.id)
        queue_ids = {
            row.patient_id for row in db.query(VerificationTask).all()
        }
        return sorted(ids | queue_ids)

    return []


def relationship_reason(db: Session, principal, patient: Patient) -> Optional[str]:
    role = principal.role
    if role == "patient":
        return "Own health record" if principal.patient_id == patient.id else None

    if role == "doctor":
        if patient.primary_doctor_id == principal.profile_id:
            return "Primary doctor"
        assignment = (
            db.query(DoctorAssignment)
            .filter(
                DoctorAssignment.doctor_id == principal.profile_id,
                DoctorAssignment.patient_id == patient.id,
                DoctorAssignment.status == "ACTIVE",
            )
            .first()
        )
        if assignment:
            return (
                "Added by the patient after a routed medical record"
                if assignment.routed_from_document_id
                else "Added by the patient"
            )
        return None

    if role == "caregiver":
        caregiver: Caregiver = principal.profile
        if not caregiver:
            return None
        assigned = (
            db.query(CareAssignment)
            .filter(
                CareAssignment.caregiver_id == caregiver.id,
                CareAssignment.patient_id == patient.id,
                CareAssignment.active.is_(True),
            )
            .first()
        )
        if assigned:
            return "Assigned caregiver"
        if (
            caregiver.care_type == "OLD_AGE_HOME"
            and caregiver.old_age_home_id
            and patient.old_age_home_id == caregiver.old_age_home_id
        ):
            return "Resident of the same care facility"
        return None

    if role == "reviewer":
        return "Medication verification and dispensing"

    return None


def can_access_patient(db: Session, principal, patient_id: int) -> bool:
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        return False
    return relationship_reason(db, principal, patient) is not None


def require_patient_access(db: Session, principal, patient_id: int) -> AccessContext:
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="No health memory available.")

    reason = relationship_reason(db, principal, patient)
    if reason is None:
        from services import audit_service

        audit_service.log(
            db, "ACCESS_DENIED", principal, patient_id=patient_id,
            detail="No care relationship with this patient.",
        )
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view this information.",
        )

    care_type = getattr(principal.profile, "care_type", None)
    scopes = consent_service.allowed_scopes(
        db, patient.id, principal.role, principal.profile_id, care_type
    )
    if principal.role != "patient" and not scopes:
        raise HTTPException(
            status_code=403,
            detail=(
                "The patient has not granted consent for your role to view "
                "this health memory."
            ),
        )
    return AccessContext(patient, principal.role, scopes, reason)
