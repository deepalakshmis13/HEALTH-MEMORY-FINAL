"""
Tamil / English / mixed-speech handling for patient-entered text.

What this does
--------------
Patients speak and type in Tamil, in English, or in the mixture both are
actually used in ("எனக்கு two days-ஆ தலை வலிக்குது"). The extraction pipeline
downstream reads English, so this module produces an *assisted English reading*
of a Tamil or mixed entry while the patient's own words are stored untouched.

What this deliberately does NOT do
----------------------------------
It never turns anything a patient says into a confirmed diagnosis. The reading
is a plain-language restatement, marked ``assisted_reading`` and carried with
``trust_level="Patient Reported"``, and it enters exactly the same human-review
workflow as any other patient entry. A symptom stays a reported symptom; only a
doctor's record or a verified document can make it anything more.

Approach
--------
A phrase table, not a translation service. Every mapping here is a fixed,
reviewable pair, so the reading is deterministic, works offline, and cannot
hallucinate a clinical claim the patient did not make. Anything not in the
table is left in the patient's own words rather than guessed at.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

# Tamil Unicode block.
TAMIL_RANGE = re.compile(r"[஀-௿]")
LATIN_RANGE = re.compile(r"[A-Za-z]")

LANGUAGE_ENGLISH = "en"
LANGUAGE_TAMIL = "ta"
LANGUAGE_MIXED = "ta-en"


# ---------------------------------------------------------------------------
# Phrase table
#
# Ordered longest-first at match time. Each entry maps a Tamil surface form to
# the English wording a doctor or caregiver reading the record would expect.
# ---------------------------------------------------------------------------
NUMBERS: Dict[str, str] = {
    "ஒரு": "one", "ஒன்று": "one", "இரண்டு": "two", "ரெண்டு": "two",
    "மூன்று": "three", "மூணு": "three", "நான்கு": "four", "நாலு": "four",
    "ஐந்து": "five", "அஞ்சு": "five", "ஆறு": "six", "ஏழு": "seven",
    "எட்டு": "eight", "ஒன்பது": "nine", "பத்து": "ten", "பதினைந்து": "fifteen",
    "இருபது": "twenty", "முப்பது": "thirty",
}

TIME_UNITS: Dict[str, str] = {
    "நாள்": "day", "நாட்கள்": "days", "நாளா": "days", "நாளாக": "days",
    "நாளாச்": "days", "நாளைக்கு": "a day", "வாரம்": "week", "வாரங்கள்": "weeks",
    "வாரமா": "weeks", "வாரமாக": "weeks", "மாதம்": "month", "மாதங்கள்": "months",
    "மாதமா": "months", "மாதமாக": "months", "வருடம்": "year", "வருடங்கள்": "years",
    "வருஷம்": "year", "மணி": "hour", "மணிநேரம்": "hours", "நேரம்": "time",
}

SYMPTOMS: Dict[str, str] = {
    "தலை வலி": "headache", "தலைவலி": "headache",
    "தலை வலிக்குது": "a headache", "தலை வலிக்கிறது": "a headache",
    "வயிற்று வலி": "stomach pain", "வயிறு வலி": "stomach pain",
    "மார்பு வலி": "chest pain", "நெஞ்சு வலி": "chest pain",
    "முதுகு வலி": "back pain", "மூட்டு வலி": "joint pain",
    "கால் வலி": "leg pain", "கை வலி": "arm pain", "பல் வலி": "tooth pain",
    "காது வலி": "ear pain", "தொண்டை வலி": "sore throat",
    "வலி": "pain", "வலிக்குது": "pain", "வலிக்கிறது": "pain",
    "காய்ச்சல்": "fever", "ஜுரம்": "fever",
    "இருமல்": "cough", "சளி": "cold", "தும்மல்": "sneezing",
    "மயக்கம்": "dizziness", "தலைச்சுற்றல்": "dizziness",
    "வாந்தி": "vomiting", "குமட்டல்": "nausea",
    "வயிற்றுப்போக்கு": "loose motions", "மலச்சிக்கல்": "constipation",
    "மூச்சுத் திணறல்": "breathlessness", "மூச்சு திணறல்": "breathlessness",
    "மூச்சு வாங்குது": "breathlessness",
    "சோர்வு": "tiredness", "களைப்பு": "tiredness", "பலவீனம்": "weakness",
    "தூக்கமின்மை": "poor sleep", "தூக்கம் வரலை": "poor sleep",
    "பசியின்மை": "poor appetite", "பசி இல்லை": "no appetite",
    "வீக்கம்": "swelling", "அரிப்பு": "itching", "தடிப்பு": "rash",
    "நடுக்கம்": "tremor", "மறதி": "forgetfulness",
    "கண் எரிச்சல்": "eye irritation", "கண் மங்கல்": "blurred vision",
    "நெஞ்செரிச்சல்": "heartburn", "வெர்டிகோ": "vertigo",
    "விழுந்தேன்": "I had a fall", "விழுந்துட்டேன்": "I had a fall",
}

CONDITIONS: Dict[str, str] = {
    "சர்க்கரை நோய்": "diabetes", "சர்க்கரை": "blood sugar", "நீரிழிவு": "diabetes",
    "ரத்த அழுத்தம்": "blood pressure", "இரத்த அழுத்தம்": "blood pressure",
    "பிபி": "blood pressure", "பி.பி.": "blood pressure",
    "கொலஸ்ட்ரால்": "cholesterol", "தைராய்டு": "thyroid",
    "ஆஸ்துமா": "asthma", "மூட்டுவலி நோய்": "arthritis",
    "இதய நோய்": "heart condition", "சிறுநீரக": "kidney",
    "ஒவ்வாமை": "allergy", "அலர்ஜி": "allergy",
}

BODY_PARTS: Dict[str, str] = {
    "தலை": "head", "வயிறு": "stomach", "வயித்து": "stomach", "நெஞ்சு": "chest",
    "மார்பு": "chest", "முதுகு": "back", "இடுப்பு": "hip", "கால்": "leg",
    "கால்கள்": "legs", "கை": "arm", "கைகள்": "arms", "கண்": "eye",
    "கண்கள்": "eyes", "காது": "ear", "பல்": "tooth", "பற்கள்": "teeth",
    "தொண்டை": "throat", "மூட்டு": "joint", "மூட்டுகள்": "joints",
    "முழங்கால்": "knee", "தோள்": "shoulder", "கழுத்து": "neck",
}

PAIN_VERBS = {
    "வலிக்குது", "வலிக்கிறது", "வலிக்கிறார்", "வலி", "வலிக்குதுங்க",
    "வலிக்கிது", "வலித்தது",
}

PRONOUNS: Dict[str, str] = {
    "அவர்": "he", "அவங்க": "they", "அவள்": "she", "அவர்கள்": "they",
    "நாங்கள்": "we", "நீங்கள்": "you", "இது": "this", "அது": "that",
    "வருது": "is coming", "வருகிறது": "is coming", "போகுது": "is going",
    "ஆகுது": "is happening", "தெரியலை": "do not know",
}

CARE_WORDS: Dict[str, str] = {
    "மருத்துவர்": "doctor", "டாக்டர்": "doctor", "வைத்தியர்": "doctor",
    "மருத்துவமனை": "hospital", "ஆஸ்பத்திரி": "hospital",
    "மருந்து": "medicine", "மாத்திரை": "tablet", "மாத்திரைகள்": "tablets",
    "ஊசி": "injection", "மருந்துச்சீட்டு": "prescription",
    "பரிசோதனை": "test", "ரத்த பரிசோதனை": "blood test", "ஸ்கேன்": "scan",
    "ரிப்போர்ட்": "report", "செக்கப்": "check-up",
    "பராமரிப்பாளர்": "caregiver", "செவிலியர்": "nurse",
    "காலை": "in the morning", "மதியம்": "in the afternoon",
    "இரவு": "at night", "சாயங்காலம்": "in the evening",
    "சாப்பாட்டுக்கு முன்": "before food", "சாப்பாட்டுக்கு பின்": "after food",
    "உணவுக்கு பிறகு": "after food",
    "இன்று": "today", "இன்னைக்கு": "today", "நேற்று": "yesterday",
    "நேத்து": "yesterday", "நாளை": "tomorrow",
    "கடந்த": "last", "போன": "last", "கடந்த வாரம்": "last week",
    "திங்கள்": "Monday", "செவ்வாய்": "Tuesday", "புதன்": "Wednesday",
    "வியாழன்": "Thursday", "வெள்ளி": "Friday", "சனி": "Saturday",
    "ஞாயிறு": "Sunday",
}

VERBS_AND_GLUE: Dict[str, str] = {
    "எனக்கு": "I have", "என்னுடைய": "my", "என்": "my", "நான்": "I",
    "இருக்கு": "", "இருக்கிறது": "", "இருந்தது": "had",
    "ஆரம்பித்தது": "started", "ஆரம்பிச்சது": "started", "தொடங்கியது": "started",
    "நிறுத்தினார்": "stopped", "நிறுத்தி": "stopped",
    "மாற்றினார்": "changed", "மாத்தினாரு": "changed", "மாற்றி": "changed",
    "கொடுத்தார்": "gave", "குடுத்தாரு": "gave", "எழுதினார்": "prescribed",
    "சொன்னார்": "said", "சொன்னாரு": "said",
    "பார்த்தேன்": "saw", "பார்த்தன்": "saw", "சந்தித்தேன்": "met",
    "போனேன்": "went", "வந்தேன்": "came",
    "எடுத்துக்கிறேன்": "am taking", "எடுக்கிறேன்": "am taking",
    "சாப்பிடுகிறேன்": "am taking", "சாப்பிடறேன்": "am taking",
    "குடிக்கிறேன்": "am taking",
    "வேண்டும்": "need", "முடியலை": "cannot", "முடியவில்லை": "cannot",
    "ரொம்ப": "very", "கொஞ்சம்": "slightly", "அதிகமாக": "more",
    "இல்லை": "no", "ஆம்": "yes", "ஆமாம்": "yes",
    "மற்றும்": "and", "ஆனால்": "but", "பிறகு": "then",
}

# Built once, longest surface form first so "தலை வலி" wins over "வலி".
_TABLE: List[Tuple[str, str]] = sorted(
    {
        **NUMBERS,
        **TIME_UNITS,
        **SYMPTOMS,
        **CONDITIONS,
        **BODY_PARTS,
        **PRONOUNS,
        **CARE_WORDS,
        **VERBS_AND_GLUE,
    }.items(),
    key=lambda item: -len(item[0]),
)

# Phrases that carry a whole clinical meaning, matched before word-by-word work.
SENTENCE_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (
        re.compile(
            r"எனக்கு\s+(?P<count>[஀-௿]+|\d+)\s*(?P<unit>நாளா(?:க|ச்)?|நாட்களாக|வாரமா(?:க)?|மாதமா(?:க)?)\s+"
            r"(?P<what>[஀-௿\s]+?)\s*(?P<verb>வலிக்கு(?:து|ிறது)|இருக்கு(?:து|ிறது)?)\.?$"
        ),
        "I have had {what} for {count} {unit}.",
    ),
    (
        re.compile(
            r"எனக்கு\s+(?P<count>[஀-௿]+|\d+)\s*(?P<unit>நாளா(?:க|ச்)?|நாட்களாக|வாரமா(?:க)?|மாதமா(?:க)?)\s+"
            r"(?P<what>[஀-௿\s]+?)(?P<verb>)\s*$"
        ),
        "I have had {what} for {count} {unit}.",
    ),
]


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------
def detect_language(text: str) -> str:
    """Return 'ta', 'en' or 'ta-en' for a piece of patient-entered text."""
    if not text:
        return LANGUAGE_ENGLISH
    tamil = len(TAMIL_RANGE.findall(text))
    latin = len(LATIN_RANGE.findall(text))
    if tamil == 0:
        return LANGUAGE_ENGLISH
    if latin == 0:
        return LANGUAGE_TAMIL
    # Mixed speech: enough of both scripts that neither is incidental.
    return LANGUAGE_MIXED if latin >= 3 else LANGUAGE_TAMIL


def _lookup(token: str) -> str:
    """Translate one Tamil token, tolerating common case endings."""
    cleaned = token.strip(" .,;:!?()‘’“”")
    if not cleaned or not TAMIL_RANGE.search(cleaned):
        return token
    for source, target in _TABLE:
        if cleaned == source:
            return target
    # Suffix-tolerant match: Tamil agglutinates, so try dropping case endings.
    for source, target in _TABLE:
        if len(source) >= 4 and cleaned.startswith(source):
            return target
    return cleaned


LATIN_WITH_TAMIL_SUFFIX = re.compile(
    r"^([A-Za-z0-9.']+(?:[-'][A-Za-z0-9.']+)*)[-\u2010-\u2015]?[\u0B80-\u0BFF]+([.,;:!?]?)$"
)


def _strip_tamil_suffix(token: str) -> str:
    """"Kumar-ஐ" and "bp-யை" carry a Tamil case ending on an English word."""
    match = LATIN_WITH_TAMIL_SUFFIX.match(token)
    return f"{match.group(1)}{match.group(2)}" if match else token


def _compose_pain(words: List[str]) -> List[str]:
    """A body part followed by a pain verb reads as "<part> pain"."""
    out: List[str] = []
    index = 0
    while index < len(words):
        token = words[index].strip(" .,;:!?")
        part = BODY_PARTS.get(token)
        following = words[index + 1].strip(" .,;:!?") if index + 1 < len(words) else ""
        if part and following in PAIN_VERBS:
            out.append("a headache" if part == "head" else f"{part} pain")
            index += 2
            continue
        out.append(words[index])
        index += 1
    return out


def _translate_fragment(fragment: str) -> str:
    tokens = _compose_pain(fragment.split())
    out = []
    for token in tokens:
        if not TAMIL_RANGE.search(token):
            out.append(token)
            continue
        rendered = _lookup(token)
        if rendered:
            out.append(rendered)
    return " ".join(out).strip()


SINGULARS = {"days": "day", "weeks": "week", "months": "month", "years": "year",
             "hours": "hour"}


def _agree(count: str, unit: str) -> str:
    """"one weeks" is wrong in either language."""
    if count in {"one", "1", "a"} and unit in SINGULARS:
        return SINGULARS[unit]
    return unit


def _tidy(sentence: str) -> str:
    sentence = re.sub(r"\s+", " ", sentence).strip()
    sentence = re.sub(r"\s+([.,;:!?])", r"\1", sentence)
    if not sentence:
        return sentence
    sentence = sentence[0].upper() + sentence[1:]
    if sentence[-1] not in ".!?":
        sentence += "."
    return sentence


def to_english(text: str) -> str:
    """Best-effort plain-English reading of Tamil or mixed text."""
    if not text:
        return ""
    source = re.sub(r"\s+", " ", text).strip()

    for pattern, template in SENTENCE_PATTERNS:
        match = pattern.search(source)
        if not match:
            continue
        parts = match.groupdict()
        what_fragment = parts.get("what", "")
        verb = (parts.get("verb") or "").strip()
        if verb in PAIN_VERBS:
            what_fragment = f"{what_fragment} {verb}"
        rendered = template.format(
            what=_translate_fragment(what_fragment) or "symptoms",
            count=_lookup(parts.get("count", "")),
            unit=_agree(_lookup(parts.get("count", "")), _lookup(parts.get("unit", ""))),
        )
        remainder = (source[: match.start()] + " " + source[match.end():]).strip()
        if remainder:
            rendered = f"{_tidy(_translate_fragment(remainder))} {rendered}"
        return _tidy(rendered)

    rendered = []
    for token in _compose_pain(source.split()):
        stripped = _strip_tamil_suffix(token)
        if stripped != token:
            rendered.append(stripped)
            continue
        if TAMIL_RANGE.search(token):
            trailing = "," if token.rstrip().endswith(",") else ""
            word = _lookup(token)
            if word:
                rendered.append(word + trailing)
        else:
            rendered.append(token)
    return _tidy(" ".join(rendered))


def recognised_terms(text: str) -> List[Dict[str, str]]:
    """The Tamil terms this module actually recognised, for transparency."""
    found = []
    seen = set()
    for source, target in _TABLE:
        if source in text and target and source not in seen:
            seen.add(source)
            found.append({"tamil": source, "english": target})
    return found[:12]


def normalise(text: str) -> Dict[str, Any]:
    """
    Prepare patient-entered text for extraction.

    Returns the language detected, the untouched original, and — for Tamil or
    mixed input — an assisted English reading used ONLY to help extraction and
    to let an English-reading clinician follow the entry. The original wording
    is always what is stored as the patient's words.
    """
    original = (text or "").strip()
    language = detect_language(original)

    if language == LANGUAGE_ENGLISH:
        return {
            "language": language,
            "original": original,
            "text_for_extraction": original,
            "assisted_reading": None,
            "is_assisted": False,
            "terms": [],
        }

    reading = to_english(original)
    return {
        "language": language,
        "original": original,
        "text_for_extraction": f"{reading} {original}".strip(),
        "assisted_reading": reading,
        "is_assisted": True,
        "terms": recognised_terms(original),
        "note": (
            "Assisted reading of the patient's own words. Reported by the "
            "patient, not a diagnosis."
        ),
    }
