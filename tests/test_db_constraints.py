import sqlite3
import unittest

from tests.helpers import init_memory_db


def _insert_transaction(conn, **overrides):
    data = {
        "date_payment": "2024-01-01",
        "date_application": "2024-01-01",
        "amount_cents": 1000,
        "payer": "alice",
        "payee": "bob",
        "payment_type": "card",
        "category": "food",
        "subcategory": "groceries",
        "notes": None,
    }
    data.update(overrides)
    conn.execute(
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
            data["date_payment"],
            data["date_application"],
            data["amount_cents"],
            data["payer"],
            data["payee"],
            data["payment_type"],
            data["category"],
            data["subcategory"],
            data["notes"],
        ),
    )


class TestDbConstraints(unittest.TestCase):
    def test_amount_non_negative(self) -> None:
        conn = init_memory_db()
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                _insert_transaction(conn, amount_cents=-1)
        finally:
            conn.close()

    def test_normalization_constraints(self) -> None:
        conn = init_memory_db()
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                _insert_transaction(conn, category=" Food ")
            with self.assertRaises(sqlite3.IntegrityError):
                _insert_transaction(conn, payer="Alice")
            with self.assertRaises(sqlite3.IntegrityError):
                _insert_transaction(conn, payment_type=" Cash ")
            with self.assertRaises(sqlite3.IntegrityError):
                _insert_transaction(conn, notes="   ")
        finally:
            conn.close()

    def test_payer_payee_invariants(self) -> None:
        conn = init_memory_db()
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                _insert_transaction(conn, payer=None, payee=None)
            with self.assertRaises(sqlite3.IntegrityError):
                _insert_transaction(conn, payer="alice", payee="alice")
        finally:
            conn.close()

    def test_date_shape_constraints(self) -> None:
        conn = init_memory_db()
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                _insert_transaction(conn, date_payment="2024-1-01")
            with self.assertRaises(sqlite3.IntegrityError):
                _insert_transaction(conn, date_application="2024-13-01")
        finally:
            conn.close()

    def test_tag_constraints(self) -> None:
        conn = init_memory_db()
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("INSERT INTO tags(name) VALUES (?)", (" Foo ",))
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("INSERT INTO tags(name) VALUES (?)", ("foo,bar",))
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute("INSERT INTO tags(name) VALUES (?)", ("",))
        finally:
            conn.close()
