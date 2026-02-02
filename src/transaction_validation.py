from typing import Iterable, List, Optional, Tuple, Dict

from src import amounts, tags


def _normalize_optional(value: Optional[str], lower: bool = True) -> Optional[str]:
    if value is None:
        return None
    cleaned = str(value).strip()
    if not cleaned:
        return None
    return cleaned.lower() if lower else cleaned


def _normalize_tags(
    tag_names: Iterable[str], errors: List[str]
) -> List[str]:
    normalized: List[str] = []
    seen = set()
    for name in tag_names:
        if name is None:
            continue
        cleaned = str(name).strip()
        if not cleaned:
            continue
        try:
            tag_value = tags.normalize_tag(cleaned)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if tag_value in seen:
            continue
        seen.add(tag_value)
        normalized.append(tag_value)
    return normalized


def validate_transaction_form(
    *,
    amount_raw: str,
    category: Optional[str],
    payer: Optional[str],
    payee: Optional[str],
    payment_type: Optional[str],
    subcategory: Optional[str],
    notes: Optional[str],
    selected_tags: Iterable[str],
    new_tag: Optional[str],
) -> Tuple[Optional[Dict[str, object]], List[str]]:
    errors: List[str] = []

    try:
        amount_cents = amounts.parse_amount_to_cents(amount_raw)
    except ValueError as exc:
        amount_cents = 0
        errors.append(str(exc))

    category_value = _normalize_optional(category)
    if not category_value:
        errors.append("Category is required")

    payer_value = _normalize_optional(payer)
    payee_value = _normalize_optional(payee)
    payment_type_value = _normalize_optional(payment_type)
    subcategory_value = _normalize_optional(subcategory)
    notes_value = _normalize_optional(notes, lower=False)

    if not payer_value and not payee_value:
        errors.append("Payer or payee is required")
    if payer_value and payee_value and payer_value == payee_value:
        errors.append("Payer and payee must be different")

    normalized_tags = _normalize_tags(selected_tags, errors)
    new_tag_value = (new_tag or "").strip()
    if new_tag_value:
        try:
            normalized = tags.normalize_tag(new_tag_value)
        except ValueError as exc:
            errors.append(str(exc))
        else:
            if normalized not in normalized_tags:
                normalized_tags.append(normalized)

    if errors:
        return None, errors

    payload = {
        "amount_cents": amount_cents,
        "payer": payer_value,
        "payee": payee_value,
        "payment_type": payment_type_value,
        "category": category_value,
        "subcategory": subcategory_value,
        "notes": notes_value,
        "tags": normalized_tags,
    }
    return payload, []
