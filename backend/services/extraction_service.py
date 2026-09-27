"""
Medical entity extraction.

Deliberately rule-based and transparent: a lexicon + regex layer that returns
every entity with the span it came from and a calibrated confidence. Nothing
here invents clinical facts — an entity only exists if its trigger text is
present in the source. Anything it produces is labelled `AI Extracted` until a
human (doctor or reviewer) confirms it.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from utils.helpers import parse_date, relative_day

# --------------------------------------------------------------------------
# Lexicons
# --------------------------------------------------------------------------
MEDICATION_LEXICON = {
    "amlodipine": "Amlodipine", "telmisartan": "Telmisartan",
    "metoprolol": "Metoprolol", "losartan": "Losartan", "ramipril": "Ramipril",
    "atenolol": "Atenolol", "metformin": "Metformin",
    "glimepiride": "Glimepiride", "insulin": "Insulin",
    "sitagliptin": "Sitagliptin", "atorvastatin": "Atorvastatin",
    "rosuvastatin": "Rosuvastatin", "aspirin": "Aspirin",
    "clopidogrel": "Clopidogrel", "warfarin": "Warfarin",
    "pantoprazole": "Pantoprazole", "omeprazole": "Omeprazole",
    "levothyroxine": "Levothyroxine", "thyroxine": "Levothyroxine",
    "furosemide": "Furosemide", "torsemide": "Torsemide",
    "paracetamol": "Paracetamol", "acetaminophen": "Paracetamol",
    "ibuprofen": "Ibuprofen", "donepezil": "Donepezil",
    "memantine": "Memantine", "calcium": "Calcium carbonate",
    "vitamin d3": "Vitamin D3", "cholecalciferol": "Vitamin D3",
    "iron": "Ferrous sulphate", "alprazolam": "Alprazolam",
    "melatonin": "Melatonin", "digoxin": "Digoxin",
    "salbutamol": "Salbutamol", "budesonide": "Budesonide",
}

SYMPTOM_LEXICON = [
    "dizziness", "giddiness", "headache", "chest pain", "breathlessness",
    "shortness of breath", "fatigue", "tiredness", "weakness", "swelling",
    "fever", "cough", "cold", "back pain", "knee pain", "joint pain",
    "blurred vision", "loss of appetite", "nausea", "vomiting",
    "palpitations", "insomnia", "sleeplessness", "confusion", "tremor",
    "constipation", "diarrhoea", "diarrhea", "numbness", "fall", "fainting",
    "burning sensation", "itching", "rash",
]

DIAGNOSIS_LEXICON = [
    "hypertension", "high blood pressure", "type 2 diabetes", "diabetes",
    "arthritis", "osteoarthritis", "asthma", "copd", "dementia",
    "alzheimer", "anaemia", "anemia", "hypothyroidism", "hyperthyroidism",
    "chronic kidney disease", "high cholesterol", "dyslipidaemia",
    "dyslipidemia", "cataract", "osteoporosis", "parkinson",
    "atrial fibrillation", "heart failure", "stroke", "depression",
    "urinary tract infection", "pneumonia",
]

LAB_LEXICON = {
    "hba1c": ("HbA1c", "%"), "fasting blood sugar": ("Fasting Blood Sugar", "mg/dL"),
    "fbs": ("Fasting Blood Sugar", "mg/dL"),
    "post prandial": ("Post Prandial Blood Sugar", "mg/dL"),
    "creatinine": ("Serum Creatinine", "mg/dL"),
    "haemoglobin": ("Haemoglobin", "g/dL"), "hemoglobin": ("Haemoglobin", "g/dL"),
    "ldl": ("LDL Cholesterol", "mg/dL"), "hdl": ("HDL Cholesterol", "mg/dL"),
    "total cholesterol": ("Total Cholesterol", "mg/dL"),
    "triglyceride": ("Triglycerides", "mg/dL"), "tsh": ("TSH", "mIU/L"),
    "vitamin d": ("Vitamin D", "ng/mL"), "vitamin b12": ("Vitamin B12", "pg/mL"),
    "urea": ("Blood Urea", "mg/dL"), "potassium": ("Serum Potassium", "mmol/L"),
    "sodium": ("Serum Sodium", "mmol/L"),
}

SPECIALTIES = [
    "cardiology", "cardiologist", "neurology", "neurologist", "diabetology",
    "diabetologist", "general medicine", "physician", "orthopaedics",
    "orthopedics", "orthopaedic", "geriatrics", "geriatrician", "nephrology",
    "nephrologist", "pulmonology", "pulmonologist", "endocrinology",
    "endocrinologist", "psychiatry", "ophthalmology", "dermatology",
    "urology", "gastroenterology",
]

SPECIALTY_CANONICAL = {
    "cardiologist": "Cardiology", "neurologist": "Neurology",
    "diabetologist": "Diabetology", "physician": "General Medicine",
    "orthopaedic": "Orthopaedics", "orthopedics": "Orthopaedics",
    "geriatrician": "Geriatrics", "nephrologist": "Nephrology",
    "pulmonologist": "Pulmonology", "endocrinologist": "Endocrinology",
}

FREQUENCY_PATTERNS = [
    (r"\bonce\s+(?:a\s+)?daily\b|\bod\b|\bo\.d\.\b", "Once daily"),
    (r"\btwice\s+(?:a\s+)?daily\b|\bbd\b|\bb\.d\.\b|\bbid\b", "Twice daily"),
    (r"\bthrice\s+(?:a\s+)?daily\b|\btds\b|\bt\.d\.s\.\b|\btid\b", "Three times daily"),
    (r"\bfour\s+times\s+(?:a\s+)?daily\b|\bqid\b", "Four times daily"),
    (r"\bevery\s+night\b|\bat\s+bedtime\b|\bhs\b|\bnight\b", "At night"),
    (r"\bevery\s+morning\b|\bmorning\b", "Every morning"),
    (r"\bweekly\b", "Once weekly"),
    (r"\bsos\b|\bwhen\s+(?:required|needed)\b", "When required (SOS)"),
    (r"\balternate\s+day", "Alternate days"),
]

MEDICATION_CHANGE_HINTS = [
    "changed", "change", "switched", "increased", "reduced", "decreased",
    "stopped", "discontinued", "started", "added", "revised", "adjusted",
    "titrated", "doubled", "halved",
]

DOSE_RE = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(mg|mcg|g|ml|iu|units?|tabs?|tablets?)\b", re.I
)
DOCTOR_RE = re.compile(
    r"\bDr\.?\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,2})", re.M
)
HOSPITAL_RE = re.compile(
    r"\b([A-Z][A-Za-z&.'\-]*(?:\s+[A-Z][A-Za-z&.'\-]*){0,3}\s+"
    r"(?:Hospital|Hospitals|Clinic|Nursing\s+Home|Medical\s+Centre|"
    r"Medical\s+Center|Health\s+Centre|Diagnostics|Laboratory|Labs?))\b"
)
DATE_RE = re.compile(
    r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}|"
    r"\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?"
    r"(?:\s+\d{4})?)\b",
    re.I,
)
ALLERGY_RE = re.compile(
    r"allerg(?:y|ic)\s*(?:to|:)?\s*([A-Za-z][A-Za-z0-9\s,\-]{2,60})", re.I
)
BP_RE = re.compile(r"\b(\d{2,3})\s*/\s*(\d{2,3})\s*(?:mm\s*hg)?\b", re.I)


def _clip(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 4)


def _find_frequency(window: str) -> Optional[str]:
    for pattern, label in FREQUENCY_PATTERNS:
        if re.search(pattern, window, re.I):
            return label
    return None


def _fuzzy_medication_candidates(text: str):
    """
    Approximate matches against the drug lexicon.

    OCR of a handwritten prescription rarely returns a clean drug name — it
    returns things like "Amlod!pine" or "amlod pine". A real medication reader
    has to match approximately against a known lexicon and then *lower its
    confidence accordingly*, which is exactly what this does: the match is
    reported with the similarity baked into the score, and the raw OCR string
    is preserved so a reviewer can see what was actually on the page.
    """
    import difflib

    words = [
        (match.group(0), match.start(), match.end())
        for match in re.finditer(r"[A-Za-z][A-Za-z0-9!|]{2,}", text)
    ]
    candidates = []
    for index, (word, start, end) in enumerate(words):
        candidates.append((word, start, end))
        if index + 1 < len(words):
            nxt = words[index + 1]
            # Handwriting often splits one word across a gap.
            candidates.append((word + nxt[0], start, nxt[2]))

    results = {}
    for raw, start, end in candidates:
        cleaned = re.sub(r"[^a-z]", "", raw.lower().replace("!", "i").replace("|", "l"))
        if len(cleaned) < 5:
            continue
        for key, canonical in MEDICATION_LEXICON.items():
            if abs(len(cleaned) - len(key)) > 3:
                continue
            ratio = difflib.SequenceMatcher(None, cleaned, key).ratio()
            if ratio < 0.80:
                continue
            existing = results.get(canonical)
            if existing and existing["ratio"] >= ratio:
                continue
            results[canonical] = {
                "canonical": canonical,
                "raw": raw,
                "ratio": round(ratio, 3),
                "start": start,
                "end": end,
            }
    return results


def extract_medications(text: str, base_confidence: float) -> List[Dict[str, Any]]:
    """Find medication mentions with their dose / frequency in a local window."""
    found: List[Dict[str, Any]] = []
    lowered = text.lower()

    spans: List[tuple] = []
    for key, canonical in MEDICATION_LEXICON.items():
        for match in re.finditer(re.escape(key), lowered):
            spans.append((canonical, match.start(), match.end(), 1.0, text[match.start():match.end()]))

    exact_names = {span[0] for span in spans}
    for canonical, candidate in _fuzzy_medication_candidates(text).items():
        if canonical in exact_names:
            continue
        spans.append(
            (canonical, candidate["start"], candidate["end"],
             candidate["ratio"], candidate["raw"])
        )

    ordered = sorted(spans, key=lambda s: s[1])
    for index, (canonical, start, end, ratio, raw_text) in enumerate(ordered):
        # Dose and frequency belong to *this* drug: look forward only, and stop
        # at the next drug name or the end of the line, whichever comes first.
        next_start = ordered[index + 1][1] if index + 1 < len(ordered) else len(text)
        forward = text[end: min(len(text), end + 90, next_start)]
        line_break = forward.find("\n")
        if line_break > 12:
            forward = forward[:line_break]
        window = f"{text[max(0, start - 25):end]}{forward}"

        dose_match = DOSE_RE.search(forward)
        dose = None
        if dose_match:
            unit = dose_match.group(2).lower()
            unit = "mg" if unit.startswith("mg") else unit
            dose = f"{dose_match.group(1)} {unit}"
        frequency = _find_frequency(forward)
        instruction = None
        for phrase in ("after food", "before food", "empty stomach",
                       "with water", "after meals", "before meals"):
            if phrase in forward.lower():
                instruction = phrase.title()
                break
        changed = any(hint in window.lower() for hint in MEDICATION_CHANGE_HINTS)

        # An approximate lexicon match is *less* certain than an exact one, and
        # the score has to say so.
        match_penalty = 0.0 if ratio >= 0.999 else (1 - ratio) * 1.3
        name_confidence = _clip(base_confidence + 0.04 - match_penalty)

        entry = {
            "name": canonical,
            "raw": raw_text,
            "match_ratio": ratio,
            "exact_match": ratio >= 0.999,
            "dose": dose,
            "frequency": frequency,
            "instruction": instruction,
            "is_change": changed,
            "context": window.strip(),
            "confidence": {
                "name": name_confidence,
                "dose": _clip(base_confidence - 0.01) if dose else None,
                "frequency": _clip(base_confidence - 0.09) if frequency else None,
            },
        }
        if not any(existing["name"] == canonical for existing in found):
            found.append(entry)
    return found


def extract_doctor(text: str) -> Optional[Dict[str, Any]]:
    match = DOCTOR_RE.search(text)
    if not match:
        return None
    name = match.group(1).strip()
    # Trim trailing sentence words that got swept into the name.
    stop_words = {"On", "The", "He", "She", "Has", "Advised", "Asked", "Said",
                  "Prescribed", "Changed", "Reviewed", "Last", "Yesterday"}
    parts = [p for p in name.split() if p not in stop_words]
    name = " ".join(parts[:3]) if parts else name

    specialty = None
    lowered = text.lower()
    for word in SPECIALTIES:
        if word in lowered:
            specialty = SPECIALTY_CANONICAL.get(word, word.title())
            break

    hospital_match = HOSPITAL_RE.search(text)
    reg_match = re.search(r"\b(?:reg(?:n|istration)?\.?\s*(?:no\.?)?\s*[:#]?\s*)"
                          r"([A-Z0-9/\-]{4,20})", text, re.I)
    return {
        "name": f"Dr. {name}",
        "specialty": specialty,
        "hospital": hospital_match.group(1).strip() if hospital_match else None,
        "registration_no": reg_match.group(1) if reg_match else None,
    }


def extract_dates(text: str, reference: Optional[datetime] = None) -> List[datetime]:
    dates: List[datetime] = []
    for match in DATE_RE.finditer(text):
        raw = match.group(1)
        if re.fullmatch(r"\d{1,2}\s+\w+", raw):
            raw = f"{raw} {(reference or datetime.utcnow()).year}"
        parsed = parse_date(raw)
        if parsed:
            dates.append(parsed)
    relative = relative_day(text, reference)
    if relative:
        dates.append(relative)
    return dates


def extract_entities(
    text: str,
    base_confidence: float = 0.92,
    reference: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Single entry point used by text, voice and OCR ingestion alike."""
    text = text or ""
    lowered = text.lower()

    symptoms = sorted({s for s in SYMPTOM_LEXICON if s in lowered})
    diagnoses = sorted({d for d in DIAGNOSIS_LEXICON if d in lowered})

    labs: List[Dict[str, Any]] = []
    for key, (label, unit) in LAB_LEXICON.items():
        index = lowered.find(key)
        if index == -1:
            continue
        window = text[index: index + 90]
        value_match = re.search(r"[:\-]?\s*(\d+(?:\.\d+)?)", window[len(key):])
        labs.append({
            "test_name": label,
            "value": value_match.group(1) if value_match else None,
            "unit": unit,
            "confidence": _clip(base_confidence - 0.03),
        })

    allergies = []
    for match in ALLERGY_RE.finditer(text):
        substance = match.group(1).strip().split(".")[0].split(" and ")[0]
        substance = re.sub(r"\s+(which|that|since|because|causing).*$", "",
                           substance, flags=re.I).strip(" ,;")
        if 2 < len(substance) < 60:
            allergies.append({
                "substance": substance.title(),
                "confidence": _clip(base_confidence - 0.05),
            })

    bp_match = BP_RE.search(text)
    vitals = {}
    if bp_match:
        vitals["blood_pressure"] = f"{bp_match.group(1)}/{bp_match.group(2)} mmHg"

    medications = extract_medications(text, base_confidence)
    doctor = extract_doctor(text)
    dates = extract_dates(text, reference)

    return {
        "medications": medications,
        "doctor": doctor,
        "symptoms": symptoms,
        "diagnoses": diagnoses,
        "lab_results": labs,
        "allergies": allergies,
        "vitals": vitals,
        "dates": [d.isoformat() for d in dates],
        "event_date": (dates[0] if dates else None),
        "has_medication_change": any(m["is_change"] for m in medications),
        "text_length": len(text),
    }


def summarise_entities(entities: Dict[str, Any]) -> str:
    """Short human-readable line describing what was recognised."""
    parts = []
    if entities.get("doctor"):
        parts.append(f"doctor {entities['doctor']['name']}")
    meds = entities.get("medications") or []
    if meds:
        parts.append(f"{len(meds)} medication(s)")
    if entities.get("symptoms"):
        parts.append(f"{len(entities['symptoms'])} symptom(s)")
    if entities.get("diagnoses"):
        parts.append(f"{len(entities['diagnoses'])} condition(s)")
    if entities.get("lab_results"):
        parts.append(f"{len(entities['lab_results'])} lab value(s)")
    if entities.get("allergies"):
        parts.append("allergy information")
    return ", ".join(parts) if parts else "no structured medical entities"
