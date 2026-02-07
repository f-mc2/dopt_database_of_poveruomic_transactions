import pandas as pd

from src import transactions_plus_grid as grid


def test_build_payload_handles_none_sentinel_and_tags_list() -> None:
    row = pd.Series(
        {
            "date_payment": "2024-01-02",
            "date_application": "2024-01-03",
            "amount_cents": "10.00",
            "payer": grid.NONE_SENTINEL,
            "payee": "Alice",
            "payment_type": grid.NONE_SENTINEL,
            "category": "Food",
            "subcategory": grid.NONE_SENTINEL,
            "notes": "   ",
            "tags": ["Tag1", "tag2", " tag1 "],
        }
    )

    payload, errors = grid.build_payload(row, subcategory_map={})

    assert errors == []
    assert payload is not None
    assert payload["amount_cents"] == 1000
    assert payload["payer"] is None
    assert payload["payee"] == "alice"
    assert payload["payment_type"] is None
    assert payload["category"] == "food"
    assert payload["subcategory"] is None
    assert payload["notes"] is None
    assert payload["tags"] == ["tag1", "tag2"]


def test_build_payload_subcategory_mismatch() -> None:
    row = pd.Series(
        {
            "date_payment": "2024-01-02",
            "date_application": "2024-01-03",
            "amount_cents": "5",
            "payer": "alice",
            "payee": "bob",
            "payment_type": None,
            "category": "food",
            "subcategory": "veg",
            "notes": None,
            "tags": "",
        }
    )

    payload, errors = grid.build_payload(row, subcategory_map={"veg": ["grocery"]})

    assert payload is None
    assert "Subcategory does not match the selected category" in errors


def test_ensure_row_ids_assigns_tmp_ids() -> None:
    df = pd.DataFrame({grid.ROW_ID_COLUMN: [None, "id:1"]})
    updated = grid.ensure_row_ids(df)

    assert grid.ROW_ID_COLUMN in updated.columns
    assert str(updated.loc[0, grid.ROW_ID_COLUMN]).startswith("tmp:")
    assert updated.loc[1, grid.ROW_ID_COLUMN] == "id:1"


def test_ensure_row_ids_adds_column() -> None:
    df = pd.DataFrame({"id": [1]})
    updated = grid.ensure_row_ids(df)

    assert grid.ROW_ID_COLUMN in updated.columns
    assert str(updated.loc[0, grid.ROW_ID_COLUMN]).startswith("tmp:")
