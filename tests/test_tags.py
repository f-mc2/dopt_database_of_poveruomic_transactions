import unittest

from src import tags
from tests.helpers import init_memory_db


class TestTags(unittest.TestCase):
    def test_normalize_tag_rejects_commas_and_empty(self) -> None:
        with self.assertRaises(ValueError):
            tags.normalize_tag(" ")
        with self.assertRaises(ValueError):
            tags.normalize_tag("foo,bar")
        self.assertEqual(tags.normalize_tag(" Foo "), "foo")

    def test_parse_tags_dedupes(self) -> None:
        parsed = tags.parse_tags("Foo, foo , Bar")
        self.assertEqual(parsed, ["foo", "bar"])

    def test_rename_tag_merges(self) -> None:
        conn = init_memory_db()
        try:
            tx_id = conn.execute(
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
                    "2024-01-01",
                    "2024-01-01",
                    1000,
                    "alice",
                    "bob",
                    "card",
                    "food",
                    None,
                    None,
                ),
            ).lastrowid
            tags.set_transaction_tags(conn, int(tx_id), ["home"])
            tags.upsert_tag(conn, "work")
            tags.rename_tag(conn, "home", "work")
            current = tags.get_tags_for_transaction(conn, int(tx_id))
            self.assertEqual(current, ["work"])
            rows = conn.execute("SELECT name FROM tags ORDER BY name").fetchall()
            self.assertEqual([row[0] for row in rows], ["work"])
        finally:
            conn.close()
