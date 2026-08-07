"""Tests for schema manifest models parsing branches."""

from __future__ import annotations

import pytest

from pfp_core.schema.schema_manifest.manifest_models import (
    SchemaManifestError,
    parse_manifest_document,
)


def test_parse_manifest_document_rejects_non_integer_version() -> None:
    """Raise when manifest version field is not an integer."""

    with pytest.raises(SchemaManifestError, match="version"):
        parse_manifest_document({"version": "1", "entries": []})


def test_parse_manifest_document_rejects_non_list_entries() -> None:
    """Raise when manifest entries field is not a list."""

    with pytest.raises(SchemaManifestError, match="entries"):
        parse_manifest_document({"version": 1, "entries": {}})


def test_parse_manifest_document_rejects_non_mapping_entry() -> None:
    """Raise when one manifest entry is not an object mapping."""

    with pytest.raises(SchemaManifestError, match="index 0"):
        parse_manifest_document({"version": 1, "entries": ["bad"]})


def test_parse_manifest_document_rejects_invalid_entry_fields() -> None:
    """Raise when entry misses required typed manifest fields."""

    with pytest.raises(SchemaManifestError, match="path"):
        parse_manifest_document(
            {
                "version": 1,
                "entries": [
                    {
                        "path": "",
                        "protocol_id": "openai.product_feed",
                        "schema_version": "1.0.0",
                        "sha256": "abc",
                    }
                ],
            }
        )

    with pytest.raises(SchemaManifestError, match="protocol_id"):
        parse_manifest_document(
            {
                "version": 1,
                "entries": [
                    {
                        "path": "x.yaml",
                        "protocol_id": "",
                        "schema_version": "1.0.0",
                        "sha256": "abc",
                    }
                ],
            }
        )

    with pytest.raises(SchemaManifestError, match="schema_version"):
        parse_manifest_document(
            {
                "version": 1,
                "entries": [
                    {
                        "path": "x.yaml",
                        "protocol_id": "openai.product_feed",
                        "schema_version": "",
                        "sha256": "abc",
                    }
                ],
            }
        )

    with pytest.raises(SchemaManifestError, match="sha256"):
        parse_manifest_document(
            {
                "version": 1,
                "entries": [
                    {
                        "path": "x.yaml",
                        "protocol_id": "openai.product_feed",
                        "schema_version": "1.0.0",
                        "sha256": "",
                    }
                ],
            }
        )
