from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def parse_amount_to_cents(raw: str) -> int:
    if raw is None:
        raise ValueError("Amount is required")
    cleaned = raw.strip()
    if not cleaned:
        raise ValueError("Amount is required")
    cleaned = cleaned.replace(",", ".")
    try:
        amount = Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError("Invalid amount") from exc
    if amount < 0:
        raise ValueError("Amount must be non-negative")
    quantized = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    cents = int((quantized * 100).to_integral_value(rounding=ROUND_HALF_UP))
    return cents


def format_cents(cents: int) -> str:
    value = Decimal(cents) / Decimal(100)
    return f"{value:.2f}"
