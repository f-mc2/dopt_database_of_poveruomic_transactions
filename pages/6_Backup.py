import datetime as dt
import os
from pathlib import Path
from typing import Optional

import sqlite3
import streamlit as st

from src import db

DEFAULT_BACKUP_DIR = os.environ.get("FINANCE_DB_BACKUP_DIR", "/data/db_backup")

if "db_backup_dir" not in st.session_state:
    st.session_state.db_backup_dir = DEFAULT_BACKUP_DIR

st.title("Backup")

if not st.session_state.get("db_ready"):
    st.warning("Open or create a database from the Home page first.")
    st.stop()

st.text_input("Backup directory", value=st.session_state.db_backup_dir, key="db_backup_dir")

conn: Optional[sqlite3.Connection] = None
try:
    if st.button("Backup now"):
        db_path = Path(st.session_state.db_path)
        if not db_path.exists():
            st.error("Database file does not exist.")
        else:
            backup_dir = Path(st.session_state.db_backup_dir)
            try:
                backup_dir.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                st.error(f"Failed to create backup directory: {exc}")
            else:
                timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"finance_backup_{timestamp}.db"
                target_path = backup_dir / filename
                try:
                    conn = db.connect(str(db_path))
                    db.backup_db(conn, str(target_path))
                    st.success(f"Backup created: {target_path}")
                except sqlite3.Error as exc:
                    st.error(f"Backup failed: {exc}")
finally:
    if conn is not None:
        conn.close()
