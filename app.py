import os
from pathlib import Path
import sqlite3

import streamlit as st

from src import db, settings

st.set_page_config(
    page_title="Database of Poveruomic Transactions",
    page_icon="\U0001F4B6",
    initial_sidebar_state="auto",
    layout="wide",
)

DEFAULT_DB_PATH = os.environ.get("FINANCE_DB_PATH", "/data/finance.db")
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
STATE_PATH = Path(__file__).resolve().parent / ".dopt_state.json"

state = settings.load_state(STATE_PATH)

if "db_path" not in st.session_state:
    st.session_state.db_path = state.get("last_db_path", DEFAULT_DB_PATH)
if "db_ready" not in st.session_state:
    st.session_state.db_ready = False

st.title("Home")
st.write("Choose a database path and open or create the schema.")

with st.form("db_path_form"):
    db_input = st.text_input("Database path", value=st.session_state.db_path)
    submitted = st.form_submit_button("Set path")

if submitted:
    cleaned = db_input.strip()
    if cleaned:
        st.session_state.db_path = cleaned
        st.session_state.db_ready = False
    else:
        st.warning("Database path is required.")

current_path = Path(st.session_state.db_path).expanduser()

st.subheader("Current settings")
st.write(f"DB path: {current_path}")
st.write(f"DB ready: {'yes' if st.session_state.db_ready else 'no'}")
st.caption(f"FINANCE_DB_PATH default: {DEFAULT_DB_PATH}")

if current_path.exists() and current_path.is_dir():
    st.error("The database path points to a directory. Please use a file path.")
else:
    parent_ok = current_path.parent.exists()
    if not parent_ok:
        st.error(f"Parent directory does not exist: {current_path.parent}")

    if current_path.exists() and parent_ok:
        if st.button("Open existing database"):
            try:
                conn = db.connect(str(current_path))
                if db.schema_is_valid(conn):
                    st.session_state.db_ready = True
                    settings.save_state(STATE_PATH, {"last_db_path": str(current_path)})
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
    elif parent_ok:
        if st.button("Create database and schema"):
            try:
                conn = db.connect(str(current_path))
                db.init_db(conn, str(SCHEMA_PATH))
                st.session_state.db_ready = True
                settings.save_state(STATE_PATH, {"last_db_path": str(current_path)})
                st.success("Database created and schema initialized.")
            except sqlite3.Error as exc:
                st.session_state.db_ready = False
                st.error(f"Failed to create database: {exc}")
            finally:
                if "conn" in locals():
                    conn.close()

if st.button("Switch DB"):
    st.session_state.db_ready = False
    st.info("You can set a new database path above.")
