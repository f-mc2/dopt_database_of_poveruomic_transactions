import sqlite3
from typing import List, Optional, Tuple

from src import db


DOPT_COLUMNS = {"payer", "payee", "payment_type", "category", "subcategory"}


def normalize_finance_value(value: str) -> str:
    cleaned = value.strip().lower()
    if not cleaned:
        raise ValueError("Value cannot be empty")
    return cleaned


def list_value_counts(conn: sqlite3.Connection, column: str) -> List[Tuple[str, int]]:
    if column not in DOPT_COLUMNS or column == "subcategory":
        raise ValueError(f"Unsupported column: {column}")
    where_clause = "WHERE {col} IS NOT NULL".format(col=column) if column != "category" else ""
    rows = db.fetch_all(
        conn,
        f"""
        SELECT {column} AS value, COUNT(*) AS count
        FROM transactions
        {where_clause}
        GROUP BY {column}
        ORDER BY count DESC, {column}
        """,
    )
    return [(row["value"], int(row["count"])) for row in rows]


def list_subcategory_counts(conn: sqlite3.Connection, category: Optional[str] = None) -> List[Tuple[str, str, int]]:
    params: List[object] = []
    where_parts = ["subcategory IS NOT NULL"]
    if category:
        where_parts.append("category = ?")
        params.append(category)
    where_sql = " AND ".join(where_parts)
    rows = db.fetch_all(
        conn,
        f"""
        SELECT category, subcategory, COUNT(*) AS count
        FROM transactions
        WHERE {where_sql}
        GROUP BY category, subcategory
        ORDER BY category, subcategory
        """,
        params,
    )
    return [(row["category"], row["subcategory"], int(row["count"])) for row in rows]


def rename_value(
    conn: sqlite3.Connection,
    column: str,
    old_value: str,
    new_value: str,
    category: Optional[str] = None,
) -> int:
    if column not in DOPT_COLUMNS:
        raise ValueError(f"Unsupported column: {column}")
    if column == "subcategory":
        if not category:
            raise ValueError("Category is required for subcategory rename")
        cursor = db.execute(
            conn,
            "UPDATE transactions SET subcategory = ? WHERE category = ? AND subcategory = ?",
            (new_value, category, old_value),
        )
        return cursor.rowcount
    cursor = db.execute(
        conn,
        f"UPDATE transactions SET {column} = ? WHERE {column} = ?",
        (new_value, old_value),
    )
    return cursor.rowcount


def clear_value(
    conn: sqlite3.Connection,
    column: str,
    value: str,
    category: Optional[str] = None,
) -> int:
    if column not in DOPT_COLUMNS:
        raise ValueError(f"Unsupported column: {column}")
    if column == "category":
        raise ValueError("Category cannot be cleared")
    if column == "subcategory":
        if not category:
            raise ValueError("Category is required for subcategory delete")
        cursor = db.execute(
            conn,
            "UPDATE transactions SET subcategory = NULL WHERE category = ? AND subcategory = ?",
            (category, value),
        )
        return cursor.rowcount
    cursor = db.execute(
        conn,
        f"UPDATE transactions SET {column} = NULL WHERE {column} = ?",
        (value,),
    )
    return cursor.rowcount


def count_payer_rename_conflicts(conn: sqlite3.Connection, old_value: str, new_value: str) -> int:
    row = db.fetch_one(
        conn,
        "SELECT COUNT(*) AS count FROM transactions WHERE payer = ? AND payee = ?",
        (old_value, new_value),
    )
    return int(row["count"]) if row else 0


def count_payee_rename_conflicts(conn: sqlite3.Connection, old_value: str, new_value: str) -> int:
    row = db.fetch_one(
        conn,
        "SELECT COUNT(*) AS count FROM transactions WHERE payee = ? AND payer = ?",
        (old_value, new_value),
    )
    return int(row["count"]) if row else 0


def count_payer_delete_conflicts(conn: sqlite3.Connection, value: str) -> int:
    row = db.fetch_one(
        conn,
        "SELECT COUNT(*) AS count FROM transactions WHERE payer = ? AND payee IS NULL",
        (value,),
    )
    return int(row["count"]) if row else 0


def count_payee_delete_conflicts(conn: sqlite3.Connection, value: str) -> int:
    row = db.fetch_one(
        conn,
        "SELECT COUNT(*) AS count FROM transactions WHERE payee = ? AND payer IS NULL",
        (value,),
    )
    return int(row["count"]) if row else 0
