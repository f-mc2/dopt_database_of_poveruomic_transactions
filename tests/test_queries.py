import unittest

from src import queries, tags
from tests.helpers import init_memory_db


def _insert_tx(conn, date: str, amount: int, payer: str, payee: str, category: str):
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
    return int(cursor.lastrowid)


class TestQueries(unittest.TestCase):
    def test_tags_sorted_and_any_filter(self) -> None:
        conn = init_memory_db()
        try:
            tx1 = _insert_tx(conn, "2024-01-01", 1000, "alice", "bob", "food")
            tx2 = _insert_tx(conn, "2024-01-02", 2000, "carol", "dave", "food")
            tx3 = _insert_tx(conn, "2024-01-03", 3000, "erin", "frank", "food")
            tags.set_transaction_tags(conn, tx1, ["zeta", "alpha"])
            tags.set_transaction_tags(conn, tx3, ["beta"])

            rows = queries.list_transactions(conn, {"tags": ["alpha", "beta"]})
            ids = [row["id"] for row in rows]
            self.assertCountEqual(ids, [tx1, tx3])

            tx1_row = next(row for row in rows if row["id"] == tx1)
            self.assertEqual(tx1_row["tags"], "alpha,zeta")
        finally:
            conn.close()
