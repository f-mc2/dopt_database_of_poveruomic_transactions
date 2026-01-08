import sqlite3
import unittest

from src import db
from tests.helpers import init_db_at, temp_db_path


class TestPragmasAndBackup(unittest.TestCase):
    def test_pragmas_set_on_connect(self) -> None:
        db_path = temp_db_path("pragma")
        conn = init_db_at(db_path)
        try:
            fk_row = conn.execute("PRAGMA foreign_keys").fetchone()
            self.assertEqual(fk_row[0], 1)
            journal_row = conn.execute("PRAGMA journal_mode").fetchone()
            self.assertEqual(journal_row[0].lower(), "wal")
        finally:
            conn.close()

    def test_backup_snapshot_matches(self) -> None:
        db_path = temp_db_path("backup_source")
        conn = init_db_at(db_path)
        try:
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
            )
            conn.commit()

            backup_path = temp_db_path("backup")
            db.backup_db(conn, str(backup_path))
        finally:
            conn.close()

        backup_conn = sqlite3.connect(str(backup_path))
        try:
            row = backup_conn.execute("SELECT COUNT(*) FROM transactions").fetchone()
            self.assertEqual(row[0], 1)
        finally:
            backup_conn.close()
