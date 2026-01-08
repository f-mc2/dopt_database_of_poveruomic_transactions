import os
import time
from pathlib import Path
from typing import Dict, List, Optional

import sqlite3

from src import db

REPO_ROOT = Path(__file__).resolve().parents[1]
REPO_DATA_DIR = REPO_ROOT / "data"


def _default_db_path() -> str:
    env_path = os.environ.get("FINANCE_DB_PATH")
    if env_path:
        return env_path
    if Path("/data").exists():
        return "/data/finance.db"
    return str(REPO_DATA_DIR / "finance.db")


DEFAULT_DB_PATH = _default_db_path()
def _default_dir(env_name: str, subdir: str) -> str:
    env_path = os.environ.get(env_name)
    if env_path:
        return env_path
    if Path("/data").exists():
        return f"/data/{subdir}"
    return str(REPO_DATA_DIR / subdir)


DEFAULT_IMPORT_DIR = _default_dir("FINANCE_CSV_IMPORT_DIR", "csv_import")
DEFAULT_EXPORT_DIR = _default_dir("FINANCE_CSV_EXPORT_DIR", "csv_export")
DEFAULT_BACKUP_DIR = _default_dir("FINANCE_DB_BACKUP_DIR", "db_backup")


def settings_db_path() -> str:
    base_path = Path(DEFAULT_DB_PATH).expanduser()
    return str(base_path.parent / "app_settings.db")


def connect_settings_db() -> sqlite3.Connection:
    path = Path(settings_db_path()).expanduser()
    _ensure_parent_dir(path)
    conn = db.connect(str(path))
    db.init_settings_db(conn)
    return conn


def get_app_settings(conn: sqlite3.Connection) -> Dict[str, Optional[str]]:
    row = db.fetch_one(
        conn,
        """
        SELECT last_used_db_path, csv_import_dir, csv_export_dir, db_backup_dir
        FROM app_settings
        WHERE id = 1
        """,
    )
    if row is None:
        return {
            "last_used_db_path": None,
            "csv_import_dir": None,
            "csv_export_dir": None,
            "db_backup_dir": None,
        }
    return {
        "last_used_db_path": row["last_used_db_path"],
        "csv_import_dir": row["csv_import_dir"],
        "csv_export_dir": row["csv_export_dir"],
        "db_backup_dir": row["db_backup_dir"],
    }


def update_app_settings(conn: sqlite3.Connection, **fields: Optional[str]) -> None:
    allowed = {"last_used_db_path", "csv_import_dir", "csv_export_dir", "db_backup_dir"}
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


def _ensure_parent_dir(path: Path) -> None:
    parent = path.parent
    if parent.exists():
        return
    try:
        if parent.resolve().is_relative_to(REPO_ROOT):
            parent.mkdir(parents=True, exist_ok=True)
    except (OSError, RuntimeError):
        return
