import datetime as dt
from typing import List, Optional

import pandas as pd
import sqlite3
import streamlit as st

from src import amounts, db, queries, session_state, tags, ui_widgets

session_state.ensure_db_session_state()
ui_widgets.render_sidebar_nav()

st.title("Transactions")

if not st.session_state.get("db_ready"):
    st.warning("Open or create a database from the Home page first.")
    st.stop()

DATE_INPUT_MIN = dt.date(1900, 1, 1)
DATE_INPUT_MAX = dt.date(2100, 12, 31)


def _normalize_optional(value: Optional[str], lower: bool = True) -> Optional[str]:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    return cleaned.lower() if lower else cleaned


def _format_tx_label(row: sqlite3.Row) -> str:
    amount_value = amounts.format_cents(int(row["amount_cents"]))
    return (
        f"{row['id']} • pay {row['date_payment']} • app {row['date_application']} • {amount_value}"
    )


conn: Optional[sqlite3.Connection] = None
try:
    conn = db.connect(st.session_state.db_path)

    payer_options = queries.get_distinct_values(conn, "payer")
    payee_options = queries.get_distinct_values(conn, "payee")
    payment_type_options = queries.get_distinct_values(conn, "payment_type")
    category_options = queries.get_distinct_values(conn, "category")
    subcategory_pairs = queries.get_category_subcategory_pairs(conn)
    tag_options = tags.list_tags(conn)

    search_query = st.text_input(
        "Search",
        key="tx_search",
        placeholder="payer, payee, category, subcategory, tags, notes",
    )
    all_columns = [
        "id",
        "date_payment",
        "date_application",
        "amount",
        "payer",
        "payee",
        "payment_type",
        "category",
        "subcategory",
        "tags",
        "notes",
    ]
    visible_columns = st.multiselect(
        "Visible columns",
        options=all_columns,
        default=all_columns,
        key="tx_visible_columns",
    )
    table_container = st.container()

    date_field = "date_application"
    min_date, max_date = queries.get_date_bounds(conn, date_field)
    today = dt.date.today()
    date_min_limit = dt.date.fromisoformat(min_date) if min_date else None
    date_max_limit = dt.date.fromisoformat(max_date) if max_date else None
    default_start = date_min_limit or today
    default_end = date_max_limit or today

    st.subheader("Filters")
    with st.form("tx_filters"):
        date_col1, date_col2 = st.columns(2)
        with date_col1:
            start_date = st.date_input(
                "Start date",
                value=default_start,
                min_value=date_min_limit,
                max_value=date_max_limit,
                key="tx_filter_start",
            )
        with date_col2:
            end_date = st.date_input(
                "End date",
                value=default_end,
                min_value=date_min_limit,
                max_value=date_max_limit,
                key="tx_filter_end",
            )

        payer_filter = ui_widgets.multiselect_existing(
            "Payers", payer_options, key="tx_filter_payers"
        )
        include_missing_payer = st.checkbox(
            "Include missing payer", key="tx_filter_missing_payer"
        )
        payee_filter = ui_widgets.multiselect_existing(
            "Payees", payee_options, key="tx_filter_payees"
        )
        include_missing_payee = st.checkbox(
            "Include missing payee", key="tx_filter_missing_payee"
        )
        payment_type_filter = ui_widgets.multiselect_existing(
            "Payment types", payment_type_options, key="tx_filter_payment_types"
        )
        include_missing_payment_type = st.checkbox(
            "Include missing payment type", key="tx_filter_missing_payment_type"
        )

        category_filter = ui_widgets.multiselect_existing(
            "Categories", category_options, key="tx_filter_categories"
        )
        sub_labels, label_map = ui_widgets.subcategory_label_map(
            subcategory_pairs, category_filter
        )
        subcategory_filter_labels = ui_widgets.multiselect_existing(
            "Subcategories", sub_labels, key="tx_filter_subcategories"
        )
        subcategory_filter = [label_map[label] for label in subcategory_filter_labels]

        tag_filter = ui_widgets.tags_filter("Tags", tag_options, key="tx_filter_tags")

        st.form_submit_button("Apply filters")

    error_message = None
    if start_date > end_date:
        error_message = "Start date must be before end date."
        transactions: List[sqlite3.Row] = []
    else:
        filters = {
            "date_field": date_field,
            "date_start": start_date.isoformat(),
            "date_end": end_date.isoformat(),
            "search": search_query,
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

        transactions = queries.list_transactions(
            conn,
            filters,
        )

    with table_container:
        if error_message:
            st.error(error_message)
        elif not transactions:
            st.info("No transactions match the current filters.")
        else:
            display_rows = []
            for row in transactions:
                display_rows.append(
                    {
                        "id": row["id"],
                        "date_payment": row["date_payment"],
                        "date_application": row["date_application"],
                        "amount": amounts.format_cents(int(row["amount_cents"])),
                        "payer": row["payer"] or "",
                        "payee": row["payee"] or "",
                        "payment_type": row["payment_type"] or "",
                        "category": row["category"],
                        "subcategory": row["subcategory"] or "",
                        "tags": row["tags"] or "",
                        "notes": row["notes"] or "",
                    }
                )

            ordered_columns = [col for col in all_columns if col in visible_columns]
            df = pd.DataFrame(display_rows)
            if ordered_columns:
                df = df[ordered_columns]
            display_columns = ordered_columns or list(df.columns)
            table_width = max(900, len(display_columns) * 140)
            st.dataframe(df, width=table_width, height=520)
            st.caption("Default order is date_application desc; click column headers to sort.")

    st.divider()
    st.subheader("Add transaction")
    with st.form("add_transaction"):
        date_payment = st.date_input(
            "Payment date",
            value=today,
            min_value=DATE_INPUT_MIN,
            max_value=DATE_INPUT_MAX,
            key="add_date_payment",
        )
        copy_dates = st.checkbox(
            "Use payment date for application date",
            value=True,
            key="add_copy_dates",
        )
        if copy_dates:
            st.date_input(
                "Application date",
                value=date_payment,
                min_value=DATE_INPUT_MIN,
                max_value=DATE_INPUT_MAX,
                key="add_date_application",
                disabled=True,
            )
            date_application = date_payment
        else:
            date_application = st.date_input(
                "Application date",
                value=today,
                min_value=DATE_INPUT_MIN,
                max_value=DATE_INPUT_MAX,
                key="add_date_application",
            )
        form_amount = st.text_input("Amount", value="0.00", key="add_amount")

        payer_value, _ = ui_widgets.select_or_create(
            "Payer",
            payer_options,
            key="add_payer",
            allow_empty=True,
        )
        payee_value, _ = ui_widgets.select_or_create(
            "Payee",
            payee_options,
            key="add_payee",
            allow_empty=True,
        )
        payment_type_value, _ = ui_widgets.select_or_create(
            "Payment type",
            payment_type_options,
            key="add_payment_type",
            allow_empty=True,
        )
        category_value, _ = ui_widgets.select_or_create(
            "Category",
            category_options,
            key="add_category",
            allow_empty=False,
        )
        subcategory_options = (
            queries.get_subcategories_for_category(conn, category_value)
            if category_value
            else []
        )
        subcategory_value, _ = ui_widgets.select_or_create(
            "Subcategory",
            subcategory_options,
            key="add_subcategory",
            allow_empty=True,
        )
        form_notes = st.text_area("Notes", key="add_notes")

        selected_tags, new_tag = ui_widgets.tags_assign(
            "Tags",
            tag_options,
            key="add_tags",
        )

        submitted_new = st.form_submit_button("Add transaction")

    if submitted_new:
        errors: List[str] = []
        try:
            amount_cents = amounts.parse_amount_to_cents(form_amount)
        except ValueError as exc:
            errors.append(str(exc))
            amount_cents = 0

        notes_value = _normalize_optional(form_notes, lower=False)

        if not category_value:
            errors.append("Category is required")
        if not payer_value and not payee_value:
            errors.append("Payer or payee is required")
        if payer_value and payee_value and payer_value == payee_value:
            errors.append("Payer and payee must be different")

        combined_tags = list(selected_tags)
        if new_tag.strip():
            try:
                normalized = tags.normalize_tag(new_tag)
            except ValueError as exc:
                errors.append(str(exc))
            else:
                if normalized not in combined_tags:
                    combined_tags.append(normalized)

        if errors:
            st.error("; ".join(errors))
        else:
            with conn:
                transaction_id = queries.insert_transaction(
                    conn,
                    date_payment=date_payment.isoformat(),
                    date_application=date_application.isoformat(),
                    amount_cents=amount_cents,
                    payer=_normalize_optional(payer_value),
                    payee=_normalize_optional(payee_value),
                    payment_type=_normalize_optional(payment_type_value),
                    category=category_value,
                    subcategory=_normalize_optional(subcategory_value),
                    notes=notes_value,
                )
                tags.set_transaction_tags(conn, transaction_id, combined_tags)
            st.success("Transaction added.")
            st.rerun()

    st.divider()
    st.subheader("Edit or delete")
    if not transactions:
        st.info("No transactions available for editing.")
    else:
        tx_map = {int(row["id"]): row for row in transactions}
        tx_ids = list(tx_map.keys())
        selected_id = st.selectbox(
            "Transaction",
            tx_ids,
            format_func=lambda value: _format_tx_label(tx_map[value]),
            key="tx_edit_id",
        )
        selected_row = queries.get_transaction(conn, selected_id)
        if selected_row is None:
            st.warning("Selected transaction is not available.")
        else:
            current_tags = tags.get_tags_for_transaction(conn, selected_id)
            if f"edit_tags_{selected_id}_selected" not in st.session_state:
                st.session_state[f"edit_tags_{selected_id}_selected"] = current_tags

            with st.form(f"edit_tx_{selected_id}"):
                edit_date_payment = st.date_input(
                    "Payment date",
                    value=dt.date.fromisoformat(selected_row["date_payment"]),
                    min_value=DATE_INPUT_MIN,
                    max_value=DATE_INPUT_MAX,
                    key=f"edit_date_payment_{selected_id}",
                )
                copy_edit_dates = st.checkbox(
                    "Use payment date for application date",
                    value=(selected_row["date_payment"] == selected_row["date_application"]),
                    key=f"edit_copy_dates_{selected_id}",
                )
                if copy_edit_dates:
                    st.date_input(
                        "Application date",
                        value=edit_date_payment,
                        min_value=DATE_INPUT_MIN,
                        max_value=DATE_INPUT_MAX,
                        key=f"edit_date_application_{selected_id}",
                        disabled=True,
                    )
                    edit_date_application = edit_date_payment
                else:
                    edit_date_application = st.date_input(
                        "Application date",
                        value=dt.date.fromisoformat(selected_row["date_application"]),
                        min_value=DATE_INPUT_MIN,
                        max_value=DATE_INPUT_MAX,
                        key=f"edit_date_application_{selected_id}",
                    )
                edit_amount = st.text_input(
                    "Amount",
                    value=amounts.format_cents(int(selected_row["amount_cents"])),
                    key=f"edit_amount_{selected_id}",
                )

                payer_value, _ = ui_widgets.select_or_create(
                    "Payer",
                    payer_options,
                    key=f"edit_payer_{selected_id}",
                    value=selected_row["payer"],
                    allow_empty=True,
                )
                payee_value, _ = ui_widgets.select_or_create(
                    "Payee",
                    payee_options,
                    key=f"edit_payee_{selected_id}",
                    value=selected_row["payee"],
                    allow_empty=True,
                )
                payment_type_value, _ = ui_widgets.select_or_create(
                    "Payment type",
                    payment_type_options,
                    key=f"edit_payment_type_{selected_id}",
                    value=selected_row["payment_type"],
                    allow_empty=True,
                )
                category_value, _ = ui_widgets.select_or_create(
                    "Category",
                    category_options,
                    key=f"edit_category_{selected_id}",
                    value=selected_row["category"],
                    allow_empty=False,
                )
                subcategory_options = (
                    queries.get_subcategories_for_category(conn, category_value)
                    if category_value
                    else []
                )
                subcategory_value, _ = ui_widgets.select_or_create(
                    "Subcategory",
                    subcategory_options,
                    key=f"edit_subcategory_{selected_id}",
                    value=selected_row["subcategory"],
                    allow_empty=True,
                )
                edit_notes = st.text_area(
                    "Notes",
                    value=selected_row["notes"] or "",
                    key=f"edit_notes_{selected_id}",
                )

                selected_tags, new_tag = ui_widgets.tags_assign(
                    "Tags",
                    tag_options,
                    key=f"edit_tags_{selected_id}",
                )

                submitted = st.form_submit_button("Save changes")

            if submitted:
                errors: List[str] = []
                try:
                    amount_cents = amounts.parse_amount_to_cents(edit_amount)
                except ValueError as exc:
                    errors.append(str(exc))
                    amount_cents = 0

                if not category_value:
                    errors.append("Category is required")
                if not payer_value and not payee_value:
                    errors.append("Payer or payee is required")
                if payer_value and payee_value and payer_value == payee_value:
                    errors.append("Payer and payee must be different")

                notes_value = _normalize_optional(edit_notes, lower=False)

                combined_tags = list(selected_tags)
                if new_tag.strip():
                    try:
                        normalized = tags.normalize_tag(new_tag)
                    except ValueError as exc:
                        errors.append(str(exc))
                    else:
                        if normalized not in combined_tags:
                            combined_tags.append(normalized)

                if errors:
                    st.error("; ".join(errors))
                else:
                    with conn:
                        queries.update_transaction(
                            conn,
                            transaction_id=selected_id,
                            date_payment=edit_date_payment.isoformat(),
                            date_application=edit_date_application.isoformat(),
                            amount_cents=amount_cents,
                            payer=_normalize_optional(payer_value),
                            payee=_normalize_optional(payee_value),
                            payment_type=_normalize_optional(payment_type_value),
                            category=category_value,
                            subcategory=_normalize_optional(subcategory_value),
                            notes=notes_value,
                        )
                        tags.set_transaction_tags(conn, selected_id, combined_tags)
                    st.success("Transaction updated.")
                    st.rerun()

            st.divider()
            confirm_delete = st.checkbox(
                "Confirm delete",
                key=f"tx_delete_confirm_{selected_id}",
            )
            if st.button("Delete transaction", key=f"tx_delete_{selected_id}"):
                if not confirm_delete:
                    st.warning("Please confirm deletion.")
                else:
                    with conn:
                        queries.delete_transaction(conn, selected_id)
                    st.success("Transaction deleted.")
                    st.rerun()

finally:
    if conn is not None:
        conn.close()
