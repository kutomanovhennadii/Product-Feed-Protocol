from __future__ import annotations

import copy
from typing import Any, Dict, List, Tuple

import pytest

import pfp_core.schema.schema_contract as contract_module
from pfp_core.schema.schema_contract import validate_schema_doc_format
from pfp_core.schema.schema_types import SchemaFormatError, SchemaRef

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


def test_missing_required_fields_collects_all_errors_deterministically() -> None:
    """Ensure missing required fields are collected and ordered deterministically."""

    broken_doc = copy.deepcopy(VALID_SCHEMA_DOC_MINIMAL)
    del broken_doc["header"]["artifact_profile"]
    del broken_doc["header"]["title"]
    del broken_doc["input"]["um_contract"]
    del broken_doc["output"]["writer_id"]

    with pytest.raises(SchemaFormatError) as exc:
        validate_schema_doc_format(broken_doc)

    assert _error_triplets(exc.value) == [
        (
            "SCHEMA_MISSING_FIELD",
            "header.artifact_profile",
            "Missing required field 'header.artifact_profile'.",
        ),
        (
            "SCHEMA_MISSING_FIELD",
            "header.title",
            "Missing required field 'header.title'.",
        ),
        (
            "SCHEMA_MISSING_FIELD",
            "input.um_contract",
            "Missing required field 'input.um_contract'.",
        ),
        (
            "SCHEMA_MISSING_FIELD",
            "output.writer_id",
            "Missing required field 'output.writer_id'.",
        ),
    ]


def test_validate_schema_doc_format_rejects_non_mapping_root() -> None:
    """Ensure validator rejects non-mapping root value."""

    with pytest.raises(SchemaFormatError) as exc:
        validate_schema_doc_format([])  # type: ignore[arg-type]

    assert exc.value.items[0].code == "SCHEMA_INVALID_TYPE"


def test_validate_schema_doc_format_reports_type_violations() -> None:
    """Ensure validator reports multiple field type violations."""

    broken_doc = copy.deepcopy(VALID_SCHEMA_DOC_MINIMAL)
    broken_doc["header"]["source_protocol"]["provider"] = 1
    broken_doc["output"]["artifact"]["file_ext"] = 1
    broken_doc["validation"]["rules"] = {}

    with pytest.raises(SchemaFormatError) as exc:
        validate_schema_doc_format(broken_doc)

    errors = _error_triplets(exc.value)
    assert (
        "SCHEMA_INVALID_TYPE",
        "header.source_protocol.provider",
        "header.source_protocol.provider must be a string.",
    ) in errors
    assert (
        "SCHEMA_INVALID_TYPE",
        "output.artifact.file_ext",
        "output.artifact.file_ext must be a string.",
    ) in errors
    assert (
        "SCHEMA_INVALID_TYPE",
        "validation.rules",
        "validation.rules must be a list.",
    ) in errors


def test_validate_schema_doc_format_handles_empty_doc() -> None:
    """Ensure empty schema doc collects missing-field errors."""

    with pytest.raises(SchemaFormatError) as exc:
        validate_schema_doc_format({})

    assert any(item.path == "header" for item in exc.value.items)
    assert any(item.path == "validation" for item in exc.value.items)


def test_validate_schema_doc_format_reports_non_mapping_section() -> None:
    """Ensure section expected as object reports SCHEMA_INVALID_TYPE."""

    broken_doc = copy.deepcopy(VALID_SCHEMA_DOC_MINIMAL)
    broken_doc["output"] = "not-an-object"

    with pytest.raises(SchemaFormatError) as exc:
        validate_schema_doc_format(broken_doc)

    assert (
        "SCHEMA_INVALID_TYPE",
        "output",
        "output must be an object.",
    ) in _error_triplets(exc.value)


def test_filename_header_mismatch_is_format_error() -> None:
    """Ensure filename/header mismatch yields SCHEMA_HEADER_FILENAME_MISMATCH."""

    broken_doc = copy.deepcopy(VALID_SCHEMA_DOC_MINIMAL)

    with pytest.raises(SchemaFormatError) as exc:
        validate_schema_doc_format(
            broken_doc,
            expected_ref=SchemaRef(
                protocol_id="openai.product_feed", schema_version="1.2.3"
            ),
        )

    assert any(
        item.code == "SCHEMA_HEADER_FILENAME_MISMATCH" for item in exc.value.items
    )


def test_private_helper_try_get_mapping_handles_none_and_non_mapping() -> None:
    assert contract_module._try_get_mapping(None, "header") is None
    assert contract_module._try_get_mapping({"header": "x"}, "header") is None


def test_private_helper_try_get_str_handles_none_and_non_str() -> None:
    assert contract_module._try_get_str(None, "protocol_id") is None
    assert contract_module._try_get_str({"protocol_id": 1}, "protocol_id") is None


def test_private_helper_try_get_field_handles_none() -> None:
    assert contract_module._try_get_field(None, "any") is None


def test_private_helper_try_get_field_returns_value_from_mapping() -> None:
    assert contract_module._try_get_field({"any": 42}, "any") == 42
