import datetime as dt

import pandas as pd

from src import date_utils


def test_parse_date_optional_empty() -> None:
    assert date_utils.parse_date_optional(None, "date") is None
    assert date_utils.parse_date_optional("", "date") is None
    assert date_utils.parse_date_optional("   ", "date") is None


def test_parse_date_optional_invalid_format() -> None:
    try:
        date_utils.parse_date_optional("2024/01/01", "date_payment")
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "Invalid date_payment format" in str(exc)


def test_parse_date_optional_invalid_date() -> None:
    try:
        date_utils.parse_date_optional("2024-02-30", "date_application")
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "Invalid date_application format" in str(exc)


def test_parse_date_optional_valid() -> None:
    assert date_utils.parse_date_optional("2024-01-02", "date") == "2024-01-02"


def test_coerce_date_variants() -> None:
    assert date_utils.coerce_date(dt.date(2024, 1, 2), "Date")[0] == "2024-01-02"
    assert date_utils.coerce_date(dt.datetime(2024, 1, 2, 5, 0), "Date")[0] == "2024-01-02"
    assert (
        date_utils.coerce_date(pd.Timestamp("2024-01-02 03:00"), "Date")[0]
        == "2024-01-02"
    )
    assert date_utils.coerce_date("2024-01-02", "Date")[0] == "2024-01-02"


def test_coerce_date_errors() -> None:
    assert date_utils.coerce_date(None, "Date")[1] == "Date is required"
    assert date_utils.coerce_date("", "Date")[1] == "Date is required"
    assert date_utils.coerce_date("2024/01/02", "Date")[1] == "Date must be YYYY-MM-DD"
