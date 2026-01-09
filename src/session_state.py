from pathlib import Path
import sqlite3
from typing import Optional

import streamlit as st

from src import db, settings


def ensure_db_session_state(
    settings_conn: Optional[sqlite3.Connection] = None,
    reload_paths: bool = False,
) -> None:
    close_conn = False
    if settings_conn is None:
        settings_conn = settings.connect_settings_db(st.session_state.get("db_path"))
        close_conn = True
    app_settings = settings.get_app_settings(settings_conn)

    if "db_path" not in st.session_state:
        st.session_state.db_path = (
            app_settings.get("last_used_db_path") or settings.DEFAULT_DB_PATH
        )
    if "db_ready" not in st.session_state:
        st.session_state.db_ready = False
    if "db_auto_open_attempted" not in st.session_state:
        st.session_state.db_auto_open_attempted = False
    if "db_auto_open_error" not in st.session_state:
        st.session_state.db_auto_open_error = None
    if "csv_import_dir" not in st.session_state or reload_paths:
        st.session_state.csv_import_dir = settings.resolve_setting(
            app_settings.get("csv_import_dir"), settings.DEFAULT_IMPORT_DIR
        )
    if "csv_export_dir" not in st.session_state or reload_paths:
        st.session_state.csv_export_dir = settings.resolve_setting(
            app_settings.get("csv_export_dir"), settings.DEFAULT_EXPORT_DIR
        )
    if "db_backup_dir" not in st.session_state or reload_paths:
        st.session_state.db_backup_dir = settings.resolve_setting(
            app_settings.get("db_backup_dir"), settings.DEFAULT_BACKUP_DIR
        )

    if not st.session_state.db_ready and not st.session_state.db_auto_open_attempted:
        st.session_state.db_auto_open_attempted = True
        current_path = Path(st.session_state.db_path).expanduser()
        if current_path.exists() and not current_path.is_dir():
            try:
                conn = db.connect(str(current_path))
                if db.schema_is_valid(conn):
                    st.session_state.db_ready = True
                    settings.update_app_settings(
                        settings_conn, last_used_db_path=str(current_path)
                    )
                    settings.record_recent_db_path(settings_conn, str(current_path))
                    st.session_state.db_auto_open_error = None
                else:
                    st.session_state.db_auto_open_error = (
                        "Saved database path has an invalid schema."
                    )
            except sqlite3.Error as exc:
                st.session_state.db_ready = False
                st.session_state.db_auto_open_error = f"Auto-open failed: {exc}"
            finally:
                if "conn" in locals():
                    conn.close()

    if close_conn:
        settings_conn.close()
