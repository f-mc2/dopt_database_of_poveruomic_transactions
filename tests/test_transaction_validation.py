from src.transaction_validation import validate_transaction_form


def test_validate_transaction_form_valid_payload() -> None:
    payload, errors = validate_transaction_form(
        amount_raw="12.30",
        category=" Food ",
        payer="Alice",
        payee="Bob",
        payment_type=" Card ",
        subcategory=" Dinner ",
        notes="  Note ",
        selected_tags=["Tag1", "tag1", "  Tag2 "],
        new_tag="NewTag",
    )

    assert errors == []
    assert payload is not None
    assert payload["amount_cents"] == 1230
    assert payload["category"] == "food"
    assert payload["payer"] == "alice"
    assert payload["payee"] == "bob"
    assert payload["payment_type"] == "card"
    assert payload["subcategory"] == "dinner"
    assert payload["notes"] == "Note"
    assert payload["tags"] == ["tag1", "tag2", "newtag"]


def test_validate_transaction_form_notes_blank() -> None:
    payload, errors = validate_transaction_form(
        amount_raw="1.00",
        category="food",
        payer="alice",
        payee=None,
        payment_type=None,
        subcategory=None,
        notes="   ",
        selected_tags=[],
        new_tag=None,
    )

    assert errors == []
    assert payload is not None
    assert payload["notes"] is None


def test_validate_transaction_form_missing_category() -> None:
    payload, errors = validate_transaction_form(
        amount_raw="1.00",
        category=" ",
        payer="alice",
        payee=None,
        payment_type=None,
        subcategory=None,
        notes=None,
        selected_tags=[],
        new_tag=None,
    )

    assert payload is None
    assert "Category is required" in errors


def test_validate_transaction_form_missing_parties() -> None:
    payload, errors = validate_transaction_form(
        amount_raw="1.00",
        category="food",
        payer=None,
        payee=None,
        payment_type=None,
        subcategory=None,
        notes=None,
        selected_tags=[],
        new_tag=None,
    )

    assert payload is None
    assert "Payer or payee is required" in errors


def test_validate_transaction_form_same_party() -> None:
    payload, errors = validate_transaction_form(
        amount_raw="1.00",
        category="food",
        payer="alice",
        payee="Alice",
        payment_type=None,
        subcategory=None,
        notes=None,
        selected_tags=[],
        new_tag=None,
    )

    assert payload is None
    assert "Payer and payee must be different" in errors


def test_validate_transaction_form_invalid_amount() -> None:
    payload, errors = validate_transaction_form(
        amount_raw="12.345",
        category="food",
        payer="alice",
        payee="bob",
        payment_type=None,
        subcategory=None,
        notes=None,
        selected_tags=[],
        new_tag=None,
    )

    assert payload is None
    assert any("Invalid amount format" in err for err in errors)


def test_validate_transaction_form_invalid_tags() -> None:
    payload, errors = validate_transaction_form(
        amount_raw="1.00",
        category="food",
        payer="alice",
        payee="bob",
        payment_type=None,
        subcategory=None,
        notes=None,
        selected_tags=["bad,tag"],
        new_tag=None,
    )

    assert payload is None
    assert "Tag names cannot contain commas" in errors
