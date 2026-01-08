import datetime as dt
from typing import Dict, List, Optional, Tuple

import pandas as pd
import sqlite3
import streamlit as st

from src import amounts, comparison_engine, db, plotting, queries, session_state, tags, ui_widgets
from src.types import Group, Node, Period

session_state.ensure_db_session_state()

st.title("Compare")

if not st.session_state.get("db_ready"):
    st.warning("Open or create a database from the Home page first.")
    st.stop()


def _default_label(prefix: str, index: int, value: str) -> str:
    cleaned = value.strip()
    return cleaned or f"{prefix} {index}"


def _build_category_nodes(categories: List[str], sub_pairs: List[Tuple[str, str]]) -> Dict[str, Node]:
    nodes: Dict[str, Node] = {"All categories": Node(label="All categories", kind="all_categories")}
    for category in categories:
        nodes[category] = Node(label=category, kind="category", category=category)
    for category, subcategory in sub_pairs:
        label = f"{category} / {subcategory}"
        nodes[label] = Node(
            label=label,
            kind="subcategory",
            category=category,
            subcategory=subcategory,
        )
    return nodes


def _build_or_nodes(
    categories: List[str],
    sub_pairs: List[Tuple[str, str]],
    tag_list: List[str],
) -> Dict[str, Node]:
    nodes = _build_category_nodes(categories, sub_pairs)
    nodes["All tags"] = Node(label="All tags", kind="all_tags")
    for tag in tag_list:
        nodes[tag] = Node(label=tag, kind="tag", tag=tag)
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
        "Application date": "date_application",
        "Payment date": "date_payment",
    }
    selected_label = st.selectbox(
        "Date field",
        list(date_field_labels.keys()),
        index=0,
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

    st.subheader("Periods")
    period_count = st.number_input(
        "Number of periods",
        min_value=1,
        max_value=5,
        value=1,
        step=1,
        key="compare_period_count",
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
            full_range = st.checkbox(
                "Use full range",
                value=True,
                key=f"period_full_{idx}",
            )
            if full_range:
                start_date = min_date_value
                end_date = max_date_value
                st.caption(f"{start_date.isoformat()} to {end_date.isoformat()}")
            else:
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

    st.subheader("Groups")
    group_count = st.number_input(
        "Number of groups",
        min_value=1,
        max_value=5,
        value=1,
        step=1,
        key="compare_group_count",
    )

    groups: List[Group] = []
    for idx in range(int(group_count)):
        with st.expander(f"Group {idx + 1}", expanded=True):
            label_input = st.text_input(
                "Label",
                value=f"Group {idx + 1}",
                key=f"group_label_{idx}",
            )
            payers = ui_widgets.multiselect_existing(
                "Payers",
                payer_options,
                key=f"group_{idx}_payers",
            )
            payees = ui_widgets.multiselect_existing(
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

    st.subheader("Mode")
    mode_label = st.radio(
        "Computation mode",
        ["role", "perfect-match"],
        key="compare_mode",
        horizontal=True,
    )
    mode = "matched_only" if mode_label == "perfect-match" else "role"

    st.subheader("Node selection")
    node_mode_label = st.radio(
        "Slice mode",
        ["Category slices + tag filter", "Mixed slices"],
        key="compare_node_mode",
        horizontal=True,
    )
    node_mode = "and" if node_mode_label == "Category slices + tag filter" else "or"

    and_entries: List[Node] = []
    or_entries: List[Node] = []
    and_tags: List[str] = []
    tag_match = comparison_engine.TAG_MATCH_ANY

    if node_mode == "and":
        node_map = _build_category_nodes(category_options, subcategory_pairs)
        selected_labels = ui_widgets.multiselect_existing(
            "Category/subcategory nodes",
            list(node_map.keys()),
            key="compare_and_nodes",
        )
        if len(selected_labels) > 10:
            st.error("Select at most 10 nodes.")
        and_entries = [node_map[label] for label in selected_labels]

        and_tags = ui_widgets.tags_filter("Tags", tag_options, key="compare_and_tags")
        tag_match = st.selectbox(
            "Tag match",
            [comparison_engine.TAG_MATCH_ANY, comparison_engine.TAG_MATCH_ALL],
            key="compare_tag_match",
        )
    else:
        node_map = _build_or_nodes(category_options, subcategory_pairs, tag_options)
        selected_labels = ui_widgets.multiselect_existing(
            "Nodes",
            list(node_map.keys()),
            key="compare_or_nodes",
        )
        if len(selected_labels) > 10:
            st.error("Select at most 10 nodes.")
        or_entries = [node_map[label] for label in selected_labels]

    if st.button("Run comparison"):
        errors: List[str] = []
        if period_errors:
            errors.extend(period_errors)
        if not groups:
            errors.append("At least one group is required.")
        if node_mode == "and" and not and_entries:
            errors.append("Select at least one category/subcategory node.")
        if node_mode == "or" and not or_entries:
            errors.append("Select at least one node.")
        if node_mode == "and" and len(and_entries) > 10:
            errors.append("Reduce category/subcategory nodes to at most 10.")
        if node_mode == "or" and len(or_entries) > 10:
            errors.append("Reduce nodes to at most 10.")

        if errors:
            st.error(" ".join(errors))
        else:
            df = comparison_engine.compute_comparison(
                conn,
                periods=periods,
                groups=groups,
                mode=mode,
                node_mode=node_mode,
                date_field=date_field,
                or_nodes=or_entries,
                and_entries=and_entries,
                and_tags=and_tags,
                tag_match=tag_match,
            )

            if df.empty:
                st.info("No comparison data generated.")
            else:
                st.subheader("Results")
                period_order = [period.label for period in periods]
                node_order = (
                    [node.label for node in and_entries]
                    if node_mode == "and"
                    else [node.label for node in or_entries]
                )

                for period_label in period_order:
                    st.markdown(f"### {period_label}")
                    period_df = df[df["period_label"] == period_label]
                    for node_label in node_order:
                        node_df = period_df[period_df["node_label"] == node_label]
                        if node_df.empty:
                            continue
                        st.markdown(f"#### {node_label}")
                        table = node_df.set_index("group_label")
                        if mode == "matched_only":
                            display = pd.DataFrame(
                                {
                                    "#transactions": table["tx_count"].astype(int),
                                    "matched flow": table["matched_flow_cents"].apply(
                                        lambda v: amounts.format_cents(int(v))
                                    ),
                                }
                            )
                        else:
                            display = pd.DataFrame(
                                {
                                    "#tx (inflow ∪ outflow)": table["tx_count"].astype(int),
                                    "inflow": table["inflow_cents"].apply(
                                        lambda v: amounts.format_cents(int(v))
                                    ),
                                    "outflow": table["outflow_cents"].apply(
                                        lambda v: amounts.format_cents(int(v))
                                    ),
                                    "net": table["net_cents"].apply(
                                        lambda v: amounts.format_cents(int(v))
                                    ),
                                }
                            )
                        st.dataframe(display, use_container_width=True)

                st.divider()
                if mode == "matched_only":
                    metric = "matched_flow_cents"
                else:
                    metric = st.selectbox(
                        "Metric",
                        ["net_cents", "inflow_cents", "outflow_cents"],
                        key="compare_metric",
                    )
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
