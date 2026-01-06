import datetime as dt
from typing import List, Optional

import sqlite3
import streamlit as st

from src import amounts, db, queries, tags, ui_widgets


st.title("Transactions")

if not st.session_state.get("db_ready"):
    st.warning("Open or create a database from the Home page first.")
    st.stop()


def normalize_optional(value: Optional[str], lower: bool = False) -> Optional[str]:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    return cleaned.lower() if lower else cleaned


def normalize_required(value: Optional[str], lower: bool = False) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        raise ValueError("Value is required")
    return cleaned.lower() if lower else cleaned


def convert_empty_selection(selected: List[str]) -> List[Optional[str]]:
    return [None if item == "(empty)" else item for item in selected]


conn: Optional[sqlite3.Connection] = None
try:
    conn = db.connect(st.session_state.db_path)

    payer_options = queries.get_distinct_values(conn, "payer")
    payee_options = queries.get_distinct_values(conn, "payee")
    category_options = queries.get_distinct_values(conn, "category")
    subcategory_options = queries.get_distinct_values(conn, "subcategory")
    tag_options = tags.list_tags(conn)

    date_field_labels = {
        "Payment date": "date_payment",
        "Application date": "date_application",
    }
    selected_label = st.selectbox(
        "Filter by date field",
        list(date_field_labels.keys()),
        key="tx_date_field",
    )
    date_field = date_field_labels[selected_label]

    min_date, max_date = queries.get_date_bounds(conn, date_field)
    today = dt.date.today()
    start_default = dt.date.fromisoformat(min_date) if min_date else today
    end_default = dt.date.fromisoformat(max_date) if max_date else today

    st.subheader("Filters")
    date_col1, date_col2 = st.columns(2)
    with date_col1:
        start_date = st.date_input(
            "Start date", value=start_default, key=f"tx_filter_start_{date_field}"
        )
    with date_col2:
        end_date = st.date_input("End date", value=end_default, key=f"tx_filter_end_{date_field}")

    search_text = st.text_input("Search text", key="tx_filter_search")

    payer_filter = ui_widgets.typeahead_multi_select(
        "Payers", ["(empty)"] + payer_options, key="tx_filter_payers"
    )
    payee_filter = ui_widgets.typeahead_multi_select(
        "Payees", ["(empty)"] + payee_options, key="tx_filter_payees"
    )
    category_filter = ui_widgets.typeahead_multi_select(
        "Categories", category_options, key="tx_filter_categories"
    )
    subcategory_filter = ui_widgets.typeahead_multi_select(
        "Subcategories", ["(empty)"] + subcategory_options, key="tx_filter_subcategories"
    )
    tag_filter = ui_widgets.typeahead_multi_select("Tags", tag_options, key="tx_filter_tags")

    filters = {
        "date_field": date_field,
        "date_start": start_date.isoformat() if start_date else None,
        "date_end": end_date.isoformat() if end_date else None,
        "payers": convert_empty_selection(payer_filter),
        "payees": convert_empty_selection(payee_filter),
        "categories": category_filter,
        "subcategories": convert_empty_selection(subcategory_filter),
        "tags": tag_filter,
        "search": search_text,
    }

    transactions = queries.list_transactions(conn, filters)

    st.subheader("Results")
    if not transactions:
        st.info("No transactions match the current filters.")
    else:
        table_rows = []
        for row in transactions:
            table_rows.append(
                {
                    "id": row["id"],
                    "date_payment": row["date_payment"],
                    "date_application": row["date_application"],
                    "amount": amounts.format_cents(int(row["amount_cents"])),
                    "payer": row["payer"] or "",
                    "payee": row["payee"] or "",
                    "category": row["category"],
                    "subcategory": row["subcategory"] or "",
                    "tags": row["tags"] or "",
                    "notes": row["notes"] or "",
                }
            )
        st.dataframe(table_rows, use_container_width=True)

    st.subheader("Edit or delete")
    for row in transactions:
        tx_id = int(row["id"])
        expander_label = (
            f"Transaction {tx_id} • pay {row['date_payment']} • app {row['date_application']}"
        )
        with st.expander(expander_label):
            current_tags = row["tags"].split(",") if row["tags"] else []
            st.write(
                f"Amount: {amounts.format_cents(int(row['amount_cents']))} | "
                f"Category: {row['category']} | Subcategory: {row['subcategory'] or '(empty)'}"
            )

            with st.form(f"edit_tx_{tx_id}"):
                form_date_payment = st.date_input(
                    "Payment date",
                    value=dt.date.fromisoformat(row["date_payment"]),
                    key=f"tx_date_payment_{tx_id}",
                )
                form_date_application = st.date_input(
                    "Application date",
                    value=dt.date.fromisoformat(row["date_application"]),
                    key=f"tx_date_application_{tx_id}",
                )
                form_amount = st.text_input(
                    "Amount",
                    value=amounts.format_cents(int(row["amount_cents"])),
                    key=f"tx_amount_{tx_id}",
                )
                form_payer = ui_widgets.select_or_add(
                    "Payer",
                    payer_options,
                    key=f"tx_payer_{tx_id}",
                    allow_empty=True,
                    current=row["payer"],
                )
                form_payee = ui_widgets.select_or_add(
                    "Payee",
                    payee_options,
                    key=f"tx_payee_{tx_id}",
                    allow_empty=True,
                    current=row["payee"],
                )
                form_category = ui_widgets.select_or_add(
                    "Category",
                    category_options,
                    key=f"tx_category_{tx_id}",
                    allow_empty=False,
                    current=row["category"],
                )
                form_subcategory = ui_widgets.select_or_add(
                    "Subcategory",
                    subcategory_options,
                    key=f"tx_subcategory_{tx_id}",
                    allow_empty=True,
                    current=row["subcategory"],
                )
                form_notes = st.text_area(
                    "Notes",
                    value=row["notes"] or "",
                    key=f"tx_notes_{tx_id}",
                )

                form_tags = st.multiselect(
                    "Tags",
                    options=tag_options,
                    default=current_tags,
                    key=f"tx_tags_{tx_id}",
                )
                new_tags_raw = st.text_input(
                    "Add new tags (comma-separated)",
                    key=f"tx_new_tags_{tx_id}",
                )

                submitted = st.form_submit_button("Save changes")

            if submitted:
                errors: List[str] = []
                try:
                    amount_cents = amounts.parse_amount_to_cents(form_amount)
                except ValueError as exc:
                    errors.append(str(exc))

                try:
                    category_value = normalize_required(form_category, lower=True)
                except ValueError as exc:
                    errors.append(str(exc))
                    category_value = ""

                payer_value = normalize_optional(form_payer)
                payee_value = normalize_optional(form_payee)
                subcategory_value = normalize_optional(form_subcategory, lower=True)
                notes_value = normalize_optional(form_notes)

                if payer_value and payee_value and payer_value == payee_value:
                    errors.append("Payer and payee must be different")

                combined_tags = []
                for tag_name in list(form_tags) + tags.parse_tags(new_tags_raw):
                    normalized = tags.normalize_tag(tag_name)
                    if not normalized or normalized in combined_tags:
                        continue
                    combined_tags.append(normalized)

                if errors:
                    st.error("; ".join(errors))
                else:
                    updated_at = dt.datetime.now().isoformat(timespec="seconds")
                    with conn:
                        queries.update_transaction(
                            conn,
                            transaction_id=tx_id,
                            date_payment=form_date_payment.isoformat(),
                            date_application=form_date_application.isoformat(),
                            amount_cents=amount_cents,
                            payer=payer_value,
                            payee=payee_value,
                            category=category_value,
                            subcategory=subcategory_value,
                            notes=notes_value,
                            updated_at=updated_at,
                        )
                        tags.set_transaction_tags(conn, tx_id, combined_tags)
                    st.success("Transaction updated.")
                    st.rerun()

            st.divider()
            confirm_delete = st.checkbox("Confirm delete", key=f"tx_delete_confirm_{tx_id}")
            if st.button("Delete transaction", key=f"tx_delete_{tx_id}"):
                if not confirm_delete:
                    st.warning("Please confirm deletion.")
                else:
                    with conn:
                        queries.delete_transaction(conn, tx_id)
                    st.success("Transaction deleted.")
                    st.rerun()

finally:
    if conn is not None:
        conn.close()
