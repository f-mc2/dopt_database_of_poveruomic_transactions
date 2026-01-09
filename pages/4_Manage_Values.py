import sqlite3
from typing import Optional

import streamlit as st

from src import db, session_state, tags, ui_widgets, values

st.set_page_config(
    page_title="Manage Values",
    page_icon="\U0001F4B6",
    initial_sidebar_state="auto",
    layout="wide",
)

session_state.ensure_db_session_state()
ui_widgets.render_sidebar_nav()

st.title("Manage Values")

if not st.session_state.get("db_ready"):
    st.warning("Open or create a database from the Home page first.")
    st.stop()

conn: Optional[sqlite3.Connection] = None
try:
    conn = db.connect(st.session_state.db_path)

    st.subheader("Payer")
    payer_counts = values.list_value_counts(conn, "payer")
    if not payer_counts:
        st.info("No payer values found.")
    else:
        payer_options = [value for value, _ in payer_counts]
        payer_selection = ui_widgets.select_existing(
            "Select payer",
            payer_options,
            key="mv_payer_select",
            allow_empty=False,
        )
        if payer_selection:
            with st.form("mv_payer_rename"):
                new_value = st.text_input("Rename payer to")
                confirm = st.checkbox("Confirm rename/merge")
                submit = st.form_submit_button("Rename")
            if submit:
                try:
                    normalized = values.normalize_finance_value(new_value)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    if normalized == payer_selection:
                        st.warning("New value matches the current value.")
                    else:
                        conflicts = values.count_payer_rename_conflicts(
                            conn, payer_selection, normalized
                        )
                        if conflicts:
                            st.error(
                                f"Rename blocked: {conflicts} transactions would have payer == payee."
                            )
                        elif not confirm:
                            st.warning("Please confirm rename/merge.")
                        else:
                            with conn:
                                rowcount = values.rename_value(
                                    conn, "payer", payer_selection, normalized
                                )
                            st.success(f"Updated {rowcount} transactions.")
                            st.rerun()

            with st.form("mv_payer_delete"):
                confirm_delete = st.checkbox("Confirm delete")
                delete_submit = st.form_submit_button("Delete")
            if delete_submit:
                conflicts = values.count_payer_delete_conflicts(conn, payer_selection)
                if conflicts:
                    st.error(
                        f"Delete blocked: {conflicts} transactions would have both payer and payee NULL."
                    )
                elif not confirm_delete:
                    st.warning("Please confirm deletion.")
                else:
                    with conn:
                        rowcount = values.clear_value(conn, "payer", payer_selection)
                    st.success(f"Cleared {rowcount} transactions.")
                    st.rerun()

    st.divider()
    st.subheader("Payee")
    payee_counts = values.list_value_counts(conn, "payee")
    if not payee_counts:
        st.info("No payee values found.")
    else:
        payee_options = [value for value, _ in payee_counts]
        payee_selection = ui_widgets.select_existing(
            "Select payee",
            payee_options,
            key="mv_payee_select",
            allow_empty=False,
        )
        if payee_selection:
            with st.form("mv_payee_rename"):
                new_value = st.text_input("Rename payee to")
                confirm = st.checkbox("Confirm rename/merge")
                submit = st.form_submit_button("Rename")
            if submit:
                try:
                    normalized = values.normalize_finance_value(new_value)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    if normalized == payee_selection:
                        st.warning("New value matches the current value.")
                    else:
                        conflicts = values.count_payee_rename_conflicts(
                            conn, payee_selection, normalized
                        )
                        if conflicts:
                            st.error(
                                f"Rename blocked: {conflicts} transactions would have payer == payee."
                            )
                        elif not confirm:
                            st.warning("Please confirm rename/merge.")
                        else:
                            with conn:
                                rowcount = values.rename_value(
                                    conn, "payee", payee_selection, normalized
                                )
                            st.success(f"Updated {rowcount} transactions.")
                            st.rerun()

            with st.form("mv_payee_delete"):
                confirm_delete = st.checkbox("Confirm delete")
                delete_submit = st.form_submit_button("Delete")
            if delete_submit:
                conflicts = values.count_payee_delete_conflicts(conn, payee_selection)
                if conflicts:
                    st.error(
                        f"Delete blocked: {conflicts} transactions would have both payer and payee NULL."
                    )
                elif not confirm_delete:
                    st.warning("Please confirm deletion.")
                else:
                    with conn:
                        rowcount = values.clear_value(conn, "payee", payee_selection)
                    st.success(f"Cleared {rowcount} transactions.")
                    st.rerun()

    st.divider()
    st.subheader("Payment type")
    payment_type_counts = values.list_value_counts(conn, "payment_type")
    if not payment_type_counts:
        st.info("No payment types found.")
    else:
        payment_type_options = [value for value, _ in payment_type_counts]
        payment_type_selection = ui_widgets.select_existing(
            "Select payment type",
            payment_type_options,
            key="mv_payment_type_select",
            allow_empty=False,
        )
        if payment_type_selection:
            with st.form("mv_payment_type_rename"):
                new_value = st.text_input("Rename payment type to")
                confirm = st.checkbox("Confirm rename/merge")
                submit = st.form_submit_button("Rename")
            if submit:
                try:
                    normalized = values.normalize_finance_value(new_value)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    if normalized == payment_type_selection:
                        st.warning("New value matches the current value.")
                    elif not confirm:
                        st.warning("Please confirm rename/merge.")
                    else:
                        with conn:
                            rowcount = values.rename_value(
                                conn, "payment_type", payment_type_selection, normalized
                            )
                        st.success(f"Updated {rowcount} transactions.")
                        st.rerun()

            with st.form("mv_payment_type_delete"):
                confirm_delete = st.checkbox("Confirm delete")
                delete_submit = st.form_submit_button("Delete")
            if delete_submit:
                if not confirm_delete:
                    st.warning("Please confirm deletion.")
                else:
                    with conn:
                        rowcount = values.clear_value(conn, "payment_type", payment_type_selection)
                    st.success(f"Cleared {rowcount} transactions.")
                    st.rerun()

    st.divider()
    st.subheader("Category")
    category_counts = values.list_value_counts(conn, "category")
    if not category_counts:
        st.info("No categories found.")
    else:
        category_options = [value for value, _ in category_counts]
        category_selection = ui_widgets.select_existing(
            "Select category",
            category_options,
            key="mv_category_select",
            allow_empty=False,
        )
        if category_selection:
            with st.form("mv_category_rename"):
                new_value = st.text_input("Rename category to")
                confirm = st.checkbox("Confirm rename/merge")
                submit = st.form_submit_button("Rename")
            if submit:
                try:
                    normalized = values.normalize_finance_value(new_value)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    if normalized == category_selection:
                        st.warning("New value matches the current value.")
                    elif not confirm:
                        st.warning("Please confirm rename/merge.")
                    else:
                        with conn:
                            rowcount = values.rename_value(
                                conn, "category", category_selection, normalized
                            )
                        st.success(f"Updated {rowcount} transactions.")
                        st.rerun()
            st.caption("Category deletion is not allowed in MVP.")

    st.divider()
    st.subheader("Subcategory")
    subcategory_counts = values.list_subcategory_counts(conn)
    if not subcategory_counts:
        st.info("No subcategories found.")
    else:
        category_options = sorted({cat for cat, _, _ in subcategory_counts})
        category_selection = ui_widgets.select_existing(
            "Select category",
            category_options,
            key="mv_subcategory_category",
            allow_empty=False,
        )
        if category_selection:
            scoped_subcategories = values.list_subcategory_counts(
                conn, category=category_selection
            )
            sub_options = [sub for _, sub, _ in scoped_subcategories]
            sub_selection = ui_widgets.select_existing(
                "Select subcategory",
                sub_options,
                key="mv_subcategory_select",
                allow_empty=False,
            )
            if sub_selection:
                with st.form("mv_subcategory_rename"):
                    new_value = st.text_input("Rename subcategory to")
                    confirm = st.checkbox("Confirm rename/merge")
                    submit = st.form_submit_button("Rename")
                if submit:
                    try:
                        normalized = values.normalize_finance_value(new_value)
                    except ValueError as exc:
                        st.error(str(exc))
                    else:
                        if normalized == sub_selection:
                            st.warning("New value matches the current value.")
                        elif not confirm:
                            st.warning("Please confirm rename/merge.")
                        else:
                            with conn:
                                rowcount = values.rename_value(
                                    conn,
                                    "subcategory",
                                    sub_selection,
                                    normalized,
                                    category=category_selection,
                                )
                            st.success(f"Updated {rowcount} transactions.")
                            st.rerun()

                with st.form("mv_subcategory_delete"):
                    confirm_delete = st.checkbox("Confirm delete")
                    delete_submit = st.form_submit_button("Delete")
                if delete_submit:
                    if not confirm_delete:
                        st.warning("Please confirm deletion.")
                    else:
                        with conn:
                            rowcount = values.clear_value(
                                conn,
                                "subcategory",
                                sub_selection,
                                category=category_selection,
                            )
                        st.success(f"Cleared {rowcount} transactions.")
                        st.rerun()

    st.divider()
    st.subheader("Tags")
    tag_counts = tags.tag_counts(conn)
    if not tag_counts:
        st.info("No tags available.")
    else:
        tag_names = [name for name, _ in tag_counts]
        tag_selection = ui_widgets.select_existing(
            "Select tag",
            tag_names,
            key="mv_tag_select",
            allow_empty=False,
        )
        if tag_selection:
            with st.form("tag_rename_form"):
                new_tag = st.text_input("Rename tag to")
                confirm = st.checkbox("Confirm rename/merge")
                rename_tag_submit = st.form_submit_button("Rename")
            if rename_tag_submit:
                try:
                    normalized = tags.normalize_tag(new_tag)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    if normalized == tag_selection:
                        st.warning("New value matches the current value.")
                    elif not confirm:
                        st.warning("Please confirm rename/merge.")
                    else:
                        with conn:
                            tags.rename_tag(conn, tag_selection, normalized)
                        st.success("Tag renamed.")
                        st.rerun()

            with st.form("tag_delete_form"):
                confirm_tag = st.checkbox("Confirm delete")
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
