import unittest

from src import amounts


class TestAmounts(unittest.TestCase):
    def test_amount_parsing_valid(self) -> None:
        self.assertEqual(amounts.parse_amount_to_cents("10"), 1000)
        self.assertEqual(amounts.parse_amount_to_cents("10.5"), 1050)
        self.assertEqual(amounts.parse_amount_to_cents("10.50"), 1050)
        self.assertEqual(amounts.parse_amount_to_cents("0"), 0)

    def test_amount_parsing_invalid(self) -> None:
        invalid_values = ["", " ", "10,5", "1,000.00", "+10", "-10", "10.123", "abc"]
        for value in invalid_values:
            with self.assertRaises(ValueError):
                amounts.parse_amount_to_cents(value)

    def test_format_cents(self) -> None:
        self.assertEqual(amounts.format_cents(0), "0.00")
        self.assertEqual(amounts.format_cents(501), "5.01")
