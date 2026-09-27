"""Small shared helpers: dates, formatting, serialisation."""

from datetime import datetime, timedelta
from typing import Any, Optional

DATE_FORMATS = [
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d %b %Y",
    "%d %B %Y",
    "%b %d %Y",
    "%B %d %Y",
]


def parse_date(value: Any, default: Optional[datetime] = None) -> Optional[datetime]:
    if value is None or value == "":
        return default
    if isinstance(value, datetime):
        return value
    text = str(value).strip().replace(",", "").replace("Z", "")
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return default


def iso(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if isinstance(value, datetime) else None


def human_date(value: Optional[datetime]) -> str:
    if not isinstance(value, datetime):
        return "Unknown date"
    return value.strftime("%d %b %Y")


def human_datetime(value: Optional[datetime]) -> str:
    if not isinstance(value, datetime):
        return "Unknown time"
    return value.strftime("%d %b %Y, %H:%M")


def days_ago(value: Optional[datetime]) -> Optional[int]:
    if not isinstance(value, datetime):
        return None
    return max(0, (datetime.utcnow() - value).days)


def relative_day(text: str, reference: Optional[datetime] = None) -> Optional[datetime]:
    """Resolve loose phrases like 'yesterday' or 'last Monday' from free text."""
    reference = reference or datetime.utcnow()
    lowered = (text or "").lower()
    if "day before yesterday" in lowered:
        return reference - timedelta(days=2)
    if "yesterday" in lowered:
        return reference - timedelta(days=1)
    if "today" in lowered or "this morning" in lowered or "tonight" in lowered:
        return reference
    if "last week" in lowered:
        return reference - timedelta(days=7)
    weekdays = [
        "monday", "tuesday", "wednesday", "thursday",
        "friday", "saturday", "sunday",
    ]
    for index, day in enumerate(weekdays):
        if day in lowered:
            delta = (reference.weekday() - index) % 7
            delta = delta or 7
            return reference - timedelta(days=delta)
    return None


def percent(value: Optional[float]) -> str:
    if value is None:
        return "—"
    return f"{round(float(value) * 100)}%"


def confidence_band(value: Optional[float]) -> str:
    from config import HIGH_CONFIDENCE_THRESHOLD, MEDIUM_CONFIDENCE_THRESHOLD

    if value is None:
        return "UNKNOWN"
    if value >= HIGH_CONFIDENCE_THRESHOLD:
        return "HIGH"
    if value >= MEDIUM_CONFIDENCE_THRESHOLD:
        return "MEDIUM"
    return "LOW"


def truncate(text: str, limit: int = 220) -> str:
    text = (text or "").strip().replace("\n", " ")
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"
