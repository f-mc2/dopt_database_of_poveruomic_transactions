import datetime as dt
import os
from typing import Optional

import sqlite3
import streamlit as st

from src import csv_io, db, queries, tags, ui_widgets


def _convert_empty_selection(selected):
    return [None if item == "(empty)" else item for item in selected]

DEFAULT_IMPORT_DIR = os.environ.get("FINANCE_CSV_IMPORT_DIR", "/data/csv_import")
DEFAULT_EXPORT_DIR = os.environ.get("FINANCE_CSV_EXPORT_DIR", "/data/csv_export")

if "csv_import_dir" not in st.session_state:
    st.session_state.csv_import_dir = DEFAULT_IMPORT_DIR
if "csv_export_dir" not in st.session_state:
    st.session_state.csv_export_dir = DEFAULT_EXPORT_DIR

st.title("Import / Export")

if not st.session_state.get("db_ready"):
    st.warning("Open or create a database from the Home page first.")
    st.stop()

conn: Optional[sqlite3.Connection] = None
try:
    conn = db.connect(st.session_state.db_path)

    tab_import, tab_export = st.tabs(["Import", "Export"])

    with tab_import:
        st.subheader("CSV import")
        st.text_input("Import directory", value=st.session_state.csv_import_dir, key="csv_import_dir")
        st.caption("Upload a semicolon-separated CSV file.")

        uploaded = st.file_uploader("Choose a CSV file", type=["csv"], key="csv_import_file")
        if uploaded is not None:
            contents = uploaded.getvalue()
            decoded = csv_io.decode_csv_bytes(contents)
            headers, raw_rows = csv_io.read_csv_rows(decoded)

            missing = sorted(csv_io.REQUIRED_COLUMNS.difference(headers))
            if missing:
                st.error(f"Missing required columns: {', '.join(missing)}")
            else:
                st.write(f"Detected columns: {', '.join(headers)}")
                preview = csv_io.preview_rows(raw_rows)
                if preview:
                    st.dataframe(preview, use_container_width=True)

                parsed_rows, errors = csv_io.validate_rows(raw_rows)
                if errors:
                    st.error("Validation errors detected. Fix the CSV and try again.")
                    st.dataframe(
                        [{"row": err.row, "error": err.message} for err in errors],
                        use_container_width=True,
                    )
                elif not parsed_rows:
                    st.warning("No rows to import.")
                else:
                    st.success(f"Validated {len(parsed_rows)} rows. Ready to import.")
                    if st.button("Import CSV"):
                        with conn:
                            csv_io.insert_transactions(conn, parsed_rows)
                        st.success("Import completed.")
                        st.rerun()

    with tab_export:
        st.subheader("CSV export")
        st.text_input("Export directory", value=st.session_state.csv_export_dir, key="csv_export_dir")

        min_date, max_date = queries.get_date_bounds(conn)
        if min_date is None or max_date is None:
            st.warning("No transactions available to export.")
        else:
            start_default = st.session_state.get("export_start_date")
            end_default = st.session_state.get("export_end_date")
            if start_default is None:
                start_default = dt.date.fromisoformat(min_date)
            elif isinstance(start_default, str):
                start_default = dt.date.fromisoformat(start_default)
            if end_default is None:
                end_default = dt.date.fromisoformat(max_date)
            elif isinstance(end_default, str):
                end_default = dt.date.fromisoformat(end_default)

            date_col1, date_col2 = st.columns(2)
            with date_col1:
                start_date = st.date_input("Start date", value=start_default, key="export_start_date")
            with date_col2:
                end_date = st.date_input("End date", value=end_default, key="export_end_date")

            payer_options = queries.get_distinct_values(conn, "payer")
            payee_options = queries.get_distinct_values(conn, "payee")
            category_options = queries.get_distinct_values(conn, "category")
            subcategory_options = queries.get_distinct_values(conn, "subcategory")
            tag_options = tags.list_tags(conn)

            payer_filter = ui_widgets.typeahead_multi_select(
                "Payers", ["(empty)"] + payer_options, key="export_payers"
            )
            payee_filter = ui_widgets.typeahead_multi_select(
                "Payees", ["(empty)"] + payee_options, key="export_payees"
            )
            category_filter = ui_widgets.typeahead_multi_select(
                "Categories", category_options, key="export_categories"
            )
            subcategory_filter = ui_widgets.typeahead_multi_select(
                "Subcategories", ["(empty)"] + subcategory_options, key="export_subcategories"
            )
            tag_filter = ui_widgets.typeahead_multi_select("Tags", tag_options, key="export_tags")

            if st.button("Generate export"):
                if start_date > end_date:
                    st.error("Start date must be before end date.")
                else:
                    filters = {
                        "date_start": start_date.isoformat(),
                        "date_end": end_date.isoformat(),
                        "payers": _convert_empty_selection(payer_filter),
                        "payees": _convert_empty_selection(payee_filter),
                        "categories": category_filter,
                        "subcategories": _convert_empty_selection(subcategory_filter),
                        "tags": tag_filter,
                    }
                    rows = queries.list_transactions(conn, filters)
                    csv_text = csv_io.export_to_csv(rows)
                    filename = csv_io.default_export_filename()
                    st.session_state.export_csv_text = csv_text
                    st.session_state.export_csv_filename = filename
                    st.success(f"Prepared export with {len(rows)} rows.")

            csv_text = st.session_state.get("export_csv_text")
            filename = st.session_state.get("export_csv_filename")
            if csv_text and filename:
                st.download_button(
                    "Download CSV",
                    data=csv_text,
                    file_name=filename,
                    mime="text/csv",
                )

                save_copy = st.checkbox("Save copy to export directory", key="export_save_copy")
                if save_copy:
                    override_name = st.text_input(
                        "Filename", value=filename, key="export_filename_override"
                    )
                    if st.button("Save export"):
                        try:
                            saved_path = csv_io.save_export_csv(
                                csv_text, st.session_state.csv_export_dir, override_name
                            )
                            st.success(f"Saved to {saved_path}")
                        except OSError as exc:
                            st.error(f"Failed to save export: {exc}")

finally:
    if conn is not None:
        conn.close()
