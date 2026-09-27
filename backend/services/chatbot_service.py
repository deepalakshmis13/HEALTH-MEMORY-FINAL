"""
Role-specific chatbot orchestration (§22, §36, §43).

    authorization -> consent -> retrieval -> context -> role agent ->
    AI provider -> answer + evidence

Four distinct agents, four distinct system prompts, one shared memory.
"""

from typing import Any, Dict, List, Optional

from database import Session

from agents import (
    ai_provider,
    caregiver_agent,
    doctor_agent,
    memory_agent,
    patient_agent,
    reviewer_agent,
)
from rag import context_builder
from services import audit_service
from services.authorization_service import require_patient_access

AGENTS = {
    "patient": patient_agent,
    "doctor": doctor_agent,
    "caregiver": caregiver_agent,
    "reviewer": reviewer_agent,
}

ROLE_SOURCE_FOCUS = {
    "reviewer": [
        "DOCTOR_DOCUMENT", "HANDWRITTEN_DOCUMENT", "SCANNED_DOCUMENT", "OCR",
        "REVIEWER_VERIFIED", "DOCTOR_RECORDED", "PATIENT_TEXT", "PATIENT_VOICE",
    ],
}


def agent_profile(role: str) -> Dict[str, Any]:
    agent = AGENTS[role]
    return {
        "role": role,
        "name": agent.NAME,
        "quick_actions": agent.QUICK_ACTIONS,
        "system_prompt": agent.SYSTEM_PROMPT,
    }


def ask(
    db: Session,
    principal,
    role: str,
    patient_id: int,
    message: str,
    history: Optional[List[Dict[str, str]]] = None,
    extras: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if role not in AGENTS:
        raise ValueError(f"Unknown chatbot role '{role}'")

    context = require_patient_access(db, principal, patient_id)

    bundle = memory_agent.gather(
        db, context, message, actor=principal,
        top_k=10,
        source_types=ROLE_SOURCE_FOCUS.get(role),
        extras=extras,
    )

    agent = AGENTS[role]
    built = agent.build(db, bundle)

    provider = ai_provider.get_provider()
    generated = provider.generate(
        system_prompt=built["system_prompt"],
        context_text=bundle.context_text,
        question=message,
        grounded_draft=built["grounded_draft"],
        history=history or [],
    )

    audit_service.log(
        db, "CHAT_QUERY", principal, patient_id=patient_id,
        target=f"{role}:{built['agent']}",
        detail=(
            f"intent={bundle.intent}; sources={len(bundle.sources)}; "
            f"provider={generated['provider']}"
        ),
    )

    return {
        "answer": generated["answer"],
        "sources": bundle.sources,
        "evidence": context_builder.evidence_panel(bundle.sources),
        "agent": built["agent"],
        "provider": generated["provider"],
        "model": generated.get("model"),
        "intent": bundle.intent,
        "quick_actions": built["quick_actions"],
        "explanation": _explanation(bundle),
        "retrieval": {
            "chunks_considered": bundle.built["chunks_considered"],
            "chunks_used": bundle.built["chunks_used"],
            "filters": bundle.filters,
        },
    }


def _explanation(bundle: memory_agent.MemoryBundle) -> str:
    """'Why am I seeing this?' (§36)."""
    if not bundle.sources:
        return (
            "No health-memory records passed the consent and authorization "
            "filters for this question, so nothing was used to answer it."
        )
    kinds = sorted({source["source_type"] for source in bundle.sources})
    return (
        f"Answered using {len(bundle.sources)} authorized health-memory "
        f"record(s) ({', '.join(kinds)}) for "
        f"{bundle.patient.full_name}. Access basis: {bundle.context.reason}; "
        f"consent scopes: {', '.join(sorted(bundle.context.scopes)) or 'none'}."
    )
