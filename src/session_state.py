from pathlib import Path
import sqlite3

import streamlit as st

from src import db, settings


def ensure_db_session_state() -> None:
    settings_conn = settings.connect_settings_db()
    app_settings = settings.get_app_settings(settings_conn)

    if "db_path" not in st.session_state:
        st.session_state.db_path = (
            app_settings.get("last_used_db_path") or settings.DEFAULT_DB_PATH
        )
    if "db_ready" not in st.session_state:
        st.session_state.db_ready = False
    if "db_auto_open_attempted" not in st.session_state:
        st.session_state.db_auto_open_attempted = False

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
            except sqlite3.Error:
                st.session_state.db_ready = False
            finally:
                if "conn" in locals():
                    conn.close()

    settings_conn.close()
