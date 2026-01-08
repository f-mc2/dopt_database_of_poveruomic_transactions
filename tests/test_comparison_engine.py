from typing import List
import unittest

try:
    import pandas as _pandas  # noqa: F401
except ModuleNotFoundError as exc:  # pragma: no cover - dependency gate
    raise unittest.SkipTest("pandas is required for comparison engine tests") from exc

from src import comparison_engine, tags
from src.types import Group, Node, Period
from tests.helpers import init_memory_db


def _add_tx(conn, date: str, amount: int, payer: str, payee: str, category: str, tag_list: List[str]):
    cursor = conn.execute(
        """
        INSERT INTO transactions (
            date_payment,
            date_application,
            amount_cents,
            payer,
            payee,
            payment_type,
            category,
            subcategory,
            notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            date,
            date,
            amount,
            payer,
            payee,
            "card",
            category,
            None,
            None,
        ),
    )
    tx_id = int(cursor.lastrowid)
    if tag_list:
        tags.set_transaction_tags(conn, tx_id, tag_list)


def _build_fixture(conn):
    _add_tx(conn, "2024-01-05", 1000, "alice", "charlie", "food", ["home"])
    _add_tx(conn, "2024-01-06", 2000, "dana", "bob", "food", ["home"])
    _add_tx(conn, "2024-01-07", 1500, "alice", "bob", "food", ["work"])
    _add_tx(conn, "2024-01-08", 500, "alice", "bob", "travel", ["home"])
    _add_tx(conn, "2024-01-09", 800, "eve", "frank", "food", ["home"])
    _add_tx(conn, "2024-01-10", 1200, "alice", "gina", "food", [])
    _add_tx(conn, "2024-01-11", 700, "henry", "bob", "food", [])
    _add_tx(conn, "2024-01-12", 900, "alice", "bob", "food", ["home", "work"])


def _row(df, node_label: str):
    row = df[
        (df["period_label"] == "P1")
        & (df["group_label"] == "G1")
        & (df["node_label"] == node_label)
    ]
    return row.iloc[0]


class TestComparisonEngine(unittest.TestCase):
    def test_role_mode_or_nodes(self) -> None:
        conn = init_memory_db()
        try:
            _build_fixture(conn)
            periods = [Period(label="P1", start_date="2024-01-01", end_date="2024-01-31")]
            groups = [Group(label="G1", payers=["alice"], payees=["bob"])]
            nodes = [
                Node(label="All categories", kind="all_categories"),
                Node(label="food", kind="category", category="food"),
                Node(label="home", kind="tag", tag="home"),
            ]
            df = comparison_engine.compute_comparison(
                conn,
                periods=periods,
                groups=groups,
                mode="role",
                node_mode="or",
                date_field="date_application",
                or_nodes=nodes,
            )

            food_row = _row(df, "food")
            self.assertEqual(int(food_row["tx_count"]), 6)
            self.assertEqual(int(food_row["inflow_cents"]), 5100)
            self.assertEqual(int(food_row["outflow_cents"]), 4600)
            self.assertEqual(int(food_row["net_cents"]), 500)

            home_row = _row(df, "home")
            self.assertEqual(int(home_row["tx_count"]), 4)
            self.assertEqual(int(home_row["inflow_cents"]), 3400)
            self.assertEqual(int(home_row["outflow_cents"]), 2400)
            self.assertEqual(int(home_row["net_cents"]), 1000)

            all_row = _row(df, "All categories")
            self.assertEqual(int(all_row["tx_count"]), 7)
            self.assertEqual(int(all_row["inflow_cents"]), 5600)
            self.assertEqual(int(all_row["outflow_cents"]), 5100)
            self.assertEqual(int(all_row["net_cents"]), 500)
        finally:
            conn.close()

    def test_matched_only_mode(self) -> None:
        conn = init_memory_db()
        try:
            _build_fixture(conn)
            periods = [Period(label="P1", start_date="2024-01-01", end_date="2024-01-31")]
            groups = [Group(label="G1", payers=["alice"], payees=["bob"])]
            nodes = [Node(label="food", kind="category", category="food")]
            df = comparison_engine.compute_comparison(
                conn,
                periods=periods,
                groups=groups,
                mode="matched_only",
                node_mode="or",
                date_field="date_application",
                or_nodes=nodes,
            )
            food_row = _row(df, "food")
            self.assertEqual(int(food_row["tx_count"]), 2)
            self.assertEqual(int(food_row["matched_flow_cents"]), 2400)
        finally:
            conn.close()

    def test_tag_match_any_all(self) -> None:
        conn = init_memory_db()
        try:
            _build_fixture(conn)
            periods = [Period(label="P1", start_date="2024-01-01", end_date="2024-01-31")]
            groups = [Group(label="G1", payers=["alice"], payees=["bob"])]
            entries = [Node(label="food", kind="category", category="food")]

            any_df = comparison_engine.compute_comparison(
                conn,
                periods=periods,
                groups=groups,
                mode="role",
                node_mode="and",
                date_field="date_application",
                and_entries=entries,
                and_tags=["home", "work"],
                tag_match=comparison_engine.TAG_MATCH_ANY,
            )
            any_row = _row(any_df, "food")
            self.assertEqual(int(any_row["tx_count"]), 4)
            self.assertEqual(int(any_row["inflow_cents"]), 4400)
            self.assertEqual(int(any_row["outflow_cents"]), 3400)

            all_df = comparison_engine.compute_comparison(
                conn,
                periods=periods,
                groups=groups,
                mode="role",
                node_mode="and",
                date_field="date_application",
                and_entries=entries,
                and_tags=["home", "work"],
                tag_match=comparison_engine.TAG_MATCH_ALL,
            )
            all_row = _row(all_df, "food")
            self.assertEqual(int(all_row["tx_count"]), 1)
            self.assertEqual(int(all_row["inflow_cents"]), 900)
            self.assertEqual(int(all_row["outflow_cents"]), 900)
        finally:
            conn.close()
