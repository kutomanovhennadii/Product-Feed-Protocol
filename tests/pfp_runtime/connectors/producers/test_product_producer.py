"""Tests for ProductProducer.produce_stream."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence

from pfp_runtime.connectors.producers.product_producer import ProductProducer


class _LogPipelineStub:
    """Forwarding stub: routes log_process to stdlib so caplog can capture it."""

    def log_process(
        self, level: int, module_name: str, message: str, *_args: Any, **kwargs: Any
    ) -> None:
        import logging as _stdlib

        extra = kwargs.get("extra")
        _stdlib.getLogger(module_name).log(level, message, extra=extra)


_FULL_RECORD: Dict[str, Any] = {
    "product.item_id": "SKU-1",
    "product.title": "Widget",
    "product.description": "A widget",
    "product.url": "http://example.com/widget",
}


def _run(records: Sequence[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
    return list(
        ProductProducer(log_pipeline=_LogPipelineStub()).produce_stream(records)  # type: ignore[arg-type]
    )


def test_happy_path_returns_nested_dict() -> None:
    """Full valid record returns one nested dict record."""
    results = _run([_FULL_RECORD])

    assert len(results) == 1
    assert isinstance(results[0], Mapping)


def test_item_id_mapped_correctly() -> None:
    """product.item_id is placed in record['product']['item_id']."""
    result = _run([_FULL_RECORD])[0]

    assert result["product"]["item_id"] == "SKU-1"


def test_title_mapped_correctly() -> None:
    """product.title is placed in record['product']['title']."""
    result = _run([_FULL_RECORD])[0]

    assert result["product"]["title"] == "Widget"


def test_offer_price_unflattened() -> None:
    """Dot-path offer.price.* keys are unflattened into a nested dict."""
    record = {
        **_FULL_RECORD,
        "offer.price.amount": "9.99",
        "offer.price.currency": "USD",
    }

    result = _run([record])[0]

    assert result["offer"]["price"]["amount"] == "9.99"
    assert result["offer"]["price"]["currency"] == "USD"


def test_partial_offer_missing_currency_yields_no_money() -> None:
    """offer.price with only amount keeps only provided nested keys."""
    record = {**_FULL_RECORD, "offer.price.amount": "9.99"}

    result = _run([record])[0]

    assert result["offer"]["price"]["amount"] == "9.99"
    assert "currency" not in result["offer"]["price"]


def test_missing_item_id_skips_record() -> None:
    """Record without product.item_id is skipped."""
    record = {
        "product.title": "Widget",
        "product.description": "desc",
        "product.url": "http://x",
    }

    results = _run([record])

    assert results == []


def test_missing_title_is_allowed() -> None:
    """Record without product.title is allowed when product.item_id is present."""
    record = {
        "product.item_id": "X1",
        "product.description": "desc",
        "product.url": "http://x",
    }

    results = _run([record])

    assert len(results) == 1
    assert results[0]["product"]["item_id"] == "X1"


def test_multiple_records_one_invalid() -> None:
    """From three records where one is invalid, exactly two records are yielded."""
    invalid = {"product.title": "no id", "product.description": "d", "product.url": "u"}
    records = [_FULL_RECORD, invalid, {**_FULL_RECORD, "product.item_id": "SKU-2"}]

    results = _run(records)

    assert len(results) == 2
    assert results[0]["product"]["item_id"] == "SKU-1"
    assert results[1]["product"]["item_id"] == "SKU-2"


def test_empty_stream_returns_empty() -> None:
    """Empty input produces empty output without exceptions."""
    results = _run([])

    assert results == []


def test_produce_stream_is_lazy() -> None:
    """produce_stream returns a generator, not a materialised list."""
    import types

    gen = ProductProducer(log_pipeline=_LogPipelineStub()).produce_stream(  # type: ignore[arg-type]
        [_FULL_RECORD]
    )

    assert isinstance(gen, types.GeneratorType)


def test_inventory_availability_mapped() -> None:
    """inventory.availability is placed in record['inventory']['availability']."""
    record = {**_FULL_RECORD, "inventory.availability": "in_stock"}

    result = _run([record])[0]

    assert result["inventory"]["availability"] == "in_stock"


def test_stateless_repeated_calls_give_same_result() -> None:
    """Two sequential produce_stream calls on the same instance give identical results."""
    producer = ProductProducer(log_pipeline=_LogPipelineStub())  # type: ignore[arg-type]

    first = list(producer.produce_stream([_FULL_RECORD]))
    second = list(producer.produce_stream([_FULL_RECORD]))

    assert first == second


def test_optional_product_fields_propagated() -> None:
    """Optional product.* fields are preserved in the output record."""
    record = {
        **_FULL_RECORD,
        "product.image_url": "http://img.example.com/w.jpg",
        "product.product_category": "Electronics",
    }

    result = _run([record])[0]

    assert result["product"]["image_url"] == "http://img.example.com/w.jpg"
    assert result["product"]["product_category"] == "Electronics"


def test_unknown_top_level_key_ignored() -> None:
    """Record with only unknown top-level keys (no product.*) is skipped."""
    record = {"unknown.field": "value", "another.key": "val"}

    results = _run([record])

    assert results == []


def test_none_value_treated_as_missing() -> None:
    """A None value for a required field is treated as absent — record skipped."""
    record = {
        "product.item_id": None,
        "product.title": "Widget",
        "product.description": "desc",
        "product.url": "http://x",
    }

    results = _run([record])

    assert results == []


def test_unknown_product_subfield_preserved() -> None:
    """Unknown keys within the product sub-dict are preserved in the output record."""
    record = {**_FULL_RECORD, "product.nonexistent_custom_key": "some_value"}

    result = _run([record])[0]

    assert result["product"]["nonexistent_custom_key"] == "some_value"
    assert result["product"]["item_id"] == "SKU-1"


def test_offer_price_as_scalar_yields_no_money() -> None:
    """When offer.price is a scalar (not a dict), it remains scalar after unflatten."""
    record = {**_FULL_RECORD, "offer.price": "9.99"}

    result = _run([record])[0]

    assert result["offer"]["price"] == "9.99"
