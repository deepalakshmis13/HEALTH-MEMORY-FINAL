"""
Consent Control Center logic (§30).

Consent is checked *before* any retrieval, never after. `allowed_scopes()` is
the single function the RAG retriever and every route uses to find out what a
given viewer may see about a given patient.
"""

from datetime import datetime
from typing import List, Optional, Set

from database import Session

from config import CONSENT_SCOPES
from models import Consent, ConsentHistory, Patient

# Which memory events each scope covers.
SCOPE_EVENT_TYPES = {
    "MEDICATION_INFORMATION": {
        "MEDICATION", "PRESCRIPTION", "MEDICATION_CHANGE",
        "MEDICATION_ADMINISTRATION", "ALLERGY",
    },
    "RECENT_HISTORY": {
        "CONSULTATION", "DIAGNOSIS", "SYMPTOM", "HOSPITAL_VISIT",
        "LAB_RESULT", "NOTE",
    },
    "CAREGIVER_NOTES": {"OBSERVATION"},
    "VOICE_DIARY": {"VOICE_ENTRY"},
    "DOCUMENTS": {"DOCUMENT"},
    "EMERGENCY_INFORMATION": {"ALLERGY", "DIAGNOSIS", "MEDICATION"},
}

DEFAULT_GRANTS = {
    "doctor": ["FULL_HEALTH_MEMORY", "MEDICATION_INFORMATION", "RECENT_HISTORY",
               "DOCUMENTS", "CAREGIVER_NOTES", "EMERGENCY_INFORMATION"],
    "caregiver": ["MEDICATION_INFORMATION", "CAREGIVER_NOTES",
                  "EMERGENCY_INFORMATION", "RECENT_HISTORY"],
    "old_age_home": ["MEDICATION_INFORMATION", "CAREGIVER_NOTES",
                     "EMERGENCY_INFORMATION"],
    "reviewer": ["MEDICATION_INFORMATION"],
    "emergency": ["EMERGENCY_INFORMATION"],
}


def ensure_default_consents(db: Session, patient: Patient, commit: bool = True):
    """A new patient starts with a sensible, explicit consent configuration."""
    existing = {
        (c.grantee_role, c.scope)
        for c in db.query(Consent).filter(Consent.patient_id == patient.id)
    }
    for role, scopes in DEFAULT_GRANTS.items():
        for scope in scopes:
            if (role, scope) in existing:
                continue
            db.add(
                Consent(
                    patient_id=patient.id,
                    grantee_role=role,
                    scope=scope,
                    granted=True,
                    note="Default consent created with the health memory record",
                )
            )
    if commit:
        db.commit()


def list_consents(db: Session, patient_id: int) -> List[Consent]:
    return (
        db.query(Consent)
        .filter(Consent.patient_id == patient_id)
        .order_by(Consent.grantee_role, Consent.scope)
        .all()
    )


def set_consent(
    db: Session,
    patient_id: int,
    grantee_role: str,
    scope: str,
    granted: bool,
    grantee_id: Optional[int] = None,
    grantee_name: Optional[str] = None,
    actor_name: Optional[str] = None,
    note: Optional[str] = None,
) -> Consent:
    if scope not in CONSENT_SCOPES:
        raise ValueError(f"Unknown consent scope '{scope}'")

    query = db.query(Consent).filter(
        Consent.patient_id == patient_id,
        Consent.grantee_role == grantee_role,
        Consent.scope == scope,
    )
    if grantee_id is not None:
        query = query.filter(Consent.grantee_id == grantee_id)
    consent = query.first()

    if not consent:
        consent = Consent(
            patient_id=patient_id,
            grantee_role=grantee_role,
            grantee_id=grantee_id,
            grantee_name=grantee_name,
            scope=scope,
        )
        db.add(consent)

    consent.granted = granted
    consent.note = note
    consent.grantee_name = grantee_name or consent.grantee_name
    if granted:
        consent.granted_at = datetime.utcnow()
        consent.revoked_at = None
    else:
        consent.revoked_at = datetime.utcnow()

    db.add(
        ConsentHistory(
            patient_id=patient_id,
            grantee_role=grantee_role,
            grantee_name=grantee_name,
            scope=scope,
            action="GRANTED" if granted else "REVOKED",
            actor_name=actor_name or "Patient / Guardian",
        )
    )
    db.commit()
    db.refresh(consent)
    return consent


def consent_history(db: Session, patient_id: int, limit: int = 60):
    return (
        db.query(ConsentHistory)
        .filter(ConsentHistory.patient_id == patient_id)
        .order_by(ConsentHistory.created_at.desc())
        .limit(limit)
        .all()
    )


def allowed_scopes(
    db: Session,
    patient_id: int,
    viewer_role: str,
    viewer_profile_id: Optional[int] = None,
    care_type: Optional[str] = None,
) -> Set[str]:
    """
    The set of consent scopes a viewer currently holds for this patient.

    The patient (and their guardian) always hold every scope over their own
    record. Everyone else holds only what the patient has explicitly granted.
    """
    if viewer_role == "patient":
        return set(CONSENT_SCOPES)

    role_key = viewer_role
    if viewer_role == "caregiver" and care_type == "OLD_AGE_HOME":
        role_key = "old_age_home"

    rows = (
        db.query(Consent)
        .filter(
            Consent.patient_id == patient_id,
            Consent.grantee_role.in_([role_key, viewer_role]),
            Consent.granted.is_(True),
        )
        .all()
    )
    scopes = {
        row.scope
        for row in rows
        if row.grantee_id is None or row.grantee_id == viewer_profile_id
    }
    if "FULL_HEALTH_MEMORY" in scopes:
        scopes |= set(CONSENT_SCOPES)
    return scopes


def scopes_for_event_type(event_type: str) -> Set[str]:
    """Which scopes would grant visibility of this event type."""
    scopes = {"FULL_HEALTH_MEMORY"}
    for scope, types in SCOPE_EVENT_TYPES.items():
        if event_type in types:
            scopes.add(scope)
    return scopes


def event_visible(event_type: str, granted_scopes: Set[str]) -> bool:
    return bool(scopes_for_event_type(event_type) & granted_scopes)
