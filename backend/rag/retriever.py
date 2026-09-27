"""
Consent-aware RAG retrieval (§19, §20).

The order below is the whole point of the system and is not negotiable:

    1. patient isolation
    2. user authentication      (handled by the route dependency)
    3. role authorization       (authorization_service)
    4. consent restrictions     (consent_service)
    5. source verification status
    6. relevance
    7. recency

Unauthorised records are removed from the candidate set *before* scoring. The
language model is never asked to ignore something it can see.
"""

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from database import Session

from config import (
    HIGH_CONFIDENCE_THRESHOLD,
    RAG_RECENCY_HALFLIFE_DAYS,
    RAG_TOP_K,
)
from models import MemoryChunk
from rag.embeddings import cosine, embed, keyword_overlap
from services import consent_service
from services.authorization_service import AccessContext

# What each role may retrieve, on top of consent.
ROLE_SOURCE_POLICY = {
    "patient": None,  # everything about themselves
    "doctor": None,   # everything consented
    "caregiver": {
        "PATIENT_TEXT", "PATIENT_VOICE", "CAREGIVER_RECORDED", "DOCTOR_RECORDED",
        "REVIEWER_VERIFIED", "DOCTOR_DOCUMENT", "HANDWRITTEN_DOCUMENT",
        "SCANNED_DOCUMENT", "OCR",
    },
    "reviewer": {
        "DOCTOR_DOCUMENT", "HANDWRITTEN_DOCUMENT", "SCANNED_DOCUMENT", "OCR",
        "REVIEWER_VERIFIED", "DOCTOR_RECORDED", "PATIENT_TEXT", "PATIENT_VOICE",
    },
}

# Event types a caregiver may never retrieve regardless of consent.
CAREGIVER_BLOCKED_SCOPES = {"VOICE_DIARY"}


@dataclass
class RetrievedChunk:
    chunk: MemoryChunk
    score: float
    relevance: float
    recency: float
    trust: float
    reasons: List[str] = field(default_factory=list)

    def to_source(self) -> Dict[str, Any]:
        return {
            "source_id": self.chunk.source_id,
            "title": self.chunk.title or "Health memory entry",
            "source_type": self.chunk.source_type,
            "date": self.chunk.event_date.isoformat() if self.chunk.event_date else None,
            "trust_level": self.chunk.trust_level,
            "confidence": self.chunk.confidence,
            "verification_status": self.chunk.verification_status,
            "author": self.chunk.author,
            "excerpt": (self.chunk.text or "")[:280],
            "score": round(self.score, 4),
        }


def _recency_score(event_date: Optional[datetime]) -> float:
    if not event_date:
        return 0.3
    age_days = max(0.0, (datetime.utcnow() - event_date).total_seconds() / 86400)
    return round(math.pow(0.5, age_days / max(1.0, RAG_RECENCY_HALFLIFE_DAYS)), 4)


def _trust_score(chunk: MemoryChunk) -> float:
    """
    §16 — verified / high-confidence information outranks unverified extraction,
    but nothing is silently discarded: low-trust chunks stay retrievable and
    carry their status into the evidence panel.
    """
    status = (chunk.verification_status or "NOT_REQUIRED").upper()
    confidence = chunk.confidence if chunk.confidence is not None else 1.0
    base = {
        "VERIFIED": 1.0,
        "CORRECTED": 1.0,
        "NOT_REQUIRED": 0.9,
        "PENDING_VERIFICATION": 0.45,
        "REJECTED": 0.05,
    }.get(status, 0.7)
    if confidence < HIGH_CONFIDENCE_THRESHOLD and status not in {
        "VERIFIED", "CORRECTED"
    }:
        base *= 0.75 + (confidence * 0.25)
    return round(min(1.0, base), 4)


def candidate_chunks(
    db: Session,
    context: AccessContext,
    include_rejected: bool = False,
) -> List[MemoryChunk]:
    """Steps 1–5: everything the viewer is *allowed* to see, before relevance."""
    rows = (
        db.query(MemoryChunk)
        .filter(MemoryChunk.patient_id == context.patient_id)  # 1. isolation
        .all()
    )

    allowed_sources = ROLE_SOURCE_POLICY.get(context.role)  # 3. role policy
    permitted: List[MemoryChunk] = []
    for chunk in rows:
        if allowed_sources is not None and chunk.source_type not in allowed_sources:
            continue
        scope = chunk.consent_scope or "FULL_HEALTH_MEMORY"       # 4. consent
        if context.role != "patient":
            if scope not in context.scopes and "FULL_HEALTH_MEMORY" not in context.scopes:
                continue
            if context.role == "caregiver" and scope in CAREGIVER_BLOCKED_SCOPES:
                continue
        if not include_rejected and (                             # 5. verification
            chunk.verification_status or ""
        ).upper() == "REJECTED":
            continue
        permitted.append(chunk)
    return permitted


def retrieve(
    db: Session,
    context: AccessContext,
    query: str,
    top_k: int = RAG_TOP_K,
    source_types: Optional[List[str]] = None,
    since: Optional[datetime] = None,
    include_rejected: bool = False,
) -> List[RetrievedChunk]:
    pool = candidate_chunks(db, context, include_rejected=include_rejected)
    if source_types:
        allowed = set(source_types)
        pool = [c for c in pool if c.source_type in allowed]
    if since:
        pool = [c for c in pool if c.event_date and c.event_date >= since]
    if not pool:
        return []

    query_vector = embed(query or "")
    scored: List[RetrievedChunk] = []
    for chunk in pool:
        semantic = cosine(query_vector, chunk.vector or [])
        lexical = keyword_overlap(query or "", f"{chunk.title} {chunk.text}")
        relevance = (semantic * 0.62) + (lexical * 0.38)          # 6. relevance
        recency = _recency_score(chunk.event_date)                # 7. recency
        trust = _trust_score(chunk)
        score = (relevance * 0.60) + (recency * 0.22) + (trust * 0.18)

        reasons = []
        if lexical > 0.3:
            reasons.append("keyword match")
        if semantic > 0.25:
            reasons.append("semantic match")
        if recency > 0.6:
            reasons.append("recent")
        if trust >= 0.9:
            reasons.append("verified source")
        scored.append(RetrievedChunk(chunk, score, relevance, recency, trust, reasons))

    scored.sort(key=lambda item: item.score, reverse=True)

    # Keep a floor of recent context even for a vague question.
    top = scored[:top_k]
    if len(top) < top_k:
        return top
    if all(item.relevance < 0.08 for item in top):
        recent_first = sorted(
            scored, key=lambda item: item.chunk.event_date or datetime.min, reverse=True
        )
        top = recent_first[:top_k]
    return top


def retrieve_recent(
    db: Session, context: AccessContext, limit: int = 12
) -> List[RetrievedChunk]:
    pool = candidate_chunks(db, context)
    pool.sort(key=lambda c: c.event_date or datetime.min, reverse=True)
    return [
        RetrievedChunk(chunk, 1.0, 0.0, _recency_score(chunk.event_date),
                       _trust_score(chunk), ["recent"])
        for chunk in pool[:limit]
    ]


def describe_filters(db: Session, context: AccessContext) -> Dict[str, Any]:
    """Used by the 'Why am I seeing this?' panel (§36)."""
    return {
        "patient_isolation": f"patient_id = {context.patient_id}",
        "role": context.role,
        "relationship": context.reason,
        "granted_consent_scopes": sorted(context.scopes),
        "source_policy": sorted(ROLE_SOURCE_POLICY.get(context.role) or ["all"]),
        "verification_rule": "REJECTED sources are excluded from retrieval",
        "thresholds": {"high_confidence": HIGH_CONFIDENCE_THRESHOLD},
        "consent_scope_map": {
            scope: sorted(types)
            for scope, types in consent_service.SCOPE_EVENT_TYPES.items()
        },
    }
