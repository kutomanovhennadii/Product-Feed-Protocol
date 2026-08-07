"""Tests for deterministic schema manifest generation."""

from __future__ import annotations

from pathlib import Path

import pytest

import pfp_core.schema.schema_manifest.manifest_builder as manifest_builder
from pfp_core.schema.schema_manifest import SchemaManifestError, build_manifest_document


def _write_schema(
    root: Path,
    *,
    rel_path: str,
    protocol_id: str,
    schema_version: str,
) -> Path:
    file_path = root / rel_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        (
            "header:\n"
            f'  protocol_id: "{protocol_id}"\n'
            f'  schema_version: "{schema_version}"\n'
            '  artifact_profile: "catalog_snapshot"\n'
            '  title: "x"\n'
            "  source_protocol:\n"
            '    provider: "x"\n'
            '    url: "https://example.com"\n'
            '    revision: "r1"\n'
            '    retrieved_at: "2026-03-08"\n'
            "input:\n"
            '  um_contract: "um.v1"\n'
            "modes:\n"
            '  supported: ["FULL", "DIFF", "DELETE"]\n'
            "output:\n"
            '  output_kind: "json_object"\n'
            '  writer_id: "jsonl"\n'
            "  writer_config:\n"
            '    line_terminator: "\\n"\n'
            "  artifact:\n"
            '    content_type: "application/x-ndjson"\n'
            '    file_ext: ".jsonl"\n'
            "mapping:\n"
            '  output_kind: "json_object"\n'
            "  fields:\n"
            "    id:\n"
            "      source:\n"
            '        path: "item_id"\n'
            "        required: true\n"
            "validation:\n"
            "  rules: []\n"
        ),
        encoding="utf-8",
    )
    return file_path


def test_build_manifest_document_contains_required_fields(tmp_path: Path) -> None:
    """Build manifest entries with path, protocol_id, schema_version, and sha256."""

    _write_schema(
        tmp_path,
        rel_path="openai.product_feed/openai.product_feed-1.0.0.yaml",
        protocol_id="openai.product_feed",
        schema_version="1.0.0",
    )

    manifest = build_manifest_document(tmp_path)

    assert manifest.version == 1
    assert len(manifest.entries) == 1
    entry = manifest.entries[0]
    assert entry.path == "openai.product_feed/openai.product_feed-1.0.0.yaml"
    assert entry.protocol_id == "openai.product_feed"
    assert entry.schema_version == "1.0.0"
    assert len(entry.sha256) == 64


def test_build_manifest_document_is_deterministic(tmp_path: Path) -> None:
    """Produce byte-stable manifest content across repeated generation."""

    _write_schema(
        tmp_path,
        rel_path="stripe.product_feed/stripe.product_feed-1.0.0.yaml",
        protocol_id="stripe.product_feed",
        schema_version="1.0.0",
    )

    first = build_manifest_document(tmp_path)
    second = build_manifest_document(tmp_path)

    assert first == second


def test_build_manifest_document_fails_on_duplicate_identity(tmp_path: Path) -> None:
    """Fail when two built-in schema files have same protocol/version identity."""

    _write_schema(
        tmp_path,
        rel_path="a/schema-a.yaml",
        protocol_id="stripe.product_feed",
        schema_version="1.0.0",
    )
    _write_schema(
        tmp_path,
        rel_path="b/schema-b.yaml",
        protocol_id="stripe.product_feed",
        schema_version="1.0.0",
    )

    with pytest.raises(SchemaManifestError, match="Duplicate schema identity"):
        build_manifest_document(tmp_path)


def test_build_manifest_document_fails_on_duplicate_path_from_collector(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fail when collector returns duplicate schema path entries."""

    schema_file = _write_schema(
        tmp_path,
        rel_path="openai.product_feed/openai.product_feed-1.0.0.yaml",
        protocol_id="openai.product_feed",
        schema_version="1.0.0",
    )
    monkeypatch.setattr(
        manifest_builder,
        "collect_builtin_schema_files",
        lambda root: [schema_file, schema_file],
    )

    with pytest.raises(SchemaManifestError, match="Duplicate built-in schema path"):
        build_manifest_document(tmp_path)
