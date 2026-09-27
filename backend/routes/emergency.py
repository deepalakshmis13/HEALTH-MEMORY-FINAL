"""Emergency Health Card routes (§31)."""

from fastapi import APIRouter, Depends, HTTPException
from database import Session

from auth import Principal, get_current_user
from database import get_db
from services import audit_service, consent_service, memory_service
from services.authorization_service import require_patient_access

router = APIRouter(prefix="/api/emergency", tags=["emergency"])


@router.get("/{patient_id}")
def emergency_card(
    patient_id: int,
    principal: Principal = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    context = require_patient_access(db, principal, patient_id)
    if principal.role != "patient" and not (
        {"EMERGENCY_INFORMATION", "FULL_HEALTH_MEMORY"} & context.scopes
    ):
        raise HTTPException(
            status_code=403,
            detail=(
                "Emergency information has not been shared with your role for "
                "this patient."
            ),
        )
    card = memory_service.emergency_card(db, patient_id)
    if not card:
        raise HTTPException(status_code=404, detail="No health memory available.")

    audit_service.log(
        db, "EMERGENCY_ACCESS", principal, patient_id=patient_id,
        target="emergency_card", detail=f"role={principal.role}",
    )
    card["access"] = context.as_dict()
    return card
