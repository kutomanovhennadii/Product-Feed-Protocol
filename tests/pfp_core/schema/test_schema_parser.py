from __future__ import annotations

import pytest

from pfp_core.schema.schema_parser import parse_schema_text
from pfp_core.schema.schema_types import SchemaErrorItem, SchemaFormatError


def test_parse_schema_text_accepts_valid_yaml() -> None:
    """Ensure valid YAML is parsed and returned as mapping."""

    parsed = parse_schema_text(
        "header:\n  protocol_id: stripe.product_feed", format="yaml"
    )
    assert parsed["header"]["protocol_id"] == "stripe.product_feed"


def test_parse_schema_text_accepts_valid_json() -> None:
    """Ensure valid JSON is parsed and returned as mapping."""

    parsed = parse_schema_text(
        '{"header": {"protocol_id": "stripe.product_feed"}}', format="json"
    )
    assert parsed["header"]["protocol_id"] == "stripe.product_feed"


def test_parse_schema_text_rejects_unsupported_format() -> None:
    """Ensure unsupported format is rejected with deterministic parse error."""

    with pytest.raises(SchemaFormatError) as exc:
        parse_schema_text("{}", format="toml")  # type: ignore[arg-type]

    assert exc.value.items == [
        SchemaErrorItem(
            code="SCHEMA_PARSE_ERROR",
            path="$",
            message="Unsupported schema format: 'toml'. Supported formats are: yaml, json.",
        )
    ]


def test_parse_error_message_is_deterministic() -> None:
    """Ensure parse error message includes format and exception type only."""

    with pytest.raises(SchemaFormatError) as exc:
        parse_schema_text("{", format="json")

    assert exc.value.items == [
        SchemaErrorItem(
            code="SCHEMA_PARSE_ERROR",
            path="$",
            message="Failed to parse schema text as json: JSONDecodeError",
        )
    ]


def test_parse_schema_text_rejects_non_mapping_root() -> None:
    """Ensure parser rejects non-mapping root values."""

    with pytest.raises(SchemaFormatError) as exc:
        parse_schema_text("[]", format="json")

    assert exc.value.items == [
        SchemaErrorItem(
            code="SCHEMA_INVALID_TYPE",
            path="$",
            message="Schema document root must be a mapping.",
        )
    ]
