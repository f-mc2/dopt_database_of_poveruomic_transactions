import os
from pathlib import Path
import sqlite3

import streamlit as st

from src import db, session_state, settings, ui_widgets

st.set_page_config(
    page_title="HOME",
    page_icon="\U0001F4B6",
    initial_sidebar_state="auto",
    layout="wide",
)

REPO_ROOT = Path(__file__).resolve().parent
SCHEMA_PATH = REPO_ROOT / "schema.sql"


def _reset_session_state(
    new_db_path: str,
    import_dir: str,
    export_dir: str,
    backup_dir: str,
) -> None:
    st.session_state.clear()
    st.session_state.db_path = new_db_path
    st.session_state.db_ready = False
    st.session_state.db_auto_open_attempted = False
    st.session_state.csv_import_dir = import_dir
    st.session_state.csv_export_dir = export_dir
    st.session_state.db_backup_dir = backup_dir
    st.session_state.db_switch_notice = True


def _ensure_parent_dir(path: Path) -> bool:
    parent = path.parent
    if parent.exists():
        return True
    try:
        if parent.resolve().is_relative_to(REPO_ROOT):
            parent.mkdir(parents=True, exist_ok=True)
            return True
    except (OSError, RuntimeError):
        return False
    return False


st.markdown("# Home")

settings_conn = settings.connect_settings_db()
session_state.ensure_db_session_state(settings_conn)
ui_widgets.render_sidebar_nav()
recent_paths = settings.get_recent_db_paths(settings_conn)

st.subheader("Database selection")
if st.session_state.get("db_auto_open_error"):
    st.warning(st.session_state.db_auto_open_error)
    st.session_state.db_auto_open_error = None

recent_choice = st.selectbox(
    "Recent databases",
    ["(manual)"] + recent_paths,
    index=0,
    key="recent_db_choice",
)
manual_path = st.text_input(
    "Manual database path",
    value=st.session_state.db_path,
    key="manual_db_path",
)

selected_path = manual_path.strip() if recent_choice == "(manual)" else recent_choice
current_path = Path(st.session_state.db_path).expanduser()

confirm_switch = False
if selected_path and selected_path != st.session_state.db_path and st.session_state.db_ready:
    confirm_switch = st.checkbox(
        "Confirm switch (resets filters)",
        key="confirm_db_switch",
    )

if st.button("Use selected path"):
    if not selected_path:
        st.warning("Database path is required.")
    elif selected_path != st.session_state.db_path:
        if st.session_state.db_ready and not confirm_switch:
            st.warning("Confirm the switch to reset session filters.")
        else:
            _reset_session_state(
                selected_path,
                st.session_state.csv_import_dir,
                st.session_state.csv_export_dir,
                st.session_state.db_backup_dir,
            )
            st.success("Database path updated.")
            st.rerun()

if st.session_state.get("db_switch_notice"):
    st.info("Session reset after switching databases.")
    st.session_state.db_switch_notice = False

st.caption(f"FINANCE_DB_PATH default: {settings.DEFAULT_DB_PATH}")

if current_path.exists() and current_path.is_dir():
    st.error("The database path points to a directory. Please use a file path.")
else:
    parent_ok = current_path.parent.exists()
    if not parent_ok:
        st.warning(
            f"Parent directory does not exist: {current_path.parent}. "
            "It will be created for local data paths when creating a new database."
        )

    if current_path.exists() and parent_ok:
        if st.button("Open existing database"):
            try:
                conn = db.connect(str(current_path))
                if db.schema_is_valid(conn):
                    st.session_state.db_ready = True
                    settings.update_app_settings(
                        settings_conn, last_used_db_path=str(current_path)
                    )
                    settings.record_recent_db_path(settings_conn, str(current_path))
                    st.success("Database opened and schema validated.")
                else:
                    st.session_state.db_ready = False
                    st.error("Schema validation failed for this database.")
            except sqlite3.Error as exc:
                st.session_state.db_ready = False
                st.error(f"Failed to open database: {exc}")
            finally:
                if "conn" in locals():
                    conn.close()
    else:
        if st.button("Create database and schema"):
            if not _ensure_parent_dir(current_path):
                st.error("Parent directory does not exist and could not be created.")
            else:
                try:
                    conn = db.connect(str(current_path))
                    db.init_db(conn, str(SCHEMA_PATH))
                    st.session_state.db_ready = True
                    settings.update_app_settings(
                        settings_conn, last_used_db_path=str(current_path)
                    )
                    settings.record_recent_db_path(settings_conn, str(current_path))
                    st.success("Database created and schema initialized.")
                except sqlite3.Error as exc:
                    st.session_state.db_ready = False
                    st.error(f"Failed to create database: {exc}")
                finally:
                    if "conn" in locals():
                        conn.close()

st.divider()
st.subheader("Directories")
with st.form("directory_settings"):
    import_dir = st.text_input("CSV import directory", st.session_state.csv_import_dir)
    export_dir = st.text_input("CSV export directory", st.session_state.csv_export_dir)
    backup_dir = st.text_input("DB backup directory", st.session_state.db_backup_dir)
    dir_submit = st.form_submit_button("Save directories")
if dir_submit:
    st.session_state.csv_import_dir = import_dir.strip() or settings.DEFAULT_IMPORT_DIR
    st.session_state.csv_export_dir = export_dir.strip() or settings.DEFAULT_EXPORT_DIR
    st.session_state.db_backup_dir = backup_dir.strip() or settings.DEFAULT_BACKUP_DIR
    settings.update_app_settings(
        settings_conn,
        csv_import_dir=st.session_state.csv_import_dir,
        csv_export_dir=st.session_state.csv_export_dir,
        db_backup_dir=st.session_state.db_backup_dir,
    )
    st.success("Directories saved.")

settings_conn.close()
