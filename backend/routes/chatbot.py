"""The four role-specific chatbot endpoints (§22)."""

from fastapi import APIRouter, Depends, HTTPException
from database import Session

from agents import ai_provider
from auth import Principal, get_current_user, require_roles
from database import get_db
from schemas import ChatRequest
from services import chatbot_service

router = APIRouter(prefix="/api/chat", tags=["chatbots"])


def _resolve_patient_id(principal: Principal, payload: ChatRequest) -> int:
    patient_id = payload.patient_id or (
        principal.patient_id if principal.role == "patient" else None
    )
    if not patient_id:
        raise HTTPException(
            status_code=400, detail="Select a patient before asking a question."
        )
    return patient_id


@router.get("/agents")
def agents():
    return {
        "agents": [
            chatbot_service.agent_profile(role)
            for role in ("patient", "doctor", "caregiver", "reviewer")
        ],
        "provider": ai_provider.provider_status(),
    }


@router.post("/patient")
def chat_patient(
    payload: ChatRequest,
    principal: Principal = Depends(require_roles("patient")),
    db: Session = Depends(get_db),
):
    return chatbot_service.ask(
        db, principal, "patient", _resolve_patient_id(principal, payload),
        payload.message, payload.history,
    )


@router.post("/doctor")
def chat_doctor(
    payload: ChatRequest,
    principal: Principal = Depends(require_roles("doctor")),
    db: Session = Depends(get_db),
):
    return chatbot_service.ask(
        db, principal, "doctor", _resolve_patient_id(principal, payload),
        payload.message, payload.history,
    )


@router.post("/caregiver")
def chat_caregiver(
    payload: ChatRequest,
    principal: Principal = Depends(require_roles("caregiver")),
    db: Session = Depends(get_db),
):
    extras = {}
    for turn in payload.history or []:
        if turn.get("role") == "system" and turn.get("content", "").startswith("shift:"):
            extras["shift_id"] = int(turn["content"].split(":", 1)[1])
    return chatbot_service.ask(
        db, principal, "caregiver", _resolve_patient_id(principal, payload),
        payload.message, payload.history, extras=extras,
    )


@router.post("/reviewer")
def chat_reviewer(
    payload: ChatRequest,
    principal: Principal = Depends(require_roles("reviewer")),
    db: Session = Depends(get_db),
):
    return chatbot_service.ask(
        db, principal, "reviewer", _resolve_patient_id(principal, payload),
        payload.message, payload.history,
    )
