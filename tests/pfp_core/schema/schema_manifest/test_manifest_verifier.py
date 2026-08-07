"""Tests for built-in schema integrity classification and fail-fast behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from pfp_core.schema.schema_manifest import (
    STATUS_BUILT_IN_MODIFIED,
    STATUS_BUILT_IN_VERIFIED,
    STATUS_EXTERNAL_SCHEMA,
    SchemaManifestError,
    build_manifest_document,
    classify_schema_integrity,
    verify_builtin_schema_or_raise,
)


def _write_schema(root: Path) -> Path:
    schema = root / "stripe.product_feed" / "stripe.product_feed-1.0.0.yaml"
    schema.parent.mkdir(parents=True, exist_ok=True)
    schema.write_text(
        (
            "header:\n"
            '  protocol_id: "stripe.product_feed"\n'
            '  schema_version: "1.0.0"\n'
            '  artifact_profile: "catalog_snapshot"\n'
            '  title: "x"\n'
            "  source_protocol:\n"
            '    provider: "stripe"\n'
            '    url: "https://example.com"\n'
            '    revision: "r1"\n'
            '    retrieved_at: "2026-03-08"\n'
            "input:\n"
            '  um_contract: "um.v1"\n'
            "modes:\n"
            '  supported: ["FULL", "DIFF", "DELETE"]\n'
            "output:\n"
            '  output_kind: "csv_row"\n'
            '  writer_id: "csv"\n'
            "  artifact:\n"
            '    content_type: "text/csv"\n'
            '    file_ext: ".csv"\n'
            "mapping:\n"
            '  output_kind: "csv_row"\n'
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
    return schema


def test_classify_schema_integrity_returns_built_in_verified(tmp_path: Path) -> None:
    """Classify unchanged built-in schema as built_in_verified."""

    schema = _write_schema(tmp_path)
    manifest = build_manifest_document(tmp_path)

    result = classify_schema_integrity(
        schema,
        schemas_root=tmp_path,
        manifest=manifest,
    )

    assert result.status == STATUS_BUILT_IN_VERIFIED
    assert result.relative_path == "stripe.product_feed/stripe.product_feed-1.0.0.yaml"


def test_verify_builtin_schema_or_raise_fails_on_modified_schema(
    tmp_path: Path,
) -> None:
    """Fail fast when built-in schema content diverges from manifest hash."""

    schema = _write_schema(tmp_path)
    manifest = build_manifest_document(tmp_path)
    schema.write_text(
        schema.read_text(encoding="utf-8") + "\n# drift\n", encoding="utf-8"
    )

    result = classify_schema_integrity(
        schema,
        schemas_root=tmp_path,
        manifest=manifest,
    )
    assert result.status == STATUS_BUILT_IN_MODIFIED

    with pytest.raises(SchemaManifestError, match="manifest mismatch"):
        verify_builtin_schema_or_raise(
            schema,
            schemas_root=tmp_path,
            manifest=manifest,
        )


def test_classify_schema_integrity_returns_external_for_outside_path(
    tmp_path: Path,
) -> None:
    """Classify schema outside built-in root as external_schema."""

    _write_schema(tmp_path)
    manifest = build_manifest_document(tmp_path)

    external_root = tmp_path.parent / "external"
    external_root.mkdir(parents=True, exist_ok=True)
    external_schema = external_root / "custom.yaml"
    external_schema.write_text("header: {}\n", encoding="utf-8")

    result = classify_schema_integrity(
        external_schema,
        schemas_root=tmp_path,
        manifest=manifest,
    )

    assert result.status == STATUS_EXTERNAL_SCHEMA


def test_classify_schema_integrity_marks_missing_manifest_entry_as_modified(
    tmp_path: Path,
) -> None:
    """Classify built-in file missing from manifest as built_in_modified."""

    schema = _write_schema(tmp_path)
    manifest = build_manifest_document(tmp_path)
    # Remove all entries to simulate a manifest drift where path record was dropped.
    manifest_without_entries = type(manifest)(version=manifest.version, entries=())

    result = classify_schema_integrity(
        schema,
        schemas_root=tmp_path,
        manifest=manifest_without_entries,
    )

    assert result.status == STATUS_BUILT_IN_MODIFIED
    assert result.expected_sha256 is None
