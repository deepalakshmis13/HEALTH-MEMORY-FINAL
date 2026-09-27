"""Consent Control Center routes (§30)."""

from fastapi import APIRouter, Depends, HTTPException
from database import Session

from auth import Principal, get_current_user
from config import CONSENT_SCOPES
from database import get_db
from models import Caregiver, Doctor, OldAgeHome, Reviewer
from schemas import ConsentUpdate
from services import audit_service, consent_service
from services.authorization_service import require_patient_access
from utils.helpers import iso

router = APIRouter(prefix="/api/consent", tags=["consent"])

GRANTEE_ROLES = ["doctor", "caregiver", "old_age_home", "reviewer", "emergency"]

ROLE_LABELS = {
    "doctor": "Doctors",
    "caregiver": "Caregivers",
    "old_age_home": "Old Age Home staff",
    "reviewer": "Reviewers",
    "emergency": "Emergency access",
}

SCOPE_LABELS = {
    "FULL_HEALTH_MEMORY": "Full Health Memory",
    "MEDICATION_INFORMATION": "Medication Information",
    "EMERGENCY_INFORMATION": "Emergency Information",
    "RECENT_HISTORY": "Recent History",
    "CAREGIVER_NOTES": "Caregiver Notes",
    "DOCUMENTS": "Documents",
    "VOICE_DIARY": "Voice Diary",
}


@router.get("/meta")
def consent_meta():
    return {
        "roles": [{"key": key, "label": ROLE_LABELS[key]} for key in GRANTEE_ROLES],
        "scopes": [
            {"key": scope, "label": SCOPE_LABELS.get(scope, scope)}
            for scope in CONSENT_SCOPES
        ],
        "scope_event_types": {
            scope: sorted(types)
            for scope, types in consent_service.SCOPE_EVENT_TYPES.items()
        },
    }


@router.get("/{patient_id}")
def get_consent(
    patient_id: int,
    principal: Principal = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    context = require_patient_access(db, principal, patient_id)
    consents = consent_service.list_consents(db, patient_id)
    matrix = {role: {} for role in GRANTEE_ROLES}
    for consent in consents:
        matrix.setdefault(consent.grantee_role, {})[consent.scope] = {
            "granted": consent.granted,
            "granted_at": iso(consent.granted_at),
            "revoked_at": iso(consent.revoked_at),
            "note": consent.note,
        }
    history = consent_service.consent_history(db, patient_id)
    return {
        "patient_id": patient_id,
        "matrix": matrix,
        "roles": [{"key": key, "label": ROLE_LABELS[key]} for key in GRANTEE_ROLES],
        "scopes": [
            {"key": scope, "label": SCOPE_LABELS.get(scope, scope)}
            for scope in CONSENT_SCOPES
        ],
        "history": [
            {
                "id": item.id,
                "grantee_role": item.grantee_role,
                "scope": item.scope,
                "action": item.action,
                "actor_name": item.actor_name,
                "created_at": iso(item.created_at),
            }
            for item in history
        ],
        "current_viewer_scopes": sorted(context.scopes),
    }


@router.post("")
def update_consent(
    payload: ConsentUpdate,
    principal: Principal = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if principal.role != "patient" or principal.patient_id != payload.patient_id:
        raise HTTPException(
            status_code=403,
            detail="Only the patient or their guardian can change consent.",
        )
    require_patient_access(db, principal, payload.patient_id)
    if payload.grantee_role not in GRANTEE_ROLES:
        raise HTTPException(status_code=400, detail="Unknown consent recipient.")

    try:
        consent = consent_service.set_consent(
            db, payload.patient_id, payload.grantee_role, payload.scope,
            payload.granted, payload.grantee_id, payload.grantee_name,
            actor_name=principal.name, note=payload.note,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    audit_service.log(
        db, "CONSENT_GRANT" if payload.granted else "CONSENT_REVOKE", principal,
        patient_id=payload.patient_id,
        target=f"{payload.grantee_role}:{payload.scope}",
        detail=f"granted={payload.granted}",
    )
    return {
        "ok": True,
        "consent": {
            "grantee_role": consent.grantee_role,
            "scope": consent.scope,
            "granted": consent.granted,
            "granted_at": iso(consent.granted_at),
            "revoked_at": iso(consent.revoked_at),
        },
        "message": (
            f"{SCOPE_LABELS.get(payload.scope, payload.scope)} "
            f"{'granted to' if payload.granted else 'revoked from'} "
            f"{ROLE_LABELS.get(payload.grantee_role, payload.grantee_role)}."
        ),
    }


@router.get("/{patient_id}/history")
def get_history(
    patient_id: int,
    principal: Principal = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_patient_access(db, principal, patient_id)
    history = consent_service.consent_history(db, patient_id, limit=200)
    return {
        "patient_id": patient_id,
        "history": [
            {
                "id": item.id,
                "grantee_role": item.grantee_role,
                "grantee_name": item.grantee_name,
                "scope": item.scope,
                "action": item.action,
                "actor_name": item.actor_name,
                "created_at": iso(item.created_at),
            }
            for item in history
        ],
    }
