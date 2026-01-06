import sqlite3
from typing import Dict, Iterable, List, Optional, Tuple

from src import db

ALLOWED_DISTINCT_COLUMNS = {"payer", "payee", "category", "subcategory"}


def get_distinct_values(conn: sqlite3.Connection, column: str) -> List[str]:
    if column not in ALLOWED_DISTINCT_COLUMNS:
        raise ValueError(f"Unsupported column: {column}")
    sql_map = {
        "payer": "SELECT DISTINCT payer AS value FROM transactions WHERE payer IS NOT NULL ORDER BY payer",
        "payee": "SELECT DISTINCT payee AS value FROM transactions WHERE payee IS NOT NULL ORDER BY payee",
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


def list_transactions(conn: sqlite3.Connection, filters: Dict[str, object]) -> List[sqlite3.Row]:
    where_clauses: List[str] = []
    params: List[object] = []

    _apply_date_filters(filters, where_clauses, params)
    _apply_list_filter("t.payer", filters.get("payers"), where_clauses, params)
    _apply_list_filter("t.payee", filters.get("payees"), where_clauses, params)
    _apply_list_filter("t.category", filters.get("categories"), where_clauses, params)
    _apply_list_filter("t.subcategory", filters.get("subcategories"), where_clauses, params)
    _apply_tag_filter(filters.get("tags"), where_clauses, params)
    _apply_search_filter(filters.get("search"), where_clauses, params)

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    sql = f"""
        SELECT
            t.id,
            t.date,
            t.amount_cents,
            t.payer,
            t.payee,
            t.category,
            t.subcategory,
            t.notes,
            GROUP_CONCAT(tg.name, ',') AS tags
        FROM transactions t
        LEFT JOIN transaction_tags tt ON tt.transaction_id = t.id
        LEFT JOIN tags tg ON tg.id = tt.tag_id
        {where_sql}
        GROUP BY t.id
        ORDER BY t.date DESC, t.id DESC
    """
    return db.fetch_all(conn, sql, params)


def get_transaction(conn: sqlite3.Connection, transaction_id: int) -> Optional[sqlite3.Row]:
    return db.fetch_one(
        conn,
        """
        SELECT
            t.id,
            t.date,
            t.amount_cents,
            t.payer,
            t.payee,
            t.category,
            t.subcategory,
            t.notes,
            t.created_at,
            t.updated_at
        FROM transactions t
        WHERE t.id = ?
        """,
        (transaction_id,),
    )


def update_transaction(
    conn: sqlite3.Connection,
    transaction_id: int,
    date: str,
    amount_cents: int,
    payer: Optional[str],
    payee: Optional[str],
    category: str,
    subcategory: Optional[str],
    notes: Optional[str],
    updated_at: str,
) -> None:
    db.execute(
        conn,
        """
        UPDATE transactions
        SET date = ?,
            amount_cents = ?,
            payer = ?,
            payee = ?,
            category = ?,
            subcategory = ?,
            notes = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            date,
            amount_cents,
            payer,
            payee,
            category,
            subcategory,
            notes,
            updated_at,
            transaction_id,
        ),
    )


def delete_transaction(conn: sqlite3.Connection, transaction_id: int) -> None:
    db.execute(conn, "DELETE FROM transactions WHERE id = ?", (transaction_id,))


def get_date_bounds(conn: sqlite3.Connection) -> Tuple[Optional[str], Optional[str]]:
    row = db.fetch_one(conn, "SELECT MIN(date) AS min_date, MAX(date) AS max_date FROM transactions")
    if row is None:
        return None, None
    return row["min_date"], row["max_date"]


def _apply_date_filters(
    filters: Dict[str, object], where_clauses: List[str], params: List[object]
) -> None:
    start_date = filters.get("date_start")
    end_date = filters.get("date_end")
    if start_date:
        where_clauses.append("t.date >= ?")
        params.append(start_date)
    if end_date:
        where_clauses.append("t.date <= ?")
        params.append(end_date)


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
    include_null = any(item is None for item in selected)
    non_null = [item for item in selected if item is not None]
    parts: List[str] = []
    if non_null:
        placeholders = ",".join("?" for _ in non_null)
        parts.append(f"{column} IN ({placeholders})")
        params.extend(non_null)
    if include_null:
        parts.append(f"{column} IS NULL")
    if parts:
        where_clauses.append("(" + " OR ".join(parts) + ")")


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
