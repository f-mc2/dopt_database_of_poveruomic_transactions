import sqlite3
from typing import Dict, Iterable, List, Optional, Tuple

from src import db

ALLOWED_DISTINCT_COLUMNS = {"payer", "payee", "payment_type", "category", "subcategory"}
DATE_FIELDS = {"date_payment", "date_application"}
DEFAULT_DATE_FIELD = "date_application"
DATE_FIELD_LABELS = {
    "date_payment": "Payment date",
    "date_application": "Application date",
}
SORT_COLUMNS = {
    "id": "t.id",
    "date_payment": "t.date_payment",
    "date_application": "t.date_application",
    "amount_cents": "t.amount_cents",
    "payer": "t.payer",
    "payee": "t.payee",
    "payment_type": "t.payment_type",
    "category": "t.category",
    "subcategory": "t.subcategory",
    "notes": "t.notes",
    "tags": "tags",
}


def get_distinct_values(conn: sqlite3.Connection, column: str) -> List[str]:
    if column not in ALLOWED_DISTINCT_COLUMNS:
        raise ValueError(f"Unsupported column: {column}")
    sql_map = {
        "payer": "SELECT DISTINCT payer AS value FROM transactions WHERE payer IS NOT NULL ORDER BY payer",
        "payee": "SELECT DISTINCT payee AS value FROM transactions WHERE payee IS NOT NULL ORDER BY payee",
        "payment_type": "SELECT DISTINCT payment_type AS value FROM transactions WHERE payment_type IS NOT NULL ORDER BY payment_type",
        "category": "SELECT DISTINCT category AS value FROM transactions WHERE category IS NOT NULL ORDER BY category",
        "subcategory": "SELECT DISTINCT subcategory AS value FROM transactions WHERE subcategory IS NOT NULL ORDER BY subcategory",
    }
    rows = db.fetch_all(conn, sql_map[column])
    return [row["value"] for row in rows]


def get_category_subcategory_pairs(conn: sqlite3.Connection) -> List[Tuple[str, str]]:
    rows = db.fetch_all(
        conn,
        """
        SELECT DISTINCT category, subcategory
        FROM transactions
        WHERE subcategory IS NOT NULL
        ORDER BY category, subcategory
        """,
    )
    return [(row["category"], row["subcategory"]) for row in rows]


def get_subcategories_for_category(conn: sqlite3.Connection, category: str) -> List[str]:
    rows = db.fetch_all(
        conn,
        """
        SELECT DISTINCT subcategory
        FROM transactions
        WHERE category = ? AND subcategory IS NOT NULL
        ORDER BY subcategory
        """,
        (category,),
    )
    return [row["subcategory"] for row in rows]


def list_transactions(
    conn: sqlite3.Connection,
    filters: Dict[str, object],
    sort_by: Optional[str] = None,
    sort_dir: str = "desc",
    limit: Optional[int] = None,
) -> List[sqlite3.Row]:
    where_clauses: List[str] = []
    params: List[object] = []

    date_field = _resolve_date_field(filters.get("date_field"))
    _apply_date_filters(date_field, filters, where_clauses, params)
    _apply_optional_filter(
        "t.payer",
        filters.get("payers"),
        bool(filters.get("include_missing_payer")),
        where_clauses,
        params,
    )
    _apply_optional_filter(
        "t.payee",
        filters.get("payees"),
        bool(filters.get("include_missing_payee")),
        where_clauses,
        params,
    )
    _apply_optional_filter(
        "t.payment_type",
        filters.get("payment_types"),
        bool(filters.get("include_missing_payment_type")),
        where_clauses,
        params,
    )
    _apply_list_filter("t.category", filters.get("categories"), where_clauses, params)
    _apply_subcategory_filter(filters.get("subcategory_pairs"), where_clauses, params)
    _apply_tag_filter(filters.get("tags"), where_clauses, params)
    _apply_search_filter(filters.get("search"), where_clauses, params)

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    order_sql = _build_order_by(sort_by or date_field, sort_dir, date_field)
    limit_sql = ""
    if isinstance(limit, int) and limit > 0:
        limit_sql = "LIMIT ?"
        params.append(limit)

    sql = f"""
        SELECT
            t.id,
            t.date_payment,
            t.date_application,
            t.amount_cents,
            t.payer,
            t.payee,
            t.payment_type,
            t.category,
            t.subcategory,
            t.notes,
            (
                SELECT GROUP_CONCAT(name, ',')
                FROM (
                    SELECT tg.name AS name
                    FROM tags tg
                    JOIN transaction_tags tt ON tt.tag_id = tg.id
                    WHERE tt.transaction_id = t.id
                    ORDER BY tg.name
                )
            ) AS tags
        FROM transactions t
        {where_sql}
        ORDER BY {order_sql}
        {limit_sql}
    """
    return db.fetch_all(conn, sql, params)


def get_transaction(conn: sqlite3.Connection, transaction_id: int) -> Optional[sqlite3.Row]:
    return db.fetch_one(
        conn,
        """
        SELECT
            t.id,
            t.date_payment,
            t.date_application,
            t.amount_cents,
            t.payer,
            t.payee,
            t.payment_type,
            t.category,
            t.subcategory,
            t.notes
        FROM transactions t
        WHERE t.id = ?
        """,
        (transaction_id,),
    )


def update_transaction(
    conn: sqlite3.Connection,
    transaction_id: int,
    date_payment: str,
    date_application: str,
    amount_cents: int,
    payer: Optional[str],
    payee: Optional[str],
    payment_type: Optional[str],
    category: str,
    subcategory: Optional[str],
    notes: Optional[str],
) -> None:
    db.execute(
        conn,
        """
        UPDATE transactions
        SET date_payment = ?,
            date_application = ?,
            amount_cents = ?,
            payer = ?,
            payee = ?,
            payment_type = ?,
            category = ?,
            subcategory = ?,
            notes = ?
        WHERE id = ?
        """,
        (
            date_payment,
            date_application,
            amount_cents,
            payer,
            payee,
            payment_type,
            category,
            subcategory,
            notes,
            transaction_id,
        ),
    )


def insert_transaction(
    conn: sqlite3.Connection,
    date_payment: str,
    date_application: str,
    amount_cents: int,
    payer: Optional[str],
    payee: Optional[str],
    payment_type: Optional[str],
    category: str,
    subcategory: Optional[str],
    notes: Optional[str],
) -> int:
    cursor = db.execute(
        conn,
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
            date_payment,
            date_application,
            amount_cents,
            payer,
            payee,
            payment_type,
            category,
            subcategory,
            notes,
        ),
    )
    if cursor.lastrowid is None:
        raise ValueError("Failed to insert transaction")
    return int(cursor.lastrowid)


def delete_transaction(conn: sqlite3.Connection, transaction_id: int) -> None:
    db.execute(conn, "DELETE FROM transactions WHERE id = ?", (transaction_id,))


def get_date_bounds(
    conn: sqlite3.Connection, date_field: str
) -> Tuple[Optional[str], Optional[str]]:
    date_field = _resolve_date_field(date_field)
    sql = f"SELECT MIN({date_field}) AS min_date, MAX({date_field}) AS max_date FROM transactions"
    row = db.fetch_one(conn, sql)
    if row is None:
        return None, None
    return row["min_date"], row["max_date"]


def _apply_date_filters(
    date_field: str, filters: Dict[str, object], where_clauses: List[str], params: List[object]
) -> None:
    start_date = filters.get("date_start")
    end_date = filters.get("date_end")
    if start_date:
        where_clauses.append(f"t.{date_field} >= ?")
        params.append(start_date)
    if end_date:
        where_clauses.append(f"t.{date_field} <= ?")
        params.append(end_date)


def _resolve_date_field(value: object) -> str:
    if isinstance(value, str) and value in DATE_FIELDS:
        return value
    return DEFAULT_DATE_FIELD


def _apply_list_filter(
    column: str,
    values: object,
    where_clauses: List[str],
    params: List[object],
) -> None:
    if not values:
        return
    if isinstance(values, str):
        selected = [values]
    elif isinstance(values, Iterable):
        selected = list(values)
    else:
        selected = []
    if not selected:
        return
    placeholders = ",".join("?" for _ in selected)
    where_clauses.append(f"{column} IN ({placeholders})")
    params.extend(selected)


def _apply_tag_filter(values: object, where_clauses: List[str], params: List[object]) -> None:
    if not values:
        return
    if isinstance(values, str):
        selected = [values]
    elif isinstance(values, Iterable):
        selected = list(values)
    else:
        selected = []
    if not selected:
        return
    placeholders = ",".join("?" for _ in selected)
    where_clauses.append(
        "EXISTS ("
        "SELECT 1 "
        "FROM transaction_tags tt "
        "JOIN tags tg ON tg.id = tt.tag_id "
        "WHERE tt.transaction_id = t.id "
        "  AND tg.name IN (" + placeholders + ")"
        ")"
    )
    params.extend(selected)


def _apply_optional_filter(
    column: str,
    values: object,
    include_missing: bool,
    where_clauses: List[str],
    params: List[object],
) -> None:
    if not values:
        return
    if isinstance(values, str):
        selected = [values]
    elif isinstance(values, Iterable):
        selected = list(values)
    else:
        selected = []
    if not selected:
        return
    parts: List[str] = []
    placeholders = ",".join("?" for _ in selected)
    parts.append(f"{column} IN ({placeholders})")
    params.extend(selected)
    if include_missing:
        parts.append(f"{column} IS NULL")
    where_clauses.append("(" + " OR ".join(parts) + ")")


def _apply_subcategory_filter(
    pairs: object, where_clauses: List[str], params: List[object]
) -> None:
    if not pairs:
        return
    if isinstance(pairs, tuple):
        pairs_list = [pairs]
    elif isinstance(pairs, Iterable):
        pairs_list = list(pairs)
    else:
        pairs_list = []
    if not pairs_list:
        return
    parts: List[str] = []
    for pair in pairs_list:
        if not isinstance(pair, tuple) or len(pair) != 2:
            continue
        parts.append("(t.category = ? AND t.subcategory = ?)")
        params.extend([pair[0], pair[1]])
    if parts:
        where_clauses.append("(" + " OR ".join(parts) + ")")


def _apply_search_filter(search: object, where_clauses: List[str], params: List[object]) -> None:
    if not isinstance(search, str):
        return
    cleaned = search.strip().lower()
    if not cleaned:
        return
    like = f"%{cleaned}%"
    where_clauses.append(
        """
        (
            LOWER(COALESCE(t.payer, '')) LIKE ? OR
            LOWER(COALESCE(t.payee, '')) LIKE ? OR
            LOWER(COALESCE(t.category, '')) LIKE ? OR
            LOWER(COALESCE(t.subcategory, '')) LIKE ? OR
            LOWER(COALESCE(t.notes, '')) LIKE ? OR
            EXISTS (
                SELECT 1
                FROM transaction_tags tt
                JOIN tags tg ON tg.id = tt.tag_id
                WHERE tt.transaction_id = t.id
                  AND LOWER(tg.name) LIKE ?
            )
        )
        """
    )
    params.extend([like, like, like, like, like, like])


def _build_order_by(sort_by: str, sort_dir: str, fallback_date_field: str) -> str:
    column = SORT_COLUMNS.get(sort_by)
    if column is None:
        column = SORT_COLUMNS.get(fallback_date_field, "t.date_application")
    direction = "DESC" if str(sort_dir).lower() != "asc" else "ASC"
    if column == "tags":
        return f"{column} {direction}, t.id DESC"
    return f"{column} {direction}, t.id DESC"
