"""Tests for schema type contracts and errors."""

from pfp_core.schema.schema_types import (
    SchemaErrorItem,
    SchemaFormatError,
    SchemaNotFoundError,
    SchemaRef,
    sort_schema_error_items,
)


def test_sort_schema_error_items_orders_deterministically() -> None:
    """Schema error items are sorted by code, path, and message."""

    items = [
        SchemaErrorItem(code="B", path="z", message="later"),
        SchemaErrorItem(code="A", path="b", message="third"),
        SchemaErrorItem(code="A", path="a", message="first"),
    ]

    assert sort_schema_error_items(items) == [items[2], items[1], items[0]]


def test_schema_format_error_builds_sorted_message_and_context() -> None:
    """Schema format error stores sorted items and renders deterministic details."""

    items = [
        SchemaErrorItem(code="TYPE", path="body.price", message="must be decimal"),
        SchemaErrorItem(code="MISSING", path="header", message="required"),
    ]
    schema_ref = SchemaRef(protocol_id="stripe.product_feed", schema_version="1.0.0")

    error = SchemaFormatError(items, schema_ref=schema_ref, source="builtin")

    assert error.items[0].code == "MISSING"
    assert error.schema_ref is schema_ref
    assert error.source == "builtin"
    assert str(error) == (
        "Schema format error: MISSING at header: required; "
        "TYPE at body.price: must be decimal"
    )


def test_schema_format_error_without_items_uses_compact_default_message() -> None:
    """Empty error collections still render a stable default message."""

    assert str(SchemaFormatError([])) == "Schema format error"


def test_schema_not_found_error_reports_protocol_and_version() -> None:
    """Lookup error message includes canonical schema identity."""

    schema_ref = SchemaRef(protocol_id="stripe.product_feed", schema_version="1.0.0")

    error = SchemaNotFoundError(schema_ref)

    assert error.schema_ref is schema_ref
    assert "stripe.product_feed" in str(error)
    assert "1.0.0" in str(error)
