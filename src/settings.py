import os
import time
from pathlib import Path
from typing import Dict, List, Optional

import sqlite3

from src import db

DEFAULT_DB_PATH = os.environ.get("FINANCE_DB_PATH", "/data/finance.db")
DEFAULT_IMPORT_DIR = os.environ.get("FINANCE_CSV_IMPORT_DIR", "/data/csv_import")
DEFAULT_EXPORT_DIR = os.environ.get("FINANCE_CSV_EXPORT_DIR", "/data/csv_export")
DEFAULT_BACKUP_DIR = os.environ.get("FINANCE_DB_BACKUP_DIR", "/data/db_backup")


def settings_db_path() -> str:
    base_path = Path(DEFAULT_DB_PATH).expanduser()
    return str(base_path.parent / "app_settings.db")


def connect_settings_db() -> sqlite3.Connection:
    conn = db.connect(settings_db_path())
    db.init_settings_db(conn)
    return conn


def get_app_settings(conn: sqlite3.Connection) -> Dict[str, Optional[str]]:
    row = db.fetch_one(
        conn,
        """
        SELECT last_used_db_path, theme, csv_import_dir, csv_export_dir, db_backup_dir
        FROM app_settings
        WHERE id = 1
        """,
    )
    if row is None:
        return {
            "last_used_db_path": None,
            "theme": "light",
            "csv_import_dir": None,
            "csv_export_dir": None,
            "db_backup_dir": None,
        }
    return {
        "last_used_db_path": row["last_used_db_path"],
        "theme": row["theme"],
        "csv_import_dir": row["csv_import_dir"],
        "csv_export_dir": row["csv_export_dir"],
        "db_backup_dir": row["db_backup_dir"],
    }


def update_app_settings(conn: sqlite3.Connection, **fields: Optional[str]) -> None:
    allowed = {"last_used_db_path", "theme", "csv_import_dir", "csv_export_dir", "db_backup_dir"}
    updates = {key: value for key, value in fields.items() if key in allowed}
    if not updates:
        return
    assignments = ", ".join(f"{key} = ?" for key in updates.keys())
    params = list(updates.values())
    params.append(1)
    db.execute(conn, f"UPDATE app_settings SET {assignments} WHERE id = ?", params)
    conn.commit()


def get_recent_db_paths(conn: sqlite3.Connection, limit: int = 3) -> List[str]:
    rows = db.fetch_all(
        conn,
        "SELECT path FROM recent_db_paths ORDER BY last_used_at DESC LIMIT ?",
        (limit,),
    )
    return [row["path"] for row in rows]


def record_recent_db_path(conn: sqlite3.Connection, path: str, limit: int = 3) -> None:
    timestamp = int(time.time())
    db.execute(
        conn,
        """
        INSERT INTO recent_db_paths(path, last_used_at)
        VALUES (?, ?)
        ON CONFLICT(path) DO UPDATE SET last_used_at = excluded.last_used_at
        """,
        (path, timestamp),
    )
    keep_rows = db.fetch_all(
        conn,
        "SELECT path FROM recent_db_paths ORDER BY last_used_at DESC LIMIT ?",
        (limit,),
    )
    keep_paths = [row["path"] for row in keep_rows]
    if not keep_paths:
        return
    placeholders = ",".join("?" for _ in keep_paths)
    db.execute(
        conn,
        f"DELETE FROM recent_db_paths WHERE path NOT IN ({placeholders})",
        keep_paths,
    )
    conn.commit()


def resolve_setting(value: Optional[str], default: str) -> str:
    cleaned = (value or "").strip()
    return cleaned if cleaned else default
