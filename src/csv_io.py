import csv
import datetime as dt
import io
import os
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

from src import amounts, tags, transaction_validation

REQUIRED_COLUMNS = {"amount", "category"}
DATE_COLUMNS = {"date_payment", "date_application"}
PAYER_PAYEE_COLUMNS = {"payer", "payee"}
OPTIONAL_COLUMNS = {
    "payer",
    "payee",
    "payment_type",
    "subcategory",
    "notes",
    "tags",
    "date_payment",
    "date_application",
}
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
    reader = csv.reader(io.StringIO(text), delimiter=";")
    try:
        raw_headers = next(reader)
    except StopIteration:
        return [], []
    headers = [_normalize_header(header) for header in raw_headers]
    _validate_headers(headers)
    rows: List[Dict[str, Optional[str]]] = []
    for row in reader:
        row_map: Dict[str, Optional[str]] = {}
        for index, header in enumerate(headers):
            row_map[header] = row[index] if index < len(row) else None
        rows.append(row_map)
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
            date_payment = _parse_date_optional(row.get("date_payment"), "date_payment")
        except ValueError as exc:
            row_errors.append(str(exc))
            date_payment = None

        try:
            date_application = _parse_date_optional(row.get("date_application"), "date_application")
        except ValueError as exc:
            row_errors.append(str(exc))
            date_application = None

        try:
            tag_values = tags.parse_tags(row.get("tags") or "")
        except ValueError as exc:
            row_errors.append(str(exc))
            tag_values = []

        if not date_payment and not date_application:
            row_errors.append("At least one date is required")
        if date_payment is None and date_application is not None:
            date_payment = date_application
        if date_application is None and date_payment is not None:
            date_application = date_payment

        payload, form_errors = transaction_validation.validate_transaction_form(
            amount_raw=row.get("amount") or "",
            category=row.get("category"),
            payer=row.get("payer"),
            payee=row.get("payee"),
            payment_type=row.get("payment_type"),
            subcategory=row.get("subcategory"),
            notes=row.get("notes"),
            selected_tags=tag_values,
            new_tag=None,
        )
        if form_errors:
            row_errors.extend(form_errors)

        if row_errors:
            errors.append(ValidationError(row=index, message="; ".join(row_errors)))
            continue

        parsed.append(
            ParsedRow(
                date_payment=date_payment or "",
                date_application=date_application or "",
                amount_cents=int(payload["amount_cents"]),
                payer=payload["payer"],
                payee=payload["payee"],
                payment_type=payload["payment_type"],
                category=str(payload["category"]),
                subcategory=payload["subcategory"],
                notes=payload["notes"],
                tags=payload["tags"],
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


def _parse_date_optional(value: Optional[str], field_label: str) -> Optional[str]:
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


def _normalize_header(header: Optional[str]) -> str:
    cleaned = (header or "").strip().lower()
    if not cleaned:
        raise ValueError("CSV header cannot be empty")
    return cleaned


def _validate_headers(headers: List[str]) -> None:
    duplicates = {name for name in headers if headers.count(name) > 1}
    if duplicates:
        dup_list = ", ".join(sorted(duplicates))
        raise ValueError(f"Duplicate headers after normalization: {dup_list}")
