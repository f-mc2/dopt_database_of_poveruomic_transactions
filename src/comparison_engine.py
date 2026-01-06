import sqlite3
from typing import Iterable, List, Optional, Tuple

import pandas as pd

from src.types import Group, Node, Period

MODE_ROLE = "role"
MODE_MATCHED_ONLY = "matched_only"
NODE_MODE_OR = "or"
NODE_MODE_AND = "and"
TAG_MATCH_ANY = "ANY"
TAG_MATCH_ALL = "ALL"
DATE_FIELDS = {"date_payment", "date_application"}
DEFAULT_DATE_FIELD = "date_payment"


def compute_comparison(
    conn: sqlite3.Connection,
    periods: List[Period],
    groups: List[Group],
    mode: str,
    node_mode: str,
    date_field: str = DEFAULT_DATE_FIELD,
    or_nodes: Optional[List[Node]] = None,
    and_entries: Optional[List[Node]] = None,
    and_tags: Optional[List[str]] = None,
    tag_match: str = TAG_MATCH_ANY,
) -> pd.DataFrame:
    if mode not in {MODE_ROLE, MODE_MATCHED_ONLY}:
        raise ValueError("Invalid mode")
    if node_mode not in {NODE_MODE_OR, NODE_MODE_AND}:
        raise ValueError("Invalid node mode")

    date_field = _resolve_date_field(date_field)

    if node_mode == NODE_MODE_OR:
        nodes = or_nodes or []
        return _compute_for_nodes(conn, periods, groups, mode, date_field, nodes)

    entries = and_entries or []
    tags = [tag.strip().lower() for tag in (and_tags or []) if tag.strip()]
    if entries:
        tag_sql, tag_params = _build_tag_filter(tags, tag_match)
        nodes = []
        for entry in entries:
            node_sql, node_params = _build_node_predicate(entry)
            if tag_sql:
                combined_sql = f"({node_sql}) AND ({tag_sql})"
                combined_params = node_params + tag_params
            else:
                combined_sql = node_sql
                combined_params = node_params
            nodes.append((entry.label, combined_sql, combined_params))
        return _compute_for_custom_nodes(conn, periods, groups, mode, date_field, nodes)

    if not tags:
        return _empty_frame()

    tag_nodes = [Node(label=tag, kind="tag", tag=tag) for tag in tags]
    return _compute_for_nodes(conn, periods, groups, mode, date_field, tag_nodes)


def _compute_for_nodes(
    conn: sqlite3.Connection,
    periods: List[Period],
    groups: List[Group],
    mode: str,
    date_field: str,
    nodes: List[Node],
) -> pd.DataFrame:
    if not nodes:
        return _empty_frame()

    custom_nodes = []
    for node in nodes:
        node_sql, node_params = _build_node_predicate(node)
        custom_nodes.append((node.label, node_sql, node_params))
    return _compute_for_custom_nodes(conn, periods, groups, mode, date_field, custom_nodes)


def _compute_for_custom_nodes(
    conn: sqlite3.Connection,
    periods: List[Period],
    groups: List[Group],
    mode: str,
    date_field: str,
    nodes: List[Tuple[str, str, List[object]]],
) -> pd.DataFrame:
    if not nodes:
        return _empty_frame()

    rows = []
    for period in periods:
        for group in groups:
            for node_label, node_sql, node_params in nodes:
                result = _aggregate_cell(
                    conn, period, group, mode, date_field, node_label, node_sql, node_params
                )
                rows.append(result)
    return pd.DataFrame(rows)


def _empty_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "period",
            "group",
            "node",
            "tx_count",
            "inflow_cents",
            "outflow_cents",
            "internal_cents",
            "net_cents",
        ]
    )


def _aggregate_cell(
    conn: sqlite3.Connection,
    period: Period,
    group: Group,
    mode: str,
    date_field: str,
    node_label: str,
    node_sql: str,
    node_params: List[object],
) -> dict:
    date_field = _resolve_date_field(date_field)
    inflow_sql, outflow_sql, internal_sql, group_any_sql, group_params = _group_predicates(
        group, mode
    )

    sql = f"""
        SELECT
            COALESCE(SUM(CASE WHEN {group_any_sql} THEN 1 ELSE 0 END), 0) AS tx_count,
            COALESCE(SUM(CASE WHEN {inflow_sql} THEN amount_cents ELSE 0 END), 0) AS inflow_cents,
            COALESCE(SUM(CASE WHEN {outflow_sql} THEN amount_cents ELSE 0 END), 0) AS outflow_cents,
            COALESCE(SUM(CASE WHEN {internal_sql} THEN amount_cents ELSE 0 END), 0) AS internal_cents
        FROM transactions t
        WHERE t.{date_field} >= ? AND t.{date_field} <= ? AND ({node_sql})
    """
    params = [period.start_date, period.end_date] + node_params + group_params
    row = conn.execute(sql, params).fetchone()
    if row is None:
        tx_count = inflow = outflow = internal = 0
    else:
        tx_count = int(row[0])
        inflow = int(row[1])
        outflow = int(row[2])
        internal = int(row[3])
    return {
        "period": period.label,
        "group": group.label,
        "node": node_label,
        "tx_count": tx_count,
        "inflow_cents": inflow,
        "outflow_cents": outflow,
        "internal_cents": internal,
        "net_cents": inflow - outflow,
    }


def _build_node_predicate(node: Node) -> Tuple[str, List[object]]:
    if node.kind == "all":
        return "1", []
    if node.kind == "category":
        return "t.category = ?", [node.category]
    if node.kind == "subcategory":
        return "t.category = ? AND t.subcategory = ?", [node.category, node.subcategory]
    if node.kind == "tag":
        return (
            "EXISTS ("
            "SELECT 1 "
            "FROM transaction_tags tt "
            "JOIN tags tg ON tg.id = tt.tag_id "
            "WHERE tt.transaction_id = t.id "
            "  AND tg.name = ?"
            ")",
            [node.tag],
        )
    raise ValueError("Unsupported node kind")


def _build_tag_filter(tags: List[str], match: str) -> Tuple[Optional[str], List[object]]:
    if not tags:
        return None, []
    if match == TAG_MATCH_ANY:
        placeholders = ",".join("?" for _ in tags)
        sql = (
            "EXISTS ("
            "SELECT 1 "
            "FROM transaction_tags tt "
            "JOIN tags tg ON tg.id = tt.tag_id "
            "WHERE tt.transaction_id = t.id "
            "  AND tg.name IN ("
            + placeholders
            + ")"
            ")"
        )
        return sql, tags
    if match == TAG_MATCH_ALL:
        parts = []
        params: List[object] = []
        for tag in tags:
            parts.append(
                "EXISTS ("
                "SELECT 1 "
                "FROM transaction_tags tt "
                "JOIN tags tg ON tg.id = tt.tag_id "
                "WHERE tt.transaction_id = t.id "
                "  AND tg.name = ?"
                ")"
            )
            params.append(tag)
        return " AND ".join(parts), params
    raise ValueError("Invalid tag match")


def _resolve_date_field(value: object) -> str:
    if isinstance(value, str) and value in DATE_FIELDS:
        return value
    return DEFAULT_DATE_FIELD


def _group_predicates(group: Group, mode: str) -> Tuple[str, str, str, str, List[object]]:
    params: List[object] = []

    if mode == MODE_MATCHED_ONLY:
        group_any = _and(
            _in_list("t.payer", group.payers, params),
            _in_list("t.payee", group.payees, params),
        )
        inflow = "0"
        outflow = "0"
        internal = _and(
            _in_list("t.payer", group.payers, params),
            _in_list("t.payee", group.payees, params),
        )
        return inflow, outflow, internal, group_any, params

    group_any = _or(
        _in_list("t.payer", group.payers, params),
        _in_list("t.payee", group.payees, params),
    )
    inflow = _and(
        _in_list("t.payee", group.payees, params),
        _not_in_list("t.payer", group.payers, params),
    )
    outflow = _and(
        _in_list("t.payer", group.payers, params),
        _not_in_list("t.payee", group.payees, params),
    )
    internal = _and(
        _in_list("t.payer", group.payers, params),
        _in_list("t.payee", group.payees, params),
    )
    return inflow, outflow, internal, group_any, params


def _in_list(column: str, values: Iterable[str], params: List[object]) -> str:
    values_list = list(values)
    if not values_list:
        return "0"
    placeholders = ",".join("?" for _ in values_list)
    params.extend(values_list)
    return f"{column} IN ({placeholders})"


def _not_in_list(column: str, values: Iterable[str], params: List[object]) -> str:
    values_list = list(values)
    if not values_list:
        return "1"
    placeholders = ",".join("?" for _ in values_list)
    params.extend(values_list)
    return f"({column} IS NULL OR {column} NOT IN ({placeholders}))"


def _and(left: str, right: str) -> str:
    return f"({left} AND {right})"


def _or(left: str, right: str) -> str:
    return f"({left} OR {right})"
