import sqlite3
from typing import Dict, List, Tuple

from src import db

VALUE_COLUMNS: Dict[str, Dict[str, object]] = {
    "payer": {
        "label": "Payer",
        "lower": False,
        "select_sql": "SELECT payer AS value, COUNT(*) AS count FROM transactions WHERE payer IS NOT NULL GROUP BY payer ORDER BY count DESC, payer",
        "rename_sql": "UPDATE transactions SET payer = ? WHERE payer = ?",
        "clear_sql": "UPDATE transactions SET payer = NULL WHERE payer = ?",
    },
    "payee": {
        "label": "Payee",
        "lower": False,
        "select_sql": "SELECT payee AS value, COUNT(*) AS count FROM transactions WHERE payee IS NOT NULL GROUP BY payee ORDER BY count DESC, payee",
        "rename_sql": "UPDATE transactions SET payee = ? WHERE payee = ?",
        "clear_sql": "UPDATE transactions SET payee = NULL WHERE payee = ?",
    },
    "category": {
        "label": "Category",
        "lower": True,
        "select_sql": "SELECT category AS value, COUNT(*) AS count FROM transactions WHERE category IS NOT NULL GROUP BY category ORDER BY count DESC, category",
        "rename_sql": "UPDATE transactions SET category = ? WHERE category = ?",
        "clear_sql": "UPDATE transactions SET category = NULL WHERE category = ?",
    },
    "subcategory": {
        "label": "Subcategory",
        "lower": True,
        "select_sql": "SELECT subcategory AS value, COUNT(*) AS count FROM transactions WHERE subcategory IS NOT NULL GROUP BY subcategory ORDER BY count DESC, subcategory",
        "rename_sql": "UPDATE transactions SET subcategory = ? WHERE subcategory = ?",
        "clear_sql": "UPDATE transactions SET subcategory = NULL WHERE subcategory = ?",
    },
}


def list_value_counts(conn: sqlite3.Connection, column: str) -> List[Tuple[str, int]]:
    config = VALUE_COLUMNS.get(column)
    if config is None:
        raise ValueError(f"Unsupported column: {column}")
    rows = db.fetch_all(conn, config["select_sql"])
    return [(row["value"], int(row["count"])) for row in rows]


def rename_value(conn: sqlite3.Connection, column: str, old_value: str, new_value: str) -> int:
    config = VALUE_COLUMNS.get(column)
    if config is None:
        raise ValueError(f"Unsupported column: {column}")
    cursor = db.execute(conn, config["rename_sql"], (new_value, old_value))
    return cursor.rowcount


def clear_value(conn: sqlite3.Connection, column: str, value: str) -> int:
    config = VALUE_COLUMNS.get(column)
    if config is None:
        raise ValueError(f"Unsupported column: {column}")
    cursor = db.execute(conn, config["clear_sql"], (value,))
    return cursor.rowcount


def normalize_value(column: str, value: str) -> str:
    config = VALUE_COLUMNS.get(column)
    if config is None:
        raise ValueError(f"Unsupported column: {column}")
    cleaned = value.strip()
    return cleaned.lower() if config["lower"] else cleaned
