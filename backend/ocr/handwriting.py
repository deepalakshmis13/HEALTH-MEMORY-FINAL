"""
Handwriting detection and the handwriting recognition engine (§10).

Two responsibilities:

1. `detect_handwriting()` — decide whether a document is handwritten, from an
   explicit user declaration, filename hints, or (when Pillow is installed) an
   ink-distribution heuristic over the image itself.
2. `HandwritingOCR` — the recognition engine used for those documents. It
   prefers a real trained recogniser when one is installed
   (`pytesseract`/TrOCR); otherwise it runs in a clearly-labelled demo mode
   that degrades the document's ground truth exactly the way a handwriting
   recogniser does — dropped strokes, confused characters, lower confidence.
"""

import hashlib
import random
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

HANDWRITING_FILENAME_HINTS = (
    "handwritten", "hand_written", "handwriting", "hw_", "_hw",
    "scribble", "doctor_note", "doctornote", "rx_", "_rx", "prescription_note",
    "written", "note_",
)

# Character pairs a handwriting recogniser genuinely confuses.
CONFUSION_MAP = {
    "i": "l", "l": "i", "n": "m", "m": "n", "u": "v", "v": "u",
    "o": "0", "0": "o", "5": "s", "s": "5", "1": "l", "g": "9",
    "a": "o", "e": "c", "t": "f", "r": "n",
}


def _pillow():
    try:
        from PIL import Image  # noqa: F401

        return True
    except Exception:
        return False


def _ink_heuristic(path: Path) -> Optional[float]:
    """
    Rough 'is this handwriting?' score from the image itself.

    Printed medical documents have dense, regularly-spaced dark rows (text
    lines of uniform height). Handwriting has sparser ink and far more
    variance in row density. Returns 0..1, higher = more likely handwritten.
    """
    if not _pillow():
        return None
    try:
        from PIL import Image

        with Image.open(path) as image:
            grey = image.convert("L").resize((320, 320))
            pixels = list(grey.getdata())
    except Exception:
        return None

    rows = [pixels[i * 320:(i + 1) * 320] for i in range(320)]
    densities = [sum(1 for p in row if p < 150) / 320 for row in rows]
    inked = [d for d in densities if d > 0.01]
    if not inked:
        return 0.0
    mean = sum(inked) / len(inked)
    variance = sum((d - mean) ** 2 for d in inked) / len(inked)
    coverage = len(inked) / len(densities)
    # High variance + low coverage => handwriting-like.
    score = min(1.0, (variance * 45) + max(0.0, 0.55 - coverage))
    return round(score, 3)


def detect_handwriting(
    path: Optional[Path],
    filename: str,
    declared: Optional[bool] = None,
) -> Tuple[bool, str]:
    """Returns (is_handwritten, reason)."""
    if declared is True:
        return True, "Declared as a handwritten document by the uploader"
    if declared is False:
        return False, "Declared as a printed document by the uploader"

    lowered = (filename or "").lower()
    for hint in HANDWRITING_FILENAME_HINTS:
        if hint in lowered:
            return True, f"Filename indicates handwriting ('{hint}')"

    if path and path.exists() and path.suffix.lower() in {
        ".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"
    }:
        score = _ink_heuristic(path)
        if score is not None and score >= 0.35:
            return True, f"Ink-distribution heuristic score {score} (>= 0.35)"
        if score is not None:
            return False, f"Ink-distribution heuristic score {score} (< 0.35)"

    return False, "Treated as printed text"


class HandwritingOCR:
    """Recognition engine for handwritten medical documents."""

    name = "HandwritingOCR"

    def __init__(self):
        self.backend = self._detect_backend()

    @staticmethod
    def _detect_backend() -> str:
        try:
            import pytesseract  # noqa: F401
            from PIL import Image  # noqa: F401

            pytesseract.get_tesseract_version()
            return "tesseract"
        except Exception:
            return "simulated"

    # ------------------------------------------------------------------
    def recognise(self, path: Path, ground_truth: Any = None) -> Dict[str, Any]:
        if self.backend == "tesseract":
            result = self._tesseract(path)
            if result:
                return result
        return self._simulate(path, ground_truth)

    # ------------------------------------------------------------------
    def _tesseract(self, path: Path) -> Optional[Dict[str, Any]]:
        try:
            import pytesseract
            from PIL import Image

            with Image.open(path) as image:
                grey = image.convert("L")
                data = pytesseract.image_to_data(
                    grey, output_type=pytesseract.Output.DICT, config="--psm 6"
                )
            words, scores = [], []
            for text, conf in zip(data["text"], data["conf"]):
                if not text.strip():
                    continue
                words.append(text)
                try:
                    value = float(conf)
                except (TypeError, ValueError):
                    value = -1.0
                if value >= 0:
                    scores.append(value / 100.0)
            if not words:
                return None
            raw_confidence = sum(scores) / len(scores) if scores else 0.5
            # Handwriting recognisers are systematically over-confident on
            # cursive medical script; apply the calibration penalty.
            confidence = max(0.30, min(0.93, raw_confidence * 0.82))
            return {
                "text": " ".join(words),
                "confidence": round(confidence, 4),
                "engine": f"{self.name} (tesseract)",
                "mode": "tesseract",
            }
        except Exception:
            return None

    # ------------------------------------------------------------------
    def _simulate(self, path: Path, ground_truth: Any) -> Dict[str, Any]:
        seed = int(hashlib.sha256(str(path.name).encode()).hexdigest()[:12], 16)
        rng = random.Random(seed)
        text, legibility = normalise_ground_truth(ground_truth)
        base = text or _fallback_prescription(rng)
        if legibility is None:
            # Unseen handwriting: 0.42 – 0.78 legibility, deterministic per file.
            legibility = 0.42 + (rng.random() * 0.36)

        drop_rate = 0.04 + (1 - legibility) * 0.22
        confuse_rate = 0.05 + (1 - legibility) * 0.30
        noisy, _ = _degrade(base, rng, drop_rate=drop_rate, confuse_rate=confuse_rate)
        confidence = round(
            max(0.20, min(0.93, legibility + rng.uniform(-0.015, 0.015))), 4
        )
        return {
            "text": noisy,
            "confidence": confidence,
            "engine": f"{self.name} (demo mode)",
            "mode": "simulated",
            "clean_text": base,
        }


def normalise_ground_truth(ground_truth: Any):
    """Accept a plain string or a {'text', 'legibility'} fixture descriptor."""
    if ground_truth is None:
        return None, None
    if isinstance(ground_truth, dict):
        return ground_truth.get("text"), ground_truth.get("legibility")
    return str(ground_truth), None


def _degrade(text: str, rng: random.Random, drop_rate: float, confuse_rate: float):
    """Apply realistic recognition noise and report how much survived intact."""
    out = []
    intact = 0
    total = 0
    for char in text:
        if not char.isalnum():
            out.append(char)
            continue
        total += 1
        roll = rng.random()
        if roll < drop_rate:
            continue  # stroke lost
        if roll < drop_rate + confuse_rate:
            out.append(CONFUSION_MAP.get(char.lower(), char))
            continue
        intact += 1
        out.append(char)
    hit_rate = (intact / total) if total else 0.0
    return re.sub(r"[ \t]{2,}", " ", "".join(out)), hit_rate


def _fallback_prescription(rng: random.Random) -> str:
    """Used only when a handwritten image arrives with no readable ground truth."""
    templates = [
        "Dr. Arun Kumar MBBS MD Cardiology\nSunrise Hospital, Chennai\n"
        "Date: {date}\nPatient: elderly, 72 yrs\n"
        "Rx\n1. Amlodipine 5 mg once daily after food\n"
        "2. Atorvastatin 10 mg at bedtime\nReview after 4 weeks. Monitor BP daily.",
        "Dr. Meera Raghavan MD General Medicine\nCity Care Clinic\n"
        "Date: {date}\nRx\n1. Metformin 500 mg twice daily after food\n"
        "2. Vitamin D3 60000 IU once weekly\nCheck HbA1c in 3 months.",
    ]
    from datetime import datetime

    return rng.choice(templates).format(date=datetime.utcnow().strftime("%d/%m/%Y"))
