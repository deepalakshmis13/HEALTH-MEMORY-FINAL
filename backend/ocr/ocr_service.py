"""
OCRService — the modular document-understanding entry point (§9–§11).

    OCRService
     ├── PrintedOCR
     └── HandwritingOCR

`process()` returns the raw text, the per-field extraction with individual
confidence scores, and the routing decision for each field. It never decides
what enters health memory — that is the ingestion service's job, using
`ocr.confidence`.
"""

import hashlib
import random
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from ocr import confidence as conf
from ocr.handwriting import (
    HandwritingOCR,
    _degrade,
    detect_handwriting,
    normalise_ground_truth,
)
from services.extraction_service import extract_entities


# ---------------------------------------------------------------------------
class PrintedOCR:
    """Recognition engine for printed/digital documents."""

    name = "PrintedOCR"

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

    def recognise(self, path: Path, ground_truth: Any = None) -> Dict[str, Any]:
        suffix = path.suffix.lower()

        if suffix == ".txt":
            text = _read_text_file(path)
            if text:
                return {
                    "text": text,
                    "confidence": 0.99,
                    "engine": f"{self.name} (native text)",
                    "mode": "native",
                }

        if suffix == ".pdf":
            text = _read_pdf(path)
            if text and len(text.strip()) > 40:
                return {
                    "text": text,
                    "confidence": 0.97,
                    "engine": f"{self.name} (embedded PDF text)",
                    "mode": "native",
                }

        if self.backend == "tesseract" and suffix in {
            ".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"
        }:
            result = self._tesseract(path)
            if result:
                return result

        return self._simulate(path, ground_truth)

    def _tesseract(self, path: Path) -> Optional[Dict[str, Any]]:
        try:
            import pytesseract
            from PIL import Image

            with Image.open(path) as image:
                data = pytesseract.image_to_data(
                    image.convert("L"), output_type=pytesseract.Output.DICT
                )
            words, scores = [], []
            for text, score in zip(data["text"], data["conf"]):
                if not text.strip():
                    continue
                words.append(text)
                try:
                    value = float(score)
                except (TypeError, ValueError):
                    value = -1.0
                if value >= 0:
                    scores.append(value / 100.0)
            if not words:
                return None
            mean = sum(scores) / len(scores) if scores else 0.85
            return {
                "text": " ".join(words),
                "confidence": round(max(0.35, min(0.99, mean)), 4),
                "engine": f"{self.name} (tesseract)",
                "mode": "tesseract",
            }
        except Exception:
            return None

    def _simulate(self, path: Path, ground_truth: Any) -> Dict[str, Any]:
        seed = int(hashlib.sha256(path.name.encode()).hexdigest()[:12], 16)
        rng = random.Random(seed)
        text, legibility = normalise_ground_truth(ground_truth)
        base = text or _fallback_printed_report(rng)
        if legibility is None:
            legibility = 0.88 + (rng.random() * 0.10)
        drop_rate = max(0.0, (1 - legibility) * 0.06)
        confuse_rate = max(0.0, (1 - legibility) * 0.18)
        noisy, _ = _degrade(base, rng, drop_rate=drop_rate, confuse_rate=confuse_rate)
        confidence = round(
            max(0.30, min(0.98, legibility + rng.uniform(-0.01, 0.01))), 4
        )
        return {
            "text": noisy,
            "confidence": confidence,
            "engine": f"{self.name} (demo mode)",
            "mode": "simulated",
            "clean_text": base,
        }


# ---------------------------------------------------------------------------
class OCRService:
    """Routes a document to the right engine and produces scored fields."""

    def __init__(self):
        self.printed = PrintedOCR()
        self.handwriting = HandwritingOCR()

    @property
    def engines(self) -> Dict[str, str]:
        return {
            "PrintedOCR": self.printed.backend,
            "HandwritingOCR": self.handwriting.backend,
        }

    # ------------------------------------------------------------------
    def process(
        self,
        path: Path,
        filename: Optional[str] = None,
        declared_handwritten: Optional[bool] = None,
        ground_truth: Optional[str] = None,
    ) -> Dict[str, Any]:
        path = Path(path)
        filename = filename or path.name
        ground_truth = ground_truth or _load_ground_truth(path)

        is_handwritten, reason = detect_handwriting(
            path, filename, declared_handwritten
        )
        engine = self.handwriting if is_handwritten else self.printed
        raw = engine.recognise(path, ground_truth)

        text = raw.get("text", "")
        base_confidence = raw.get("confidence", 0.5)
        entities = extract_entities(text, base_confidence=base_confidence)
        fields = build_fields(entities, base_confidence, text)

        summary = conf.summarise(fields)
        return {
            "handwriting_detected": is_handwritten,
            "handwriting_reason": reason,
            "engine": raw.get("engine", engine.name),
            "engine_mode": raw.get("mode", "simulated"),
            "document_type_label": (
                "Handwritten Doctor Report" if is_handwritten else "Printed Document"
            ),
            "raw_text": text,
            "clean_reference_text": raw.get("clean_text"),
            "recognition_confidence": round(base_confidence, 4),
            "overall_confidence": summary["overall_confidence"],
            "fields": fields,
            "entities": entities,
            "summary": summary,
            "ocr_status": "PROCESSED" if text.strip() else "FAILED",
        }


# ---------------------------------------------------------------------------
def build_fields(
    entities: Dict[str, Any], base_confidence: float, text: str
) -> List[Dict[str, Any]]:
    """Turn extracted entities into individually-scored, routable fields."""
    fields: List[Dict[str, Any]] = []

    for med in entities.get("medications", []):
        scores = med.get("confidence", {})
        raw_reading = med.get("raw") or med["name"]
        name_field = conf.build_field(
            "medication_name", med["name"],
            scores.get("name") or base_confidence,
            (
                f"OCR read: \"{raw_reading}\""
                + ("" if med.get("exact_match") else
                   f" (approximate lexicon match, similarity "
                   f"{med.get('match_ratio')})")
                + f" — {med.get('context', '')}"
            ),
        )
        name_field["ocr_reading"] = raw_reading
        name_field["exact_match"] = med.get("exact_match", True)
        fields.append(name_field)
        if med.get("dose"):
            fields.append(
                conf.build_field(
                    "medication_dose", med["dose"],
                    scores.get("dose") or base_confidence - 0.02,
                    med.get("context", ""),
                )
            )
        if med.get("frequency"):
            fields.append(
                conf.build_field(
                    "medication_frequency", med["frequency"],
                    scores.get("frequency") or base_confidence - 0.08,
                    med.get("context", ""),
                )
            )
        if med.get("instruction"):
            fields.append(
                conf.build_field(
                    "prescription_instruction", med["instruction"],
                    base_confidence - 0.05, med.get("context", ""),
                )
            )
        if med.get("is_change"):
            fields.append(
                conf.build_field(
                    "medication_change",
                    f"{med['name']} — change indicated in document",
                    base_confidence - 0.06, med.get("context", ""),
                )
            )

    for allergy in entities.get("allergies", []):
        fields.append(
            conf.build_field(
                "allergy", allergy["substance"],
                allergy.get("confidence") or base_confidence - 0.05,
            )
        )

    doctor = entities.get("doctor")
    if doctor:
        fields.append(
            conf.build_field("doctor_name", doctor["name"], base_confidence + 0.03)
        )
        if doctor.get("specialty"):
            fields.append(
                conf.build_field(
                    "doctor_specialty", doctor["specialty"], base_confidence
                )
            )
        if doctor.get("hospital"):
            fields.append(
                conf.build_field("hospital", doctor["hospital"], base_confidence)
            )

    if entities.get("event_date"):
        fields.append(
            conf.build_field(
                "consultation_date",
                entities["event_date"].strftime("%d %b %Y"),
                base_confidence - 0.02,
            )
        )

    for diagnosis in entities.get("diagnoses", []):
        fields.append(
            conf.build_field("diagnosis", diagnosis.title(), base_confidence - 0.03)
        )
    for symptom in entities.get("symptoms", []):
        fields.append(
            conf.build_field("symptom", symptom.title(), base_confidence - 0.04)
        )
    for lab in entities.get("lab_results", []):
        value = f"{lab['value']} {lab['unit']}" if lab.get("value") else "recorded"
        fields.append(
            conf.build_field(
                "lab_result", f"{lab['test_name']}: {value}",
                lab.get("confidence") or base_confidence - 0.03,
            )
        )
    for key, value in (entities.get("vitals") or {}).items():
        fields.append(
            conf.build_field("vitals", f"{key.replace('_', ' ').title()}: {value}",
                             base_confidence - 0.02)
        )

    critical = re.search(
        r"((?:monitor|watch for|avoid|do not|must not|urgent|immediately|"
        r"escalate|discontinue)[^.\n]{5,110})",
        text, re.I,
    )
    if critical:
        fields.append(
            conf.build_field(
                "critical_instruction", critical.group(1).strip(),
                base_confidence - 0.07,
            )
        )

    if not fields:
        fields.append(
            conf.build_field("document_text", (text or "")[:160], base_confidence)
        )
    return fields


# ---------------------------------------------------------------------------
def _read_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _read_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception:
        return ""


def _load_ground_truth(path: Path) -> Optional[Dict[str, Any]]:
    """
    Demo-mode support: a seeded document may ship a sidecar
    `<file>.groundtruth.txt` holding the text that was rendered into the image.
    The simulated engines degrade *that* text, so the demo behaves like a real
    recogniser reading the real page.

    An optional first line `#legibility: 0.54` pins how legible the page is, so
    a scripted demo can guarantee a specific confidence band. Real uploads have
    no sidecar and get a deterministic legibility derived from the file itself.
    """
    sidecar = path.with_suffix(path.suffix + ".groundtruth.txt")
    if not sidecar.exists():
        return None
    try:
        raw = sidecar.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None

    legibility = None
    lines = raw.splitlines()
    if lines and lines[0].lower().startswith("#legibility:"):
        try:
            legibility = float(lines[0].split(":", 1)[1].strip())
        except (ValueError, IndexError):
            legibility = None
        lines = lines[1:]
    return {"text": "\n".join(lines).strip(), "legibility": legibility}


def _fallback_printed_report(rng: random.Random) -> str:
    from datetime import datetime

    templates = [
        "APOLLO DIAGNOSTICS, Chennai\nLABORATORY REPORT\n"
        "Date: {date}\nReferred by: Dr. Meera Raghavan, General Medicine\n"
        "HbA1c : 7.4 %  (Ref 4.0-5.6)\nFasting Blood Sugar : 132 mg/dL\n"
        "Serum Creatinine : 1.1 mg/dL\nHaemoglobin : 11.8 g/dL\n"
        "Impression: Glycaemic control suboptimal. Clinical correlation advised.",
        "SUNRISE HOSPITAL\nOUTPATIENT CONSULTATION RECORD\nDate: {date}\n"
        "Consultant: Dr. Arun Kumar, Cardiology\n"
        "Complaint: dizziness on standing for 5 days.\n"
        "BP 148/92 mmHg. Advised to continue Amlodipine 5 mg once daily.\n"
        "Monitor blood pressure daily and review after 2 weeks.",
    ]
    return rng.choice(templates).format(date=datetime.utcnow().strftime("%d/%m/%Y"))


ocr_service = OCRService()
