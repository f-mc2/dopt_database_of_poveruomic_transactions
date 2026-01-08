import re
from decimal import Decimal, InvalidOperation


_AMOUNT_RE = re.compile(r"^\d+(\.\d{1,2})?$")


def parse_amount_to_cents(raw: str) -> int:
    if raw is None:
        raise ValueError("Amount is required")
    cleaned = raw.strip()
    if not cleaned:
        raise ValueError("Amount is required")
    if "," in cleaned:
        raise ValueError("Invalid amount format")
    if cleaned.startswith(("+", "-")):
        raise ValueError("Amount must be non-negative")
    if not _AMOUNT_RE.match(cleaned):
        raise ValueError("Invalid amount format")
    try:
        amount = Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError("Invalid amount") from exc
    if amount < 0:
        raise ValueError("Amount must be non-negative")
    cents = int((amount * 100).to_integral_value())
    return cents


def format_cents(cents: int) -> str:
    value = Decimal(cents) / Decimal(100)
    return f"{value:.2f}"
