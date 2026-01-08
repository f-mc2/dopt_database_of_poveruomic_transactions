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
DEFAULT_DATE_FIELD = "date_application"


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
    if not entries:
        return _empty_frame()

    tag_list = [tag.strip().lower() for tag in (and_tags or []) if tag.strip()]
    tag_sql, tag_params = _build_tag_filter(tag_list, tag_match)

    nodes: List[Tuple[str, str, List[object]]] = []
    for entry in entries:
        node_sql, node_params = _build_node_predicate(entry)
        if tag_sql == "1":
            combined_sql = node_sql
            combined_params = node_params
        else:
            combined_sql = f"({node_sql}) AND ({tag_sql})"
            combined_params = node_params + tag_params
        nodes.append((entry.label, combined_sql, combined_params))

    return _compute_for_custom_nodes(conn, periods, groups, mode, date_field, nodes)


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
            "period_label",
            "group_label",
            "node_label",
            "tx_count",
            "inflow_cents",
            "outflow_cents",
            "net_cents",
            "matched_flow_cents",
            "mode",
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
    payer_sql, payer_params = _in_list("t.payer", group.payers)
    payee_sql, payee_params = _in_list("t.payee", group.payees)

    base_sql = f"""
        FROM (
            SELECT
                t.amount_cents,
                {payer_sql} AS payer_in_a,
                {payee_sql} AS payee_in_b
            FROM transactions t
            WHERE t.{date_field} >= ? AND t.{date_field} <= ? AND ({node_sql})
        ) base
    """
    base_params = payer_params + payee_params + [period.start_date, period.end_date] + node_params

    if mode == MODE_MATCHED_ONLY:
        sql = (
            "SELECT "
            "COALESCE(SUM(CASE WHEN (payer_in_a AND payee_in_b) THEN 1 ELSE 0 END), 0) AS tx_count, "
            "COALESCE(SUM(CASE WHEN (payer_in_a AND payee_in_b) THEN amount_cents ELSE 0 END), 0) AS matched_flow "
            + base_sql
        )
        row = conn.execute(sql, base_params).fetchone()
        tx_count = int(row[0]) if row else 0
        matched_flow = int(row[1]) if row else 0
        return {
            "period_label": period.label,
            "group_label": group.label,
            "node_label": node_label,
            "tx_count": tx_count,
            "inflow_cents": 0,
            "outflow_cents": 0,
            "net_cents": 0,
            "matched_flow_cents": matched_flow,
            "mode": mode,
        }

    sql = (
        "SELECT "
        "COALESCE(SUM(CASE WHEN (payer_in_a OR payee_in_b) THEN 1 ELSE 0 END), 0) AS tx_count, "
        "COALESCE(SUM(CASE WHEN payee_in_b THEN amount_cents ELSE 0 END), 0) AS inflow_cents, "
        "COALESCE(SUM(CASE WHEN payer_in_a THEN amount_cents ELSE 0 END), 0) AS outflow_cents "
        + base_sql
    )
    row = conn.execute(sql, base_params).fetchone()
    tx_count = int(row[0]) if row else 0
    inflow = int(row[1]) if row else 0
    outflow = int(row[2]) if row else 0
    return {
        "period_label": period.label,
        "group_label": group.label,
        "node_label": node_label,
        "tx_count": tx_count,
        "inflow_cents": inflow,
        "outflow_cents": outflow,
        "net_cents": inflow - outflow,
        "matched_flow_cents": 0,
        "mode": mode,
    }


def _build_node_predicate(node: Node) -> Tuple[str, List[object]]:
    if node.kind in {"all", "all_categories", "all_tags"}:
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


def _build_tag_filter(tags: List[str], match: str) -> Tuple[str, List[object]]:
    if not tags:
        return "1", []
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


def _in_list(column: str, values: Iterable[str]) -> Tuple[str, List[object]]:
    values_list = list(values)
    if not values_list:
        return "0", []
    placeholders = ",".join("?" for _ in values_list)
    return f"{column} IN ({placeholders})", values_list
