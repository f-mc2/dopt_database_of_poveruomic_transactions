import datetime as dt
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd
import sqlite3
import streamlit as st

from src import (
    amounts,
    db,
    queries,
    session_state,
    tags,
    transaction_validation,
    transactions_plus_grid,
    ui_widgets,
)

st.set_page_config(
    page_title="Transactions-plus",
    page_icon="\U0001F4B6",
    initial_sidebar_state="auto",
    layout="wide",
)

session_state.ensure_db_session_state()
ui_widgets.render_sidebar_nav()

st.title("Transactions-plus")

if not st.session_state.get("db_ready"):
    st.warning("Open or create a database from the Home page first.")
    st.stop()

DATE_INPUT_MIN = dt.date(1900, 1, 1)
DATE_INPUT_MAX = dt.date(2100, 12, 31)
NONE_SENTINEL = transactions_plus_grid.NONE_SENTINEL
SELECT_COLUMN = "__select__"
SELECT_LABEL = "Select"
COLUMN_ORDER = [
    "id",
    "date_payment",
    "date_application",
    "payer",
    "payee",
    "amount_cents",
    "category",
    "subcategory",
    "notes",
    "tags",
    "payment_type",
]
EDITOR_COLUMN_ORDER = [SELECT_COLUMN] + COLUMN_ORDER
COLUMN_LABELS = {
    "id": "id",
    "date_payment": "Date payment",
    "date_application": "Date application",
    "payer": "Payer",
    "payee": "Payee",
    "amount_cents": "Amount (amount_cents/100)",
    "category": "Category",
    "subcategory": "Subcategory",
    "notes": "Notes",
    "tags": "Tags",
    "payment_type": "Payment type",
}
LABEL_TO_COLUMN = {label: field for field, label in COLUMN_LABELS.items()}


def _normalize_optional(value: Optional[str], lower: bool = True) -> Optional[str]:
    return transactions_plus_grid.normalize_optional(value, lower=lower)


def _merge_options(base: Iterable[str], extras: Iterable[str]) -> List[str]:
    merged: List[str] = []
    seen = set()
    for item in list(base) + list(extras):
        if item in seen:
            continue
        seen.add(item)
        merged.append(item)
    return merged


def _with_none(options: Iterable[str]) -> List[str]:
    cleaned = [opt for opt in options if opt != NONE_SENTINEL]
    return [NONE_SENTINEL] + cleaned


def _get_extra_options() -> Dict[str, List[str]]:
    extra = st.session_state.get("txp_extra_options")
    if isinstance(extra, dict):
        return extra
    extra = {
        "payer": [],
        "payee": [],
        "category": [],
        "subcategory": [],
        "payment_type": [],
    }
    st.session_state["txp_extra_options"] = extra
    return extra


def _render_add_option_helper(options: Dict[str, List[str]]) -> None:
    labels = {
        "payer": "Payer",
        "payee": "Payee",
        "category": "Category",
        "subcategory": "Subcategory",
        "payment_type": "Payment type",
    }
    field_names = list(labels.keys())
    with st.expander("Add new values to suggestions", expanded=False):
        field = st.selectbox(
            "Field",
            options=field_names,
            format_func=lambda key: labels[key],
            key="txp_add_field",
        )
        value = st.text_input("New value", key="txp_add_value")
        if st.button("Add to suggestions", key="txp_add_submit"):
            normalized = _normalize_optional(value)
            if not normalized:
                st.error("Value cannot be empty.")
                return
            if normalized == NONE_SENTINEL:
                st.error("Value cannot be '(none)'.")
                return
            existing = set(options[field])
            if normalized in existing:
                st.info("Value already exists in suggestions.")
                return
            extra = _get_extra_options()
            extra[field].append(normalized)
            st.success(f"Added to suggestions: {normalized}")


def _editor_row(row: sqlite3.Row) -> Dict[str, object]:
    return {
        SELECT_COLUMN: False,
        "id": int(row["id"]),
        "date_payment": row["date_payment"],
        "date_application": row["date_application"],
        "payer": row["payer"] or NONE_SENTINEL,
        "payee": row["payee"] or NONE_SENTINEL,
        "amount_cents": amounts.format_cents(int(row["amount_cents"])),
        "category": row["category"],
        "subcategory": row["subcategory"] or NONE_SENTINEL,
        "notes": row["notes"] or "",
        "tags": tags.parse_tags(row["tags"] or ""),
        "payment_type": row["payment_type"] or NONE_SENTINEL,
    }


def _filter_signature(filters: Dict[str, object]) -> Tuple[object, ...]:
    def _tuple(value: object) -> Tuple[object, ...]:
        if isinstance(value, list):
            return tuple(value)
        if isinstance(value, tuple):
            return value
        if value is None:
            return tuple()
        return (value,)

    return (
        filters.get("date_field"),
        filters.get("date_start"),
        filters.get("date_end"),
        filters.get("search") or "",
        _tuple(filters.get("payers")),
        _tuple(filters.get("payees")),
        _tuple(filters.get("payment_types")),
        _tuple(filters.get("categories")),
        _tuple(filters.get("subcategory_pairs")),
        _tuple(filters.get("tags")),
        bool(filters.get("include_missing_payer")),
        bool(filters.get("include_missing_payee")),
        bool(filters.get("include_missing_payment_type")),
    )




conn: Optional[sqlite3.Connection] = None
try:
    conn = db.connect(st.session_state.db_path)

    payer_options = queries.get_distinct_values(conn, "payer")
    payee_options = queries.get_distinct_values(conn, "payee")
    payment_type_options = queries.get_distinct_values(conn, "payment_type")
    category_options = queries.get_distinct_values(conn, "category")
    subcategory_options = queries.get_distinct_values(conn, "subcategory")
    subcategory_pairs = queries.get_category_subcategory_pairs(conn)
    tag_options = tags.list_tags(conn)

    subcategory_map: Dict[str, List[str]] = {}
    for category_value, subcategory_value in subcategory_pairs:
        subcategory_map.setdefault(subcategory_value, []).append(category_value)

    extra_options = _get_extra_options()
    editor_options = {
        "payer": _with_none(_merge_options(payer_options, extra_options["payer"])),
        "payee": _with_none(_merge_options(payee_options, extra_options["payee"])),
        "payment_type": _with_none(
            _merge_options(payment_type_options, extra_options["payment_type"])
        ),
        "category": _merge_options(category_options, extra_options["category"]),
        "subcategory": _with_none(
            _merge_options(subcategory_options, extra_options["subcategory"])
        ),
    }

    search_query = st.text_input(
        "Search",
        key="txp_search",
        placeholder="payer, payee, category, subcategory, tags, notes",
    )

    all_columns = [COLUMN_LABELS[field] for field in COLUMN_ORDER]
    visible_columns = st.multiselect(
        "Visible columns",
        options=all_columns,
        default=all_columns,
        key="txp_visible_columns",
    )
    if COLUMN_LABELS["id"] not in visible_columns:
        visible_columns = [COLUMN_LABELS["id"]] + visible_columns
        st.session_state["txp_visible_columns"] = visible_columns

    _render_add_option_helper(editor_options)

    table_container = st.container()

    date_field = "date_application"
    min_date, max_date = queries.get_date_bounds(conn, date_field)
    today = dt.date.today()
    date_min_limit = dt.date.fromisoformat(min_date) if min_date else None
    date_max_limit = dt.date.fromisoformat(max_date) if max_date else None
    default_start = date_min_limit or today
    default_end = date_max_limit or today

    st.subheader("Filters")
    with st.form("txp_filters"):
        date_col1, date_col2 = st.columns(2)
        with date_col1:
            start_date = st.date_input(
                "Start date",
                value=default_start,
                min_value=date_min_limit,
                max_value=date_max_limit,
                key="txp_filter_start",
            )
        with date_col2:
            end_date = st.date_input(
                "End date",
                value=default_end,
                min_value=date_min_limit,
                max_value=date_max_limit,
                key="txp_filter_end",
            )

        st.caption(
            "Leave a filter empty to include all values. Select 'Missing (NULL)' to include "
            "or isolate missing values."
        )
        payer_filter, include_missing_payer = ui_widgets.multiselect_with_missing(
            "Payers", payer_options, key="txp_filter_payers"
        )
        payee_filter, include_missing_payee = ui_widgets.multiselect_with_missing(
            "Payees", payee_options, key="txp_filter_payees"
        )
        payment_type_filter, include_missing_payment_type = ui_widgets.multiselect_with_missing(
            "Payment types", payment_type_options, key="txp_filter_payment_types"
        )

        category_filter = ui_widgets.multiselect_existing(
            "Categories", category_options, key="txp_filter_categories"
        )
        sub_labels, label_map = ui_widgets.subcategory_label_map(
            subcategory_pairs, category_filter
        )
        subcategory_filter_labels = ui_widgets.multiselect_existing(
            "Subcategories", sub_labels, key="txp_filter_subcategories"
        )
        subcategory_filter = [label_map[label] for label in subcategory_filter_labels]

        tag_filter = ui_widgets.tags_filter("Tags", tag_options, key="txp_filter_tags")

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

        transactions = queries.list_transactions(conn, filters)

    with table_container:
        if error_message:
            st.error(error_message)
        elif not transactions:
            st.info("No transactions match the current filters.")
        else:
            display_rows = [_editor_row(row) for row in transactions]
            base_df = pd.DataFrame(display_rows)
            if not base_df.empty:
                base_df = base_df[EDITOR_COLUMN_ORDER]

            visible_fields = [
                LABEL_TO_COLUMN[label]
                for label in visible_columns
                if label in LABEL_TO_COLUMN
            ]
            display_order = [SELECT_COLUMN] + [
                field for field in COLUMN_ORDER if field in visible_fields
            ]

            filter_sig = _filter_signature(filters)
            reset_needed = False
            if st.session_state.get("txp_filter_sig") != filter_sig:
                reset_needed = True
            if st.session_state.get("txp_force_reset"):
                reset_needed = True

            if reset_needed:
                st.session_state["txp_filter_sig"] = filter_sig
                st.session_state["txp_original_df"] = base_df
                st.session_state["txp_editor_df"] = base_df.copy(deep=True)
                st.session_state["txp_force_reset"] = False
                st.session_state["txp_editor_key"] = st.session_state.get("txp_editor_key", 0) + 1
            editor_df = st.session_state.get("txp_editor_df", base_df)

            column_config = {
                SELECT_COLUMN: st.column_config.CheckboxColumn(SELECT_LABEL),
                "id": st.column_config.NumberColumn(COLUMN_LABELS["id"], disabled=True),
                "date_payment": st.column_config.TextColumn(COLUMN_LABELS["date_payment"]),
                "date_application": st.column_config.TextColumn(
                    COLUMN_LABELS["date_application"]
                ),
                "payer": st.column_config.SelectboxColumn(
                    COLUMN_LABELS["payer"],
                    options=editor_options["payer"],
                ),
                "payee": st.column_config.SelectboxColumn(
                    COLUMN_LABELS["payee"],
                    options=editor_options["payee"],
                ),
                "amount_cents": st.column_config.TextColumn(COLUMN_LABELS["amount_cents"]),
                "category": st.column_config.SelectboxColumn(
                    COLUMN_LABELS["category"],
                    options=editor_options["category"],
                ),
                "subcategory": st.column_config.SelectboxColumn(
                    COLUMN_LABELS["subcategory"],
                    options=editor_options["subcategory"],
                ),
                "notes": st.column_config.TextColumn(COLUMN_LABELS["notes"]),
                "tags": st.column_config.MultiselectColumn(
                    COLUMN_LABELS["tags"],
                    options=tag_options,
                    accept_new_options=True,
                ),
                "payment_type": st.column_config.SelectboxColumn(
                    COLUMN_LABELS["payment_type"],
                    options=editor_options["payment_type"],
                ),
            }

            editor_height = max(420, 32 * 15 + 80)
            edited_df = st.data_editor(
                editor_df,
                key=f"txp_editor_{st.session_state.get('txp_editor_key', 0)}",
                column_config=column_config,
                column_order=display_order,
                hide_index=True,
                height=editor_height,
                width="stretch",
                disabled=["id"],
            )
            st.session_state["txp_editor_df"] = edited_df

            st.caption(
                "Subcategory suggestions are global; save validates that each row's "
                "subcategory matches its category."
            )
            st.caption(
                "Default order is date_application desc, id desc; click column headers to sort."
            )

            with st.expander("Bulk edit selected rows", expanded=False):
                selected_ids = []
                if SELECT_COLUMN in edited_df.columns and "id" in edited_df.columns:
                    selected_ids = (
                        edited_df.loc[edited_df[SELECT_COLUMN] == True, "id"]
                        .astype(int)
                        .tolist()
                    )
                st.caption(f"Selected rows: {len(selected_ids)}")

                bulk_fields = {
                    "category_subcategory": "Category + subcategory",
                    "payer": "Payer",
                    "payee": "Payee",
                    "category": "Category",
                    "subcategory": "Subcategory",
                    "payment_type": "Payment type",
                    "date_payment": "Date payment",
                    "date_application": "Date application",
                    "amount_cents": "Amount",
                    "notes": "Notes",
                    "tags": "Tags",
                }
                bulk_field = st.selectbox(
                    "Field",
                    options=list(bulk_fields.keys()),
                    format_func=lambda key: bulk_fields[key],
                    key="txp_bulk_field",
                )

                bulk_value: object = None
                tag_values: List[str] = []
                if bulk_field == "category_subcategory":
                    bulk_category = st.selectbox(
                        "Category",
                        options=editor_options["category"],
                        key="txp_bulk_value_category_combo",
                    )
                    subcategory_for_category = (
                        queries.get_subcategories_for_category(conn, bulk_category)
                        if bulk_category
                        else []
                    )
                    subcategory_for_category = _with_none(subcategory_for_category)
                    bulk_subcategory = st.selectbox(
                        "Subcategory",
                        options=subcategory_for_category,
                        key="txp_bulk_value_subcategory_combo",
                    )
                    bulk_value = {
                        "category": bulk_category,
                        "subcategory": bulk_subcategory,
                    }
                elif bulk_field in {"payer", "payee", "subcategory", "payment_type"}:
                    bulk_value = st.selectbox(
                        "Value",
                        options=editor_options[bulk_field],
                        key="txp_bulk_value_select",
                    )
                elif bulk_field == "category":
                    bulk_value = st.selectbox(
                        "Value",
                        options=editor_options["category"],
                        key="txp_bulk_value_category",
                    )
                elif bulk_field in {"date_payment", "date_application"}:
                    bulk_date = st.date_input(
                        "Value",
                        value=today,
                        min_value=DATE_INPUT_MIN,
                        max_value=DATE_INPUT_MAX,
                        key="txp_bulk_value_date",
                    )
                    bulk_value = bulk_date.isoformat()
                elif bulk_field == "amount_cents":
                    bulk_value = st.text_input(
                        "Value (amount)",
                        value="0.00",
                        key="txp_bulk_value_amount",
                    )
                elif bulk_field == "notes":
                    bulk_value = st.text_area(
                        "Value (notes)",
                        value="",
                        key="txp_bulk_value_notes",
                    )
                elif bulk_field == "tags":
                    tag_values = st.multiselect(
                        "Tags",
                        options=tag_options,
                        default=[],
                        key="txp_bulk_value_tags",
                    )
                    new_tags_raw = st.text_input(
                        "Add new tags (comma-separated)",
                        key="txp_bulk_value_tags_new",
                    )
                    if new_tags_raw.strip():
                        try:
                            new_tags = tags.parse_tags(new_tags_raw)
                        except ValueError as exc:
                            st.error(str(exc))
                            new_tags = []
                        for tag_value in new_tags:
                            if tag_value not in tag_values:
                                tag_values.append(tag_value)
                    bulk_value = tag_values
                    st.caption("Applying an empty tag list will clear tags for selected rows.")

                clear_selection = st.checkbox(
                    "Clear selection after apply",
                    value=True,
                    key="txp_bulk_clear_selection",
                )
                if st.button("Apply to selected rows", key="txp_bulk_apply"):
                    if not selected_ids:
                        st.warning("Select at least one row to apply changes.")
                    else:
                        updated_df = edited_df.copy(deep=True)
                        selected_mask = updated_df["id"].isin(selected_ids)
                        if bulk_field == "category_subcategory":
                            updated_df.loc[selected_mask, "category"] = bulk_value["category"]
                            updated_df.loc[selected_mask, "subcategory"] = bulk_value[
                                "subcategory"
                            ]
                        elif bulk_field == "tags":
                            tag_payload = list(bulk_value)
                            updated_df.loc[selected_mask, "tags"] = [
                                tag_payload
                            ] * int(selected_mask.sum())
                        else:
                            updated_df.loc[selected_mask, bulk_field] = bulk_value
                        if clear_selection and SELECT_COLUMN in updated_df.columns:
                            updated_df.loc[selected_mask, SELECT_COLUMN] = False
                        st.session_state["txp_editor_df"] = updated_df
                        st.session_state["txp_editor_key"] = (
                            st.session_state.get("txp_editor_key", 0) + 1
                        )
                        st.rerun()

            action_col1, action_col2 = st.columns([1, 1])
            with action_col1:
                save_clicked = st.button("Save changes", key="txp_save", type="primary")
            with action_col2:
                discard_clicked = st.button("Discard changes", key="txp_discard")

            if discard_clicked:
                st.session_state["txp_force_reset"] = True
                st.success("Changes discarded.")
                st.rerun()

            if save_clicked:
                errors: List[str] = []
                payloads: Dict[int, Dict[str, object]] = {}

                original_df = st.session_state.get("txp_original_df", base_df)
                original_map = {
                    int(row["id"]): row
                    for _, row in original_df.iterrows()
                    if "id" in row
                }

                for _, row in edited_df.iterrows():
                    tx_id_raw = row.get("id")
                    if tx_id_raw is None:
                        errors.append("Missing transaction id for a row.")
                        continue
                    tx_id = int(tx_id_raw)
                    payload, row_errors = transactions_plus_grid.build_payload(
                        row, subcategory_map
                    )
                    if row_errors:
                        for msg in row_errors:
                            errors.append(f"Row {tx_id}: {msg}")
                        continue
                    original_row = original_map.get(tx_id)
                    if original_row is None:
                        errors.append(f"Row {tx_id}: original transaction not found.")
                        continue
                    original_payload, original_errors = transactions_plus_grid.build_payload(
                        original_row, subcategory_map
                    )
                    if original_errors:
                        errors.append(
                            f"Row {tx_id}: unable to validate original transaction."
                        )
                        continue
                    if payload != original_payload:
                        payloads[tx_id] = payload

                if errors:
                    st.error("; ".join(errors))
                elif not payloads:
                    st.info("No changes to save.")
                else:
                    with conn:
                        for tx_id, payload in payloads.items():
                            queries.update_transaction(
                                conn,
                                transaction_id=tx_id,
                                date_payment=payload["date_payment"],
                                date_application=payload["date_application"],
                                amount_cents=payload["amount_cents"],
                                payer=payload["payer"],
                                payee=payload["payee"],
                                payment_type=payload["payment_type"],
                                category=payload["category"],
                                subcategory=payload["subcategory"],
                                notes=payload["notes"],
                            )
                            tags.set_transaction_tags(conn, tx_id, payload["tags"])
                    st.success(f"Saved changes to {len(payloads)} transaction(s).")
                    st.session_state["txp_force_reset"] = True
                    st.rerun()

    st.divider()
    st.subheader("Add transaction")
    date_payment = st.date_input(
        "Payment date",
        value=today,
        min_value=DATE_INPUT_MIN,
        max_value=DATE_INPUT_MAX,
        key="txp_add_date_payment",
    )
    copy_dates = st.checkbox(
        "Use payment date for application date",
        value=True,
        key="txp_add_copy_dates",
    )
    if copy_dates:
        st.date_input(
            "Application date",
            value=date_payment,
            min_value=DATE_INPUT_MIN,
            max_value=DATE_INPUT_MAX,
            key="txp_add_date_application",
            disabled=True,
        )
        date_application = date_payment
    else:
        date_application = st.date_input(
            "Application date",
            value=today,
            min_value=DATE_INPUT_MIN,
            max_value=DATE_INPUT_MAX,
            key="txp_add_date_application",
        )
    form_amount = st.text_input("Amount", value="0.00", key="txp_add_amount")

    payer_value, _ = ui_widgets.select_or_create(
        "Payer",
        payer_options,
        key="txp_add_payer",
        allow_empty=True,
    )
    payee_value, _ = ui_widgets.select_or_create(
        "Payee",
        payee_options,
        key="txp_add_payee",
        allow_empty=True,
    )
    payment_type_value, _ = ui_widgets.select_or_create(
        "Payment type",
        payment_type_options,
        key="txp_add_payment_type",
        allow_empty=True,
    )
    category_value, _ = ui_widgets.select_or_create(
        "Category",
        category_options,
        key="txp_add_category",
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
        key="txp_add_subcategory",
        allow_empty=True,
    )
    form_notes = st.text_area("Notes", key="txp_add_notes")

    selected_tags, new_tag = ui_widgets.tags_assign(
        "Tags",
        tag_options,
        key="txp_add_tags",
    )

    submitted_new = st.button("Add transaction", key="txp_add_transaction_submit")

    if submitted_new:
        payload, errors = transaction_validation.validate_transaction_form(
            amount_raw=form_amount,
            category=category_value,
            payer=payer_value,
            payee=payee_value,
            payment_type=payment_type_value,
            subcategory=subcategory_value,
            notes=form_notes,
            selected_tags=selected_tags,
            new_tag=new_tag,
        )
        if errors:
            st.error("; ".join(errors))
        else:
            with conn:
                transaction_id = queries.insert_transaction(
                    conn,
                    date_payment=date_payment.isoformat(),
                    date_application=date_application.isoformat(),
                    amount_cents=int(payload["amount_cents"]),
                    payer=payload["payer"],
                    payee=payload["payee"],
                    payment_type=payload["payment_type"],
                    category=str(payload["category"]),
                    subcategory=payload["subcategory"],
                    notes=payload["notes"],
                )
                tags.set_transaction_tags(conn, transaction_id, payload["tags"])
            st.success("Transaction added.")
            st.session_state["txp_force_reset"] = True
            st.rerun()

    st.divider()
    st.subheader(
        "Edit or delete",
        help="The selector defaults to the most recent transaction in the current filters, so the form is prefilled.",
    )
    if not transactions:
        st.info("No transactions available for editing.")
    else:
        tx_map = {int(row["id"]): row for row in transactions}
        tx_ids = list(tx_map.keys())
        selected_id = st.selectbox(
            "Transaction",
            tx_ids,
            format_func=lambda value: f"{value} • pay {tx_map[value]['date_payment']} • app {tx_map[value]['date_application']} • {amounts.format_cents(int(tx_map[value]['amount_cents']))}",
            key="txp_edit_id",
        )
        selected_row = queries.get_transaction(conn, selected_id)
        if selected_row is None:
            st.warning("Selected transaction is not available.")
        else:
            current_tags = tags.get_tags_for_transaction(conn, selected_id)
            if f"txp_edit_tags_{selected_id}_selected" not in st.session_state:
                st.session_state[f"txp_edit_tags_{selected_id}_selected"] = current_tags

            with st.form(f"txp_edit_tx_{selected_id}"):
                edit_date_payment = st.date_input(
                    "Payment date",
                    value=dt.date.fromisoformat(selected_row["date_payment"]),
                    min_value=DATE_INPUT_MIN,
                    max_value=DATE_INPUT_MAX,
                    key=f"txp_edit_date_payment_{selected_id}",
                )
                copy_edit_dates = st.checkbox(
                    "Use payment date for application date",
                    value=(selected_row["date_payment"] == selected_row["date_application"]),
                    key=f"txp_edit_copy_dates_{selected_id}",
                )
                if copy_edit_dates:
                    st.date_input(
                        "Application date",
                        value=edit_date_payment,
                        min_value=DATE_INPUT_MIN,
                        max_value=DATE_INPUT_MAX,
                        key=f"txp_edit_date_application_{selected_id}",
                        disabled=True,
                    )
                    edit_date_application = edit_date_payment
                else:
                    edit_date_application = st.date_input(
                        "Application date",
                        value=dt.date.fromisoformat(selected_row["date_application"]),
                        min_value=DATE_INPUT_MIN,
                        max_value=DATE_INPUT_MAX,
                        key=f"txp_edit_date_application_{selected_id}",
                    )
                edit_amount = st.text_input(
                    "Amount",
                    value=amounts.format_cents(int(selected_row["amount_cents"])),
                    key=f"txp_edit_amount_{selected_id}",
                )

                payer_value, _ = ui_widgets.select_or_create(
                    "Payer",
                    payer_options,
                    key=f"txp_edit_payer_{selected_id}",
                    value=selected_row["payer"],
                    allow_empty=True,
                )
                payee_value, _ = ui_widgets.select_or_create(
                    "Payee",
                    payee_options,
                    key=f"txp_edit_payee_{selected_id}",
                    value=selected_row["payee"],
                    allow_empty=True,
                )
                payment_type_value, _ = ui_widgets.select_or_create(
                    "Payment type",
                    payment_type_options,
                    key=f"txp_edit_payment_type_{selected_id}",
                    value=selected_row["payment_type"],
                    allow_empty=True,
                )
                category_value, _ = ui_widgets.select_or_create(
                    "Category",
                    category_options,
                    key=f"txp_edit_category_{selected_id}",
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
                    key=f"txp_edit_subcategory_{selected_id}",
                    value=selected_row["subcategory"],
                    allow_empty=True,
                )
                edit_notes = st.text_area(
                    "Notes",
                    value=selected_row["notes"] or "",
                    key=f"txp_edit_notes_{selected_id}",
                )

                selected_tags, new_tag = ui_widgets.tags_assign(
                    "Tags",
                    tag_options,
                    key=f"txp_edit_tags_{selected_id}",
                )

                submitted = st.form_submit_button("Save changes")

            if submitted:
                payload, errors = transaction_validation.validate_transaction_form(
                    amount_raw=edit_amount,
                    category=category_value,
                    payer=payer_value,
                    payee=payee_value,
                    payment_type=payment_type_value,
                    subcategory=subcategory_value,
                    notes=edit_notes,
                    selected_tags=selected_tags,
                    new_tag=new_tag,
                )
                if errors:
                    st.error("; ".join(errors))
                else:
                    with conn:
                        queries.update_transaction(
                            conn,
                            transaction_id=selected_id,
                            date_payment=edit_date_payment.isoformat(),
                            date_application=edit_date_application.isoformat(),
                            amount_cents=int(payload["amount_cents"]),
                            payer=payload["payer"],
                            payee=payload["payee"],
                            payment_type=payload["payment_type"],
                            category=str(payload["category"]),
                            subcategory=payload["subcategory"],
                            notes=payload["notes"],
                        )
                        tags.set_transaction_tags(conn, selected_id, payload["tags"])
                    st.success("Transaction updated.")
                    st.session_state["txp_force_reset"] = True
                    st.rerun()

            st.divider()
            confirm_delete = st.checkbox(
                "Confirm delete",
                key=f"txp_delete_confirm_{selected_id}",
            )
            if st.button("Delete transaction", key=f"txp_delete_{selected_id}"):
                if not confirm_delete:
                    st.warning("Please confirm deletion.")
                else:
                    with conn:
                        queries.delete_transaction(conn, selected_id)
                    st.success("Transaction deleted.")
                    st.session_state["txp_force_reset"] = True
                    st.rerun()
finally:
    if conn is not None:
        conn.close()
