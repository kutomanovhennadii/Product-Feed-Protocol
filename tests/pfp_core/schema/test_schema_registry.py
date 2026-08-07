from __future__ import annotations

import copy
from typing import Any, Dict, List, Tuple

import pytest

from pfp_core.schema.schema_parser import parse_schema_text
from pfp_core.schema.schema_registry import SchemaRegistry
from pfp_core.schema.schema_types import (
    SchemaErrorItem,
    SchemaFormatError,
    SchemaNotFoundError,
)

VALID_SCHEMA_DOC_MINIMAL: Dict[str, Any] = {
    "header": {
        "protocol_id": "stripe.product_feed",
        "schema_version": "1.0.0",
        "artifact_profile": "catalog_snapshot",
        "title": "Stripe Product Feed Minimal",
        "source_protocol": {
            "provider": "stripe",
            "url": "https://docs.stripe.com/agentic-commerce/product-catalog",
            "revision": "2026-01",
            "retrieved_at": "2026-02-01",
        },
    },
    "input": {"um_contract": "um.v1"},
    "modes": {},
    "output": {
        "writer_id": "csv",
        "artifact": {
            "file_ext": ".csv",
            "content_type": "text/csv",
        },
    },
    "mapping": {"output_kind": "csv_row"},
    "validation": {"rules": []},
}


def _error_triplets(error: SchemaFormatError) -> List[Tuple[str, str, str]]:
    """Convert schema error items to comparable tuples."""

    return [(item.code, item.path, item.message) for item in error.items]


def test_register_get_list_happy_path() -> None:
    """Validate parse-register-get-list happy path for minimal schema doc."""

    yaml_text = """
header:
    protocol_id: stripe.product_feed
    schema_version: 1.0.0
    artifact_profile: catalog_snapshot
    title: Stripe Product Feed Minimal
    source_protocol:
        provider: stripe
        url: https://docs.stripe.com/agentic-commerce/product-catalog
        revision: 2026-01
        retrieved_at: "2026-02-01"
input:
    um_contract: um.v1
modes: {}
output:
    writer_id: csv
    artifact:
        file_ext: .csv
        content_type: text/csv
mapping:
    output_kind: csv_row
validation:
    rules: []
"""
    doc = parse_schema_text(yaml_text, format="yaml")

    registry = SchemaRegistry()
    registry.validate(doc, filename="stripe.product_feed-1.0.0.yaml")
    registry.register(doc, filename="stripe.product_feed-1.0.0.yaml")

    loaded = registry.get("stripe.product_feed", "1.0.0")
    assert loaded["header"]["protocol_id"] == "stripe.product_feed"
    assert registry.list("stripe.product_feed") == ["1.0.0"]


def test_duplicate_register_is_error() -> None:
    """Ensure duplicate register operation raises SCHEMA_DUPLICATE."""

    registry = SchemaRegistry()
    doc = copy.deepcopy(VALID_SCHEMA_DOC_MINIMAL)

    registry.register(doc, filename="stripe.product_feed-1.0.0.yaml")

    with pytest.raises(SchemaFormatError) as exc:
        registry.register(
            copy.deepcopy(VALID_SCHEMA_DOC_MINIMAL),
            filename="stripe.product_feed-1.0.0.yaml",
        )

    assert exc.value.items[0] == SchemaErrorItem(
        code="SCHEMA_DUPLICATE",
        path="$",
        message="Schema is already registered for protocol_id='stripe.product_feed', schema_version='1.0.0'.",
    )


def test_duplicate_register_preserves_source_and_filename_context() -> None:
    """Ensure duplicate error keeps both source and filename context."""

    registry = SchemaRegistry()
    registry.register(
        copy.deepcopy(VALID_SCHEMA_DOC_MINIMAL),
        filename="stripe.product_feed-1.0.0.yaml",
    )

    with pytest.raises(SchemaFormatError) as exc:
        registry.register(
            copy.deepcopy(VALID_SCHEMA_DOC_MINIMAL),
            source="embedded:stripe_v1",
            filename="stripe.product_feed-1.0.0.yaml",
        )

    assert exc.value.source == (
        "source=embedded:stripe_v1; filename=stripe.product_feed-1.0.0.yaml"
    )


def test_duplicate_register_preserves_source_only_context() -> None:
    """Ensure duplicate error keeps source context when filename is absent."""

    registry = SchemaRegistry()
    registry.register(
        copy.deepcopy(VALID_SCHEMA_DOC_MINIMAL), source="embedded:stripe_v1"
    )

    with pytest.raises(SchemaFormatError) as exc:
        registry.register(
            copy.deepcopy(VALID_SCHEMA_DOC_MINIMAL), source="embedded:stripe_v1"
        )

    assert exc.value.source == "embedded:stripe_v1"


def test_get_not_found_contains_schema_ref() -> None:
    """Ensure missing schema error includes schema_ref."""

    registry = SchemaRegistry()

    with pytest.raises(SchemaNotFoundError) as exc:
        registry.get("openai.product_feed", "9.9.9")

    assert exc.value.schema_ref is not None
    assert exc.value.schema_ref.protocol_id == "openai.product_feed"
    assert exc.value.schema_ref.schema_version == "9.9.9"


def test_list_orders_versions_lexicographically() -> None:
    """Ensure list() uses lexicographic ordering as Story 6b.2 contract."""

    registry = SchemaRegistry()

    for version in ("10.0.0", "2.0.0", "1.12.3", "1.2.10"):
        doc = copy.deepcopy(VALID_SCHEMA_DOC_MINIMAL)
        doc["header"]["schema_version"] = version
        registry.register(doc, filename=f"stripe.product_feed-{version}.yaml")

    assert registry.list("stripe.product_feed") == [
        "1.12.3",
        "1.2.10",
        "10.0.0",
        "2.0.0",
    ]


def test_registry_list_missing_protocol_returns_empty() -> None:
    """Ensure registry list returns empty list for unknown protocol."""

    registry = SchemaRegistry()
    assert registry.list("unknown.protocol") == []


def test_schema_format_error_message_for_empty_items() -> None:
    """Ensure SchemaFormatError keeps stable message for empty item list."""

    error = SchemaFormatError([])
    assert str(error) == "Schema format error"


def test_schema_format_error_items_are_sorted() -> None:
    """Ensure SchemaFormatError stores deterministic sorted items."""

    error = SchemaFormatError(
        [
            SchemaErrorItem(code="B", path="b", message="2"),
            SchemaErrorItem(code="A", path="a", message="1"),
        ]
    )
    assert _error_triplets(error) == [
        ("A", "a", "1"),
        ("B", "b", "2"),
    ]
