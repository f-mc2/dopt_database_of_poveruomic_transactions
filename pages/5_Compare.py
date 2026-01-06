import datetime as dt
from typing import List, Optional

import sqlite3
import streamlit as st

from src import comparison_engine, db, plotting, queries, tags, ui_widgets
from src.types import Group, Node, Period

st.title("Compare")

if not st.session_state.get("db_ready"):
    st.warning("Open or create a database from the Home page first.")
    st.stop()


def _default_label(prefix: str, index: int, value: str) -> str:
    cleaned = value.strip()
    return cleaned or f"{prefix} {index}"


def _build_or_nodes(
    categories: List[str],
    sub_pairs: List[tuple],
    tags_list: List[str],
) -> List[Node]:
    nodes: List[Node] = []
    for category in categories:
        nodes.append(Node(label=category, kind="category", category=category))
    for category, subcategory in sub_pairs:
        label = f"{category}:{subcategory}"
        nodes.append(
            Node(
                label=label,
                kind="subcategory",
                category=category,
                subcategory=subcategory,
            )
        )
    for tag in tags_list:
        nodes.append(Node(label=tag, kind="tag", tag=tag))
    return nodes


def _build_entry_nodes(categories: List[str], sub_pairs: List[tuple]) -> List[Node]:
    nodes: List[Node] = []
    for category in categories:
        nodes.append(Node(label=category, kind="category", category=category))
    for category, subcategory in sub_pairs:
        label = f"{category}:{subcategory}"
        nodes.append(
            Node(
                label=label,
                kind="subcategory",
                category=category,
                subcategory=subcategory,
            )
        )
    return nodes


conn: Optional[sqlite3.Connection] = None
try:
    conn = db.connect(st.session_state.db_path)

    payer_options = queries.get_distinct_values(conn, "payer")
    payee_options = queries.get_distinct_values(conn, "payee")
    category_options = queries.get_distinct_values(conn, "category")
    subcategory_pairs = queries.get_category_subcategory_pairs(conn)
    tag_options = tags.list_tags(conn)

    date_field_labels = {
        "Payment date": "date_payment",
        "Application date": "date_application",
    }
    selected_label = st.selectbox(
        "Period date field",
        list(date_field_labels.keys()),
        key="compare_date_field",
    )
    date_field = date_field_labels[selected_label]

    min_date, max_date = queries.get_date_bounds(conn, date_field)
    if min_date is None or max_date is None:
        min_date_value = dt.date.today()
        max_date_value = dt.date.today()
    else:
        min_date_value = dt.date.fromisoformat(min_date)
        max_date_value = dt.date.fromisoformat(max_date)

    st.subheader("Setup")
    period_count = st.number_input(
        "Number of periods",
        min_value=1,
        max_value=5,
        value=1,
        step=1,
        key="compare_period_count",
    )
    group_count = st.number_input(
        "Number of groups",
        min_value=1,
        max_value=5,
        value=1,
        step=1,
        key="compare_group_count",
    )

    periods: List[Period] = []
    period_errors: List[str] = []
    for idx in range(int(period_count)):
        with st.expander(f"Period {idx + 1}", expanded=True):
            label_input = st.text_input(
                "Label",
                value=f"Period {idx + 1}",
                key=f"period_label_{idx}",
            )
            start_date = st.date_input(
                "Start date",
                value=min_date_value,
                key=f"period_start_{idx}",
            )
            end_date = st.date_input(
                "End date",
                value=max_date_value,
                key=f"period_end_{idx}",
            )
            if start_date > end_date:
                period_errors.append(f"Period {idx + 1} has start date after end date.")
            periods.append(
                Period(
                    label=_default_label("Period", idx + 1, label_input),
                    start_date=start_date.isoformat(),
                    end_date=end_date.isoformat(),
                )
            )

    groups: List[Group] = []
    for idx in range(int(group_count)):
        with st.expander(f"Group {idx + 1}", expanded=True):
            label_input = st.text_input(
                "Label",
                value=f"Group {idx + 1}",
                key=f"group_label_{idx}",
            )
            payers = ui_widgets.typeahead_multi_select(
                "Payers",
                payer_options,
                key=f"group_{idx}_payers",
            )
            payees = ui_widgets.typeahead_multi_select(
                "Payees",
                payee_options,
                key=f"group_{idx}_payees",
            )
            groups.append(
                Group(
                    label=_default_label("Group", idx + 1, label_input),
                    payers=payers,
                    payees=payees,
                )
            )

    st.subheader("Nodes")
    mode = st.radio("Computation mode", ["role", "matched_only"], key="compare_mode")
    node_mode = st.radio("Node selection", ["OR", "AND"], key="compare_node_mode")

    node_entries: List[Node] = []
    node_tags: List[str] = []
    tag_match = comparison_engine.TAG_MATCH_ANY

    if node_mode == "OR":
        options = _build_or_nodes(category_options, subcategory_pairs, tag_options)
        node_entries = st.multiselect(
            "Nodes",
            options=options,
            format_func=lambda node: node.label,
            key="compare_or_nodes",
        )
        if len(node_entries) > 10:
            st.error("OR mode supports up to 10 nodes.")
    else:
        entry_options = _build_entry_nodes(category_options, subcategory_pairs)
        node_entries = st.multiselect(
            "Category/Subcategory entries",
            options=entry_options,
            format_func=lambda node: node.label,
            key="compare_and_entries",
        )
        if len(node_entries) > 10:
            st.error("AND mode supports up to 10 category/subcategory entries.")

        node_tags = st.multiselect("Tags", options=tag_options, key="compare_and_tags")
        tag_match = st.selectbox("Tag match", ["ANY", "ALL"], key="compare_tag_match")
        if tag_match == "ALL" and len(node_tags) > 5:
            st.warning("TagMatch ALL with many tags can be slow.")

    if st.button("Run comparison"):
        errors: List[str] = []
        if period_errors:
            errors.extend(period_errors)
        if not groups:
            errors.append("At least one group is required.")
        if node_mode == "OR" and len(node_entries) > 10:
            errors.append("Reduce OR nodes to at most 10.")
        if node_mode == "AND" and len(node_entries) > 10:
            errors.append("Reduce AND entries to at most 10.")
        if node_mode == "AND" and not node_entries and not node_tags:
            errors.append("Select at least one entry or tag in AND mode.")
        if errors:
            st.error(" ".join(errors))
        else:
            if node_mode == "OR":
                df = comparison_engine.compute_comparison(
                    conn,
                    periods=periods,
                    groups=groups,
                    mode=mode,
                    node_mode="or",
                    date_field=date_field,
                    or_nodes=node_entries,
                )
            else:
                df = comparison_engine.compute_comparison(
                    conn,
                    periods=periods,
                    groups=groups,
                    mode=mode,
                    node_mode="and",
                    date_field=date_field,
                    and_entries=node_entries,
                    and_tags=node_tags,
                    tag_match=tag_match,
                )

            if df.empty:
                st.info("No comparison data generated.")
            else:
                st.subheader("Results")
                st.dataframe(df, use_container_width=True)

                metric = st.selectbox(
                    "Metric",
                    ["net_cents", "inflow_cents", "outflow_cents", "internal_cents"],
                    key="compare_metric",
                )
                period_order = [period.label for period in periods]
                for group in groups:
                    st.markdown(f"### {group.label}")
                    chart = plotting.grouped_bar_chart(
                        df,
                        group_label=group.label,
                        value_field=metric,
                        period_order=period_order,
                    )
                    st.altair_chart(chart, use_container_width=True)

finally:
    if conn is not None:
        conn.close()
