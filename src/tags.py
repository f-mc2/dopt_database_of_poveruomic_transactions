import sqlite3
from typing import Iterable, List

from src import db


def normalize_tag(name: str) -> str:
    return name.strip().lower()


def parse_tags(raw: str) -> List[str]:
    if raw is None:
        return []
    parts = [normalize_tag(part) for part in raw.split(",")]
    deduped: List[str] = []
    seen = set()
    for part in parts:
        if not part:
            continue
        if part in seen:
            continue
        seen.add(part)
        deduped.append(part)
    return deduped


def list_tags(conn: sqlite3.Connection) -> List[str]:
    rows = db.fetch_all(conn, "SELECT name FROM tags ORDER BY name")
    return [row["name"] for row in rows]


def upsert_tag(conn: sqlite3.Connection, name: str) -> int:
    normalized = normalize_tag(name)
    if not normalized:
        raise ValueError("Tag name cannot be empty")
    conn.execute("INSERT OR IGNORE INTO tags(name) VALUES (?)", (normalized,))
    row = db.fetch_one(conn, "SELECT id FROM tags WHERE name = ?", (normalized,))
    if row is None:
        raise ValueError("Failed to upsert tag")
    return int(row["id"])


def get_tags_for_transaction(conn: sqlite3.Connection, transaction_id: int) -> List[str]:
    rows = db.fetch_all(
        conn,
        """
        SELECT tg.name
        FROM tags tg
        JOIN transaction_tags tt ON tt.tag_id = tg.id
        WHERE tt.transaction_id = ?
        ORDER BY tg.name
        """,
        (transaction_id,),
    )
    return [row["name"] for row in rows]


def set_transaction_tags(
    conn: sqlite3.Connection, transaction_id: int, tag_names: Iterable[str]
) -> None:
    normalized: List[str] = []
    seen = set()
    for name in tag_names:
        cleaned = normalize_tag(name)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)

    conn.execute("DELETE FROM transaction_tags WHERE transaction_id = ?", (transaction_id,))
    for name in normalized:
        tag_id = upsert_tag(conn, name)
        conn.execute(
            "INSERT OR IGNORE INTO transaction_tags(transaction_id, tag_id) VALUES (?, ?)",
            (transaction_id, tag_id),
        )
