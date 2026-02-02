import sqlite3
from pathlib import Path
from typing import List, Optional, Sequence

DEFAULT_TIMEOUT_SECONDS = 30
REQUIRED_TABLES = ("transactions", "tags", "transaction_tags")
REQUIRED_TRANSACTION_COLUMNS = {
    "id",
    "date_payment",
    "date_application",
    "amount_cents",
    "payer",
    "payee",
    "payment_type",
    "category",
    "subcategory",
    "notes",
}

SETTINGS_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS app_settings (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  last_used_db_path TEXT NULL,
  csv_import_dir TEXT NULL,
  csv_export_dir TEXT NULL,
  db_backup_dir TEXT NULL
);

CREATE TABLE IF NOT EXISTS recent_db_paths (
  path TEXT PRIMARY KEY,
  last_used_at INTEGER NOT NULL
);
"""


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


def init_settings_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SETTINGS_SCHEMA_SQL)
    conn.execute("INSERT OR IGNORE INTO app_settings (id) VALUES (1)")
    conn.commit()


def schema_is_valid(conn: sqlite3.Connection) -> bool:
    for table_name in REQUIRED_TABLES:
        row = fetch_one(
            conn,
            "SELECT name FROM sqlite_master WHERE type = ? AND name = ?",
            ("table", table_name),
        )
        if row is None:
            return False
    columns = conn.execute("PRAGMA table_info(transactions)").fetchall()
    column_names = {row[1] for row in columns}
    if not REQUIRED_TRANSACTION_COLUMNS.issubset(column_names):
        return False
    return True


def backup_db(conn: sqlite3.Connection, target_path: str) -> None:
    target_conn = sqlite3.connect(target_path)
    try:
        conn.backup(target_conn)
    finally:
        target_conn.close()


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
