import datetime as dt
from typing import Optional, Tuple

import pandas as pd


def parse_date_optional(value: Optional[str], field_label: str) -> Optional[str]:
    cleaned = (value or "").strip()
    if not cleaned:
        return None
    if len(cleaned) != 10:
        raise ValueError(f"Invalid {field_label} format")
    try:
        dt.date.fromisoformat(cleaned)
    except ValueError as exc:
        raise ValueError(f"Invalid {field_label} format") from exc
    return cleaned


def coerce_date(value: object, label: str) -> Tuple[Optional[str], Optional[str]]:
    if value is None:
        return None, f"{label} is required"
    if isinstance(value, dt.datetime):
        return value.date().isoformat(), None
    if isinstance(value, dt.date):
        return value.isoformat(), None
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat(), None
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None, f"{label} is required"
        try:
            dt.date.fromisoformat(cleaned)
        except ValueError:
            return None, f"{label} must be YYYY-MM-DD"
        return cleaned, None
    return None, f"{label} must be YYYY-MM-DD"
