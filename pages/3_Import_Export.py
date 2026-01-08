import datetime as dt
from pathlib import Path
from typing import Optional

import sqlite3
import streamlit as st

from src import csv_io, db, queries, session_state, tags, ui_widgets

session_state.ensure_db_session_state()

st.title("Import / Export")

if not st.session_state.get("db_ready"):
    st.warning("Open or create a database from the Home page first.")
    st.stop()

conn: Optional[sqlite3.Connection] = None
try:
    conn = db.connect(st.session_state.db_path)

    tab_import, tab_export, tab_backup = st.tabs(["Import", "Export", "Backup"])

    with tab_import:
        st.subheader("CSV import")
        st.text_input(
            "Import directory",
            value=st.session_state.csv_import_dir,
            disabled=True,
        )
        st.caption("Upload a semicolon-separated CSV file. Headers are trimmed and case-insensitive.")

        uploaded = st.file_uploader("Choose a CSV file", type=["csv"], key="csv_import_file")
        if uploaded is not None:
            contents = uploaded.getvalue()
            decoded = csv_io.decode_csv_bytes(contents)
            try:
                headers, raw_rows = csv_io.read_csv_rows(decoded)
            except ValueError as exc:
                st.error(str(exc))
                headers, raw_rows = [], []

            header_set = set(headers)
            missing = sorted(csv_io.REQUIRED_COLUMNS.difference(header_set))
            missing_dates = not header_set.intersection(csv_io.DATE_COLUMNS)
            missing_parties = not header_set.intersection(csv_io.PAYER_PAYEE_COLUMNS)

            if missing:
                st.error(f"Missing required columns: {', '.join(missing)}")
            if missing_dates:
                st.error("CSV must include date_payment or date_application column.")
            if missing_parties:
                st.error("CSV must include payer or payee column.")

            if headers and not missing and not missing_dates and not missing_parties:
                st.write(f"Detected columns: {', '.join(headers)}")
                preview = csv_io.preview_rows(raw_rows)
                if preview:
                    st.dataframe(preview, width="stretch")

                parsed_rows, errors = csv_io.validate_rows(raw_rows)
                if errors:
                    st.error("Validation errors detected. Fix the CSV and try again.")
                    st.dataframe(
                        [{"row": err.row, "error": err.message} for err in errors],
                        width="stretch",
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
        st.text_input(
            "Export directory",
            value=st.session_state.csv_export_dir,
            disabled=True,
        )

        date_field_labels = {
            "Application date": "date_application",
            "Payment date": "date_payment",
        }
        selected_label = st.selectbox(
            "Date field for range",
            list(date_field_labels.keys()),
            index=0,
            key="export_date_field",
        )
        date_field = date_field_labels[selected_label]

        min_date, max_date = queries.get_date_bounds(conn, date_field)
        if min_date is None or max_date is None:
            st.warning("No transactions available to export.")
        else:
            date_min_limit = dt.date.fromisoformat(min_date)
            date_max_limit = dt.date.fromisoformat(max_date)
            start_default = date_min_limit
            end_default = date_max_limit

            date_col1, date_col2 = st.columns(2)
            with date_col1:
                start_date = st.date_input(
                    "Start date",
                    value=start_default,
                    min_value=date_min_limit,
                    max_value=date_max_limit,
                    key="export_start_date",
                )
            with date_col2:
                end_date = st.date_input(
                    "End date",
                    value=end_default,
                    min_value=date_min_limit,
                    max_value=date_max_limit,
                    key="export_end_date",
                )

            payer_options = queries.get_distinct_values(conn, "payer")
            payee_options = queries.get_distinct_values(conn, "payee")
            payment_type_options = queries.get_distinct_values(conn, "payment_type")
            category_options = queries.get_distinct_values(conn, "category")
            subcategory_pairs = queries.get_category_subcategory_pairs(conn)
            tag_options = tags.list_tags(conn)

            payer_filter = ui_widgets.multiselect_existing(
                "Payers", payer_options, key="export_payers"
            )
            include_missing_payer = st.checkbox(
                "Include missing payer", key="export_missing_payer"
            )
            payee_filter = ui_widgets.multiselect_existing(
                "Payees", payee_options, key="export_payees"
            )
            include_missing_payee = st.checkbox(
                "Include missing payee", key="export_missing_payee"
            )
            payment_type_filter = ui_widgets.multiselect_existing(
                "Payment types", payment_type_options, key="export_payment_types"
            )
            include_missing_payment_type = st.checkbox(
                "Include missing payment type", key="export_missing_payment_type"
            )
            category_filter = ui_widgets.multiselect_existing(
                "Categories", category_options, key="export_categories"
            )
            subcategory_candidates = (
                [pair for pair in subcategory_pairs if pair[0] in category_filter]
                if category_filter
                else subcategory_pairs
            )
            sub_labels = []
            label_map = {}
            for category, subcategory in subcategory_candidates:
                label = f"{category} / {subcategory}"
                label_map[label] = (category, subcategory)
                sub_labels.append(label)
            subcategory_filter_labels = ui_widgets.multiselect_existing(
                "Subcategories", sub_labels, key="export_subcategories"
            )
            subcategory_filter = [label_map[label] for label in subcategory_filter_labels]

            tag_filter = ui_widgets.tags_filter("Tags", tag_options, key="export_tags")

            if st.button("Generate export"):
                if start_date > end_date:
                    st.error("Start date must be before end date.")
                else:
                    filters = {
                        "date_field": date_field,
                        "date_start": start_date.isoformat(),
                        "date_end": end_date.isoformat(),
                        "payers": payer_filter,
                        "payees": payee_filter,
                        "payment_types": payment_type_filter,
                        "categories": category_filter,
                        "subcategory_pairs": subcategory_filter,
                        "tags": tag_filter,
                        "include_missing_payer": include_missing_payer,
                        "include_missing_payee": include_missing_payee,
                        "include_missing_payment_type": include_missing_payment_type,
                    }
                    rows = queries.list_transactions(conn, filters, sort_by=date_field)
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

    with tab_backup:
        st.subheader("Backup")
        st.text_input(
            "Backup directory",
            value=st.session_state.db_backup_dir,
            disabled=True,
        )
        confirm_backup = st.checkbox("Confirm backup", key="backup_confirm")
        if st.button("Create backup"):
            if not confirm_backup:
                st.warning("Please confirm backup.")
            else:
                backup_dir = Path(st.session_state.db_backup_dir)
                backup_dir.mkdir(parents=True, exist_ok=True)
                timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"finance_backup_{timestamp}.db"
                target_path = backup_dir / filename
                try:
                    db.backup_db(conn, str(target_path))
                    st.success(f"Backup created: {target_path}")
                except sqlite3.Error as exc:
                    st.error(f"Backup failed: {exc}")

finally:
    if conn is not None:
        conn.close()
