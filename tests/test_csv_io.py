import unittest

from src import csv_io
from tests.helpers import init_memory_db


class TestCsvIo(unittest.TestCase):
    def test_read_csv_headers_normalized(self) -> None:
        content = " Amount ; CATEGORY ; Date_Payment ; Payer \n10; Food; 2024-01-01; Alice"
        headers, rows = csv_io.read_csv_rows(content)
        self.assertEqual(headers, ["amount", "category", "date_payment", "payer"])
        self.assertEqual(len(rows), 1)

    def test_read_csv_duplicate_headers_rejected(self) -> None:
        content = "amount;Amount;category\n10;10;food"
        with self.assertRaises(ValueError):
            csv_io.read_csv_rows(content)

    def test_validate_rows_auto_copy_and_normalization(self) -> None:
        rows = [
            {
                "amount": "10.00",
                "category": " Food ",
                "date_payment": "2024-01-01",
                "payer": " Alice ",
            }
        ]
        parsed, errors = csv_io.validate_rows(rows)
        self.assertFalse(errors)
        self.assertEqual(parsed[0].category, "food")
        self.assertEqual(parsed[0].payer, "alice")
        self.assertEqual(parsed[0].date_application, "2024-01-01")
        conn = init_memory_db()
        try:
            csv_io.insert_transactions(conn, parsed)
            row = conn.execute("SELECT category, payer FROM transactions").fetchone()
            self.assertEqual(row[0], "food")
            self.assertEqual(row[1], "alice")
        finally:
            conn.close()

    def test_validate_rows_requires_payer_or_payee(self) -> None:
        rows = [
            {
                "amount": "10.00",
                "category": "food",
                "date_payment": "2024-01-01",
            }
        ]
        parsed, errors = csv_io.validate_rows(rows)
        self.assertFalse(parsed)
        self.assertTrue(any("payer or payee" in err.message.lower() for err in errors))

    def test_validate_rows_requires_date(self) -> None:
        rows = [
            {
                "amount": "10.00",
                "category": "food",
                "payer": "alice",
            }
        ]
        parsed, errors = csv_io.validate_rows(rows)
        self.assertFalse(parsed)
        self.assertTrue(any("date" in err.message.lower() for err in errors))

    def test_validate_rows_rejects_invalid_dates(self) -> None:
        rows = [
            {
                "amount": "10.00",
                "category": "food",
                "date_payment": "2024-02-30",
                "payer": "alice",
            }
        ]
        parsed, errors = csv_io.validate_rows(rows)
        self.assertFalse(parsed)
        self.assertTrue(any("date_payment" in err.message for err in errors))
