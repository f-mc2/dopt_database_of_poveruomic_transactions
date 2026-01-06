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



conn: Optional[sqlite3.Connection] = None
try:
    conn = db.connect(st.session_state.db_path)

    payer_options = queries.get_distinct_values(conn, "payer")
    payee_options = queries.get_distinct_values(conn, "payee")
    payment_type_options = queries.get_distinct_values(conn, "payment_type")
    category_options = queries.get_distinct_values(conn, "category")
    subcategory_options = queries.get_distinct_values(conn, "subcategory")
    tag_options = tags.list_tags(conn)

    st.subheader("Search")
    search_text = st.text_input("Search transactions", key="tx_search")

    transactions = queries.list_transactions(conn, {"search": search_text})

    st.subheader("Results")
    if not transactions:
        st.info("No transactions match the current search.")
    else:
        table_height = 720
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
                    "payment_type": row["payment_type"] or "",
                    "category": row["category"],
                    "subcategory": row["subcategory"] or "",
                    "tags": row["tags"] or "",
                    "notes": row["notes"] or "",
                }
            )
        st.dataframe(table_rows, use_container_width=True, height=table_height)

    st.subheader("Add transaction")
    with st.form("add_transaction"):
        today = dt.date.today()
        form_date_payment = st.date_input("Payment date", value=today, key="add_date_payment")
        form_date_application = st.date_input(
            "Application date", value=today, key="add_date_application"
        )
        form_amount = st.text_input("Amount", value="0.00", key="add_amount")

        form_payer = ui_widgets.select_or_add(
            "Payer",
            payer_options,
            key="add_payer",
            allow_empty=True,
        )
        form_payee = ui_widgets.select_or_add(
            "Payee",
            payee_options,
            key="add_payee",
            allow_empty=True,
        )
        form_payment_type = ui_widgets.select_or_add(
            "Payment type",
            payment_type_options,
            key="add_payment_type",
            allow_empty=True,
        )
        form_category = ui_widgets.select_or_add(
            "Category",
            category_options,
            key="add_category",
            allow_empty=False,
        )
        form_subcategory = ui_widgets.select_or_add(
            "Subcategory",
            subcategory_options,
            key="add_subcategory",
            allow_empty=True,
        )
        form_notes = st.text_area("Notes", key="add_notes")

        form_tags = st.multiselect(
            "Tags",
            options=tag_options,
            default=[],
            key="add_tags",
        )
        new_tags_raw = st.text_input(
            "Add new tags (comma-separated)",
            key="add_tags_new",
        )

        submitted_new = st.form_submit_button("Add transaction")

    if submitted_new:
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
        payment_type_value = normalize_optional(form_payment_type, lower=True)
        subcategory_value = normalize_optional(form_subcategory, lower=True)
        notes_value_clean = normalize_optional(form_notes)

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
            timestamp = dt.datetime.now().isoformat(timespec="seconds")
            with conn:
                transaction_id = queries.insert_transaction(
                    conn,
                    date_payment=form_date_payment.isoformat(),
                    date_application=form_date_application.isoformat(),
                    amount_cents=amount_cents,
                    payer=payer_value,
                    payee=payee_value,
                    payment_type=payment_type_value,
                    category=category_value,
                    subcategory=subcategory_value,
                    notes=notes_value_clean,
                    created_at=timestamp,
                    updated_at=timestamp,
                )
                if combined_tags:
                    tags.set_transaction_tags(conn, transaction_id, combined_tags)
            st.success("Transaction added.")
            st.rerun()

    st.subheader("Edit or delete")
    if not transactions:
        st.info("No transactions available for editing.")
    else:
        tx_map = {int(row["id"]): row for row in transactions}
        tx_ids = list(tx_map.keys())

        def _format_tx_id(value: int) -> str:
            row = tx_map.get(value)
            if row is None:
                return str(value)
            amount_value = amounts.format_cents(int(row["amount_cents"]))
            return (
                f"{value} • pay {row['date_payment']} • app {row['date_application']} • {amount_value}"
            )

        selected_id = st.selectbox(
            "Transaction ID",
            tx_ids,
            format_func=_format_tx_id,
            key="tx_edit_id",
        )
        selected_row = queries.get_transaction(conn, selected_id)
        if selected_row is None:
            st.warning("Selected transaction is not available.")
        else:
            current_tags = tags.get_tags_for_transaction(conn, selected_id)
            st.write(
                f"Amount: {amounts.format_cents(int(selected_row['amount_cents']))} | "
                f"Category: {selected_row['category']} | "
                f"Subcategory: {selected_row['subcategory'] or '(empty)'}"
            )

            with st.form(f"edit_tx_{selected_id}"):
                form_date_payment = st.date_input(
                    "Payment date",
                    value=dt.date.fromisoformat(selected_row["date_payment"]),
                    key=f"tx_date_payment_{selected_id}",
                )
                form_date_application = st.date_input(
                    "Application date",
                    value=dt.date.fromisoformat(selected_row["date_application"]),
                    key=f"tx_date_application_{selected_id}",
                )
                form_amount = st.text_input(
                    "Amount",
                    value=amounts.format_cents(int(selected_row["amount_cents"])),
                    key=f"tx_amount_{selected_id}",
                )
                form_payer = ui_widgets.select_or_add(
                    "Payer",
                    payer_options,
                    key=f"tx_payer_{selected_id}",
                    allow_empty=True,
                    current=selected_row["payer"],
                )
                form_payee = ui_widgets.select_or_add(
                    "Payee",
                    payee_options,
                    key=f"tx_payee_{selected_id}",
                    allow_empty=True,
                    current=selected_row["payee"],
                )
                form_payment_type = ui_widgets.select_or_add(
                    "Payment type",
                    payment_type_options,
                    key=f"tx_payment_type_{selected_id}",
                    allow_empty=True,
                    current=selected_row["payment_type"],
                )
                form_category = ui_widgets.select_or_add(
                    "Category",
                    category_options,
                    key=f"tx_category_{selected_id}",
                    allow_empty=False,
                    current=selected_row["category"],
                )
                form_subcategory = ui_widgets.select_or_add(
                    "Subcategory",
                    subcategory_options,
                    key=f"tx_subcategory_{selected_id}",
                    allow_empty=True,
                    current=selected_row["subcategory"],
                )
                form_notes = st.text_area(
                    "Notes",
                    value=selected_row["notes"] or "",
                    key=f"tx_notes_{selected_id}",
                )

                form_tags = st.multiselect(
                    "Tags",
                    options=tag_options,
                    default=current_tags,
                    key=f"tx_tags_{selected_id}",
                )
                new_tags_raw = st.text_input(
                    "Add new tags (comma-separated)",
                    key=f"tx_new_tags_{selected_id}",
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

                payment_type_value = normalize_optional(form_payment_type, lower=True)
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
                            transaction_id=selected_id,
                            date_payment=form_date_payment.isoformat(),
                            date_application=form_date_application.isoformat(),
                            amount_cents=amount_cents,
                            payer=payer_value,
                            payee=payee_value,
                            payment_type=payment_type_value,
                            category=category_value,
                            subcategory=subcategory_value,
                            notes=notes_value,
                            updated_at=updated_at,
                        )
                        tags.set_transaction_tags(conn, selected_id, combined_tags)
                    st.success("Transaction updated.")
                    st.rerun()

            st.divider()
            confirm_delete = st.checkbox("Confirm delete", key=f"tx_delete_confirm_{selected_id}")
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
