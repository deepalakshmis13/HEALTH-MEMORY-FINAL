"""
Confidence scoring and the verification routing decision (§11–§13).

Every OCR-extracted field carries its own confidence. The routing rule is
implemented exactly once, here, and reads its thresholds from `config.py`.
"""

from typing import Any, Dict, List

from config import (
    CLINICALLY_IMPORTANT_FIELDS,
    HIGH_CONFIDENCE_THRESHOLD,
    MEDIUM_CONFIDENCE_THRESHOLD,
)

FIELD_LABELS = {
    "medication_name": "Medication",
    "medication_dose": "Dose",
    "medication_frequency": "Frequency",
    "prescription_instruction": "Prescription instruction",
    "medication_change": "Medication change",
    "allergy": "Allergy",
    "critical_instruction": "Critical instruction",
    "doctor_name": "Doctor",
    "doctor_specialty": "Specialty",
    "hospital": "Hospital / Clinic",
    "consultation_date": "Consultation date",
    "diagnosis": "Diagnosis",
    "symptom": "Symptom",
    "lab_result": "Lab result",
    "vitals": "Vitals",
    "document_text": "Document text",
}


def band(confidence: float) -> str:
    """HIGH / MEDIUM / LOW for a 0.0–1.0 confidence."""
    if confidence is None:
        return "UNKNOWN"
    if confidence >= HIGH_CONFIDENCE_THRESHOLD:
        return "HIGH"
    if confidence >= MEDIUM_CONFIDENCE_THRESHOLD:
        return "MEDIUM"
    return "LOW"


def is_clinically_important(field_key: str) -> bool:
    return field_key in CLINICALLY_IMPORTANT_FIELDS


def needs_verification(field: Dict[str, Any]) -> bool:
    """
    §13 — the reviewer must NOT receive every record.

        IF   confidence < HIGH_CONFIDENCE_THRESHOLD
        AND  the field is clinically important
        THEN create a reviewer verification task
    """
    confidence = field.get("confidence")
    if confidence is None:
        return False
    return (
        confidence < HIGH_CONFIDENCE_THRESHOLD
        and is_clinically_important(field.get("field", ""))
    )


def priority_for(confidence: float) -> str:
    """LOW confidence -> HIGH priority queue item."""
    return "HIGH" if confidence < MEDIUM_CONFIDENCE_THRESHOLD else "NORMAL"


def status_label(confidence: float, important: bool) -> str:
    if confidence >= HIGH_CONFIDENCE_THRESHOLD or not important:
        return "NOT_REQUIRED"
    return "PENDING_VERIFICATION"


def describe(confidence: float, important: bool) -> str:
    level = band(confidence)
    if level == "HIGH":
        return "Accepted into health memory (high confidence)."
    if not important:
        return "Stored with provenance — not a clinically critical field."
    if level == "MEDIUM":
        return "Needs Verification — routed to the reviewer queue."
    return "High Priority Verification — routed to the reviewer queue."


def build_field(
    field_key: str,
    value: Any,
    confidence: float,
    context: str = "",
) -> Dict[str, Any]:
    confidence = round(float(confidence or 0.0), 4)
    important = is_clinically_important(field_key)
    return {
        "field": field_key,
        "label": FIELD_LABELS.get(field_key, field_key.replace("_", " ").title()),
        "value": None if value is None else str(value),
        "confidence": confidence,
        "band": band(confidence),
        "clinically_important": important,
        "needs_verification": needs_verification(
            {"field": field_key, "confidence": confidence}
        ),
        "priority": priority_for(confidence),
        "verification_status": status_label(confidence, important),
        "note": describe(confidence, important),
        "context": context,
    }


def overall_confidence(fields: List[Dict[str, Any]]) -> float:
    """
    Weighted mean — clinically important fields dominate the document score,
    and the weakest important field drags the document down (a prescription is
    only as trustworthy as its least legible dose).
    """
    if not fields:
        return 0.0
    weighted_sum = 0.0
    weight_total = 0.0
    important_scores = []
    for field in fields:
        weight = 2.0 if field.get("clinically_important") else 1.0
        weighted_sum += (field.get("confidence") or 0.0) * weight
        weight_total += weight
        if field.get("clinically_important"):
            important_scores.append(field.get("confidence") or 0.0)
    mean = weighted_sum / weight_total if weight_total else 0.0
    if important_scores:
        mean = min(mean, (mean + min(important_scores)) / 2 + 0.02)
    return round(max(0.0, min(1.0, mean)), 4)


def summarise(fields: List[Dict[str, Any]]) -> Dict[str, Any]:
    flagged = [f for f in fields if f["needs_verification"]]
    return {
        "overall_confidence": overall_confidence(fields),
        "fields_total": len(fields),
        "fields_flagged": len(flagged),
        "high_priority": sum(1 for f in flagged if f["priority"] == "HIGH"),
        "thresholds": {
            "high": HIGH_CONFIDENCE_THRESHOLD,
            "medium": MEDIUM_CONFIDENCE_THRESHOLD,
        },
    }
