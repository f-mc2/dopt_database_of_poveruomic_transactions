import sqlite3
from pathlib import Path
from typing import List, Optional, Sequence

DEFAULT_TIMEOUT_SECONDS = 30


def connect(db_path: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=timeout)
    conn.row_factory = sqlite3.Row
    _configure_connection(conn)
    return conn


def _configure_connection(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")


def init_db(conn: sqlite3.Connection, schema_path: str) -> None:
    schema_sql = Path(schema_path).read_text(encoding="utf-8")
    conn.executescript(schema_sql)
    conn.commit()


def execute(conn: sqlite3.Connection, sql: str, params: Sequence[object] = ()) -> sqlite3.Cursor:
    return conn.execute(sql, params)


def fetch_one(
    conn: sqlite3.Connection, sql: str, params: Sequence[object] = ()
) -> Optional[sqlite3.Row]:
    cursor = conn.execute(sql, params)
    return cursor.fetchone()


def fetch_all(conn: sqlite3.Connection, sql: str, params: Sequence[object] = ()) -> List[sqlite3.Row]:
    cursor = conn.execute(sql, params)
    return cursor.fetchall()
