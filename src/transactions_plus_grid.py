import datetime as dt
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd

from src import tags, transaction_validation

NONE_SENTINEL = "(none)"


def normalize_optional(value: Optional[str], lower: bool = True) -> Optional[str]:
    if value is None:
        return None
    if pd.isna(value):
        return None
    cleaned = str(value).strip()
    if not cleaned or cleaned == NONE_SENTINEL:
        return None
    return cleaned.lower() if lower else cleaned


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


def parse_tags_cell(value: object) -> Tuple[List[str], Optional[str]]:
    if value is None:
        return [], None
    if isinstance(value, str):
        try:
            return tags.parse_tags(value), None
        except ValueError as exc:
            return [], str(exc)
    if isinstance(value, (list, tuple, set)):
        normalized: List[str] = []
        seen = set()
        for item in value:
            if item is None:
                continue
            cleaned = str(item).strip()
            if not cleaned:
                continue
            try:
                tag_value = tags.normalize_tag(cleaned)
            except ValueError as exc:
                return [], str(exc)
            if tag_value in seen:
                continue
            seen.add(tag_value)
            normalized.append(tag_value)
        return normalized, None
    if pd.isna(value):
        return [], None
    return [], "Tags must be a list"


def build_payload(
    row: pd.Series,
    subcategory_map: Dict[str, List[str]],
) -> Tuple[Optional[Dict[str, object]], List[str]]:
    errors: List[str] = []

    date_payment, err = coerce_date(row.get("date_payment"), "Payment date")
    if err:
        errors.append(err)
    date_application, err = coerce_date(row.get("date_application"), "Application date")
    if err:
        errors.append(err)

    tag_list, err = parse_tags_cell(row.get("tags"))
    if err:
        errors.append(err)

    amount_raw = row.get("amount_cents")
    amount_text = "" if amount_raw is None else str(amount_raw)
    category_value = normalize_optional(row.get("category"))
    payer_value = normalize_optional(row.get("payer"))
    payee_value = normalize_optional(row.get("payee"))
    payment_type_value = normalize_optional(row.get("payment_type"))
    subcategory_value = normalize_optional(row.get("subcategory"))
    notes_value = normalize_optional(row.get("notes"), lower=False)

    payload, form_errors = transaction_validation.validate_transaction_form(
        amount_raw=amount_text,
        category=category_value,
        payer=payer_value,
        payee=payee_value,
        payment_type=payment_type_value,
        subcategory=subcategory_value,
        notes=notes_value,
        selected_tags=tag_list,
        new_tag=None,
    )
    if form_errors:
        errors.extend(form_errors)

    if payload:
        subcategory = payload["subcategory"]
        category = payload["category"]
        if subcategory and category:
            known_categories = subcategory_map.get(subcategory)
            if known_categories and category not in known_categories:
                errors.append("Subcategory does not match the selected category")

    if errors:
        return None, errors
    if payload is None:
        return None, errors

    payload = {
        "date_payment": date_payment,
        "date_application": date_application,
        "amount_cents": payload["amount_cents"],
        "payer": payload["payer"],
        "payee": payload["payee"],
        "payment_type": payload["payment_type"],
        "category": payload["category"],
        "subcategory": payload["subcategory"],
        "notes": payload["notes"],
        "tags": payload["tags"],
    }
    return payload, []
