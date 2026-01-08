import csv
import datetime as dt
import io
import os
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

from src import amounts, tags

REQUIRED_COLUMNS = {"date_payment", "date_application", "amount", "category"}
OPTIONAL_COLUMNS = {"payer", "payee", "payment_type", "subcategory", "notes", "tags"}
EXPORT_COLUMNS = [
    "date_payment",
    "date_application",
    "amount",
    "payer",
    "payee",
    "payment_type",
    "category",
    "subcategory",
    "notes",
    "tags",
]


@dataclass(frozen=True)
class ParsedRow:
    date_payment: str
    date_application: str
    amount_cents: int
    payer: Optional[str]
    payee: Optional[str]
    payment_type: Optional[str]
    category: str
    subcategory: Optional[str]
    notes: Optional[str]
    tags: List[str]


@dataclass(frozen=True)
class ValidationError:
    row: int
    message: str


def decode_csv_bytes(data: bytes) -> str:
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("utf-8")


def read_csv_rows(text: str) -> Tuple[List[str], List[Dict[str, Optional[str]]]]:
    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    headers = reader.fieldnames or []
    rows = [row for row in reader]
    return headers, rows


def preview_rows(rows: Sequence[Dict[str, Optional[str]]], limit: int = 5) -> List[Dict[str, str]]:
    preview: List[Dict[str, str]] = []
    for row in rows[:limit]:
        cleaned = {}
        for key, value in row.items():
            if value is None:
                cleaned[key] = ""
            else:
                cleaned[key] = value.strip()
        preview.append(cleaned)
    return preview


def validate_rows(rows: Sequence[Dict[str, Optional[str]]]) -> Tuple[List[ParsedRow], List[ValidationError]]:
    parsed: List[ParsedRow] = []
    errors: List[ValidationError] = []

    for index, row in enumerate(rows, start=1):
        row_errors: List[str] = []
        try:
            date_payment = _parse_date(row.get("date_payment"), "date_payment")
        except ValueError as exc:
            row_errors.append(str(exc))
            date_payment = ""

        try:
            date_application = _parse_date(row.get("date_application"), "date_application")
        except ValueError as exc:
            row_errors.append(str(exc))
            date_application = ""

        try:
            amount_cents = amounts.parse_amount_to_cents(row.get("amount") or "")
        except ValueError as exc:
            row_errors.append(str(exc))
            amount_cents = 0

        try:
            category_value = _normalize_required(row.get("category"), lower=True)
        except ValueError as exc:
            row_errors.append(str(exc))
            category_value = ""

        payer_value = _normalize_optional(row.get("payer"))
        payee_value = _normalize_optional(row.get("payee"))
        payment_type_value = _normalize_optional(row.get("payment_type"), lower=True)
        subcategory_value = _normalize_optional(row.get("subcategory"), lower=True)
        notes_value = _normalize_optional(row.get("notes"))
        tag_values = tags.parse_tags(row.get("tags") or "")

        if payer_value and payee_value and payer_value == payee_value:
            row_errors.append("Payer and payee must be different")

        if row_errors:
            errors.append(ValidationError(row=index, message="; ".join(row_errors)))
            continue

        parsed.append(
            ParsedRow(
                date_payment=date_payment,
                date_application=date_application,
                amount_cents=amount_cents,
                payer=payer_value,
                payee=payee_value,
                payment_type=payment_type_value,
                category=category_value,
                subcategory=subcategory_value,
                notes=notes_value,
                tags=tag_values,
            )
        )

    return parsed, errors


def insert_transactions(conn, rows: Sequence[ParsedRow]) -> None:
    for row in rows:
        cursor = conn.execute(
            """
            INSERT INTO transactions (
                date_payment,
                date_application,
                amount_cents,
                payer,
                payee,
                payment_type,
                category,
                subcategory,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.date_payment,
                row.date_application,
                row.amount_cents,
                row.payer,
                row.payee,
                row.payment_type,
                row.category,
                row.subcategory,
                row.notes,
            ),
        )
        transaction_id = cursor.lastrowid
        if transaction_id is None:
            raise ValueError("Failed to insert transaction")
        if row.tags:
            tags.set_transaction_tags(conn, int(transaction_id), row.tags)


def build_export_rows(rows: Iterable[Union[Dict[str, object], object]]) -> List[Dict[str, str]]:
    export_rows: List[Dict[str, str]] = []
    for row in rows:
        date_payment = _row_value(row, "date_payment", "")
        date_application = _row_value(row, "date_application", "")
        amount_value = _row_value(row, "amount_cents", 0)
        payer_value = _row_value(row, "payer", "")
        payee_value = _row_value(row, "payee", "")
        payment_type_value = _row_value(row, "payment_type", "")
        category_value = _row_value(row, "category", "")
        subcategory_value = _row_value(row, "subcategory", "")
        notes_value = _row_value(row, "notes", "")
        tags_value = _row_value(row, "tags", "")
        export_rows.append(
            {
                "date_payment": str(date_payment),
                "date_application": str(date_application),
                "amount": amounts.format_cents(int(amount_value)),
                "payer": payer_value or "",
                "payee": payee_value or "",
                "payment_type": payment_type_value or "",
                "category": category_value or "",
                "subcategory": subcategory_value or "",
                "notes": notes_value or "",
                "tags": tags_value or "",
            }
        )
    return export_rows


def export_to_csv(rows: Iterable[Union[Dict[str, object], object]]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=EXPORT_COLUMNS, delimiter=";")
    writer.writeheader()
    for row in build_export_rows(rows):
        writer.writerow(row)
    return output.getvalue()


def _row_value(row: object, key: str, default: object) -> object:
    if isinstance(row, dict):
        return row.get(key, default)
    try:
        return row[key]
    except Exception:
        return default


def save_export_csv(contents: str, directory: str, filename: str) -> str:
    target_dir = os.path.expanduser(directory)
    full_path = os.path.join(target_dir, filename)
    os.makedirs(target_dir, exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as handle:
        handle.write(contents)
    return full_path


def default_export_filename(prefix: str = "finance_export") -> str:
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.csv"


def _normalize_optional(value: Optional[str], lower: bool = False) -> Optional[str]:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    return cleaned.lower() if lower else cleaned


def _normalize_required(value: Optional[str], lower: bool = False) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        raise ValueError("Missing required value")
    return cleaned.lower() if lower else cleaned


def _parse_date(value: Optional[str], field_label: str) -> str:
    cleaned = (value or "").strip()
    if len(cleaned) != 10:
        raise ValueError(f"Invalid {field_label} format")
    try:
        dt.date.fromisoformat(cleaned)
    except ValueError as exc:
        raise ValueError(f"Invalid {field_label} format") from exc
    return cleaned
