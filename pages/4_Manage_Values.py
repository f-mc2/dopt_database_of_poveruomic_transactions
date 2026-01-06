import sqlite3
from typing import Optional

import streamlit as st

from src import db, tags, values

st.title("Manage Values")

if not st.session_state.get("db_ready"):
    st.warning("Open or create a database from the Home page first.")
    st.stop()

conn: Optional[sqlite3.Connection] = None
try:
    conn = db.connect(st.session_state.db_path)

    st.subheader("Transaction values")
    for column in ["payer", "payee", "payment_type", "category", "subcategory"]:
        config = values.VALUE_COLUMNS[column]
        label = config["label"]
        st.markdown(f"### {label}")

        counts = values.list_value_counts(conn, column)
        if not counts:
            st.info(f"No {label.lower()} values found.")
            continue

        st.dataframe(
            [{label.lower(): value, "count": count} for value, count in counts],
            use_container_width=True,
        )

        options = [value for value, _ in counts]
        count_map = {value: count for value, count in counts}
        selection = st.selectbox(
            f"Select {label.lower()}",
            options,
            key=f"{column}_select",
        )
        st.caption(f"Current count: {count_map.get(selection, 0)}")

        with st.form(f"{column}_rename_form"):
            new_value = st.text_input(f"Rename {label.lower()} to", key=f"{column}_rename")
            rename_submit = st.form_submit_button("Rename")
        if rename_submit:
            cleaned = new_value.strip()
            if not cleaned:
                st.error("New value cannot be empty.")
            else:
                normalized = values.normalize_value(column, cleaned)
                if normalized == selection:
                    st.warning("New value matches the current value.")
                else:
                    with conn:
                        rowcount = values.rename_value(conn, column, selection, normalized)
                    st.success(f"Renamed {rowcount} transactions.")
                    st.rerun()

        with st.form(f"{column}_delete_form"):
            confirm = st.checkbox("Confirm delete", key=f"{column}_delete_confirm")
            delete_submit = st.form_submit_button("Delete")
        if delete_submit:
            if not confirm:
                st.warning("Please confirm deletion.")
            else:
                try:
                    with conn:
                        rowcount = values.clear_value(conn, column, selection)
                    st.success(f"Cleared {rowcount} transactions.")
                    st.rerun()
                except sqlite3.IntegrityError as exc:
                    st.error(f"Delete failed: {exc}")

        st.divider()

    st.subheader("Tags")
    tag_counts = tags.tag_counts(conn)
    if not tag_counts:
        st.info("No tags available.")
    else:
        st.dataframe(
            [{"tag": name, "count": count} for name, count in tag_counts],
            use_container_width=True,
        )
        tag_names = [name for name, _ in tag_counts]
        tag_selection = st.selectbox("Select tag", tag_names, key="tag_select")

        with st.form("tag_rename_form"):
            new_tag = st.text_input("Rename tag to", key="tag_rename")
            rename_tag_submit = st.form_submit_button("Rename")
        if rename_tag_submit:
            cleaned = new_tag.strip()
            if not cleaned:
                st.error("New tag cannot be empty.")
            else:
                try:
                    with conn:
                        tags.rename_tag(conn, tag_selection, cleaned)
                    st.success("Tag renamed.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("A tag with that name already exists.")

        with st.form("tag_delete_form"):
            confirm_tag = st.checkbox("Confirm delete", key="tag_delete_confirm")
            delete_tag_submit = st.form_submit_button("Delete tag")
        if delete_tag_submit:
            if not confirm_tag:
                st.warning("Please confirm deletion.")
            else:
                with conn:
                    tags.delete_tag(conn, tag_selection)
                st.success("Tag deleted.")
                st.rerun()

finally:
    if conn is not None:
        conn.close()
