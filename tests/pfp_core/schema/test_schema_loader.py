"""Unit tests for built-in schema resolver contract."""

from __future__ import annotations

from pathlib import Path

import pytest

import pfp_core.schema.schema_loader as bl
from pfp_core.schema.schema_loader import (
    BuiltinSchemaResolutionError,
    load_builtin_schema_registry,
)
from pfp_core.schema.schema_manifest import build_manifest_document, get_manifest_path
from pfp_core.schema.schema_manifest.manifest_io import write_manifest_file
from pfp_core.schema.schema_registry import SchemaRegistry
from pfp_core.schema.schema_types import SchemaFormatError


def test_load_builtin_schema_registry_returns_schema_registry() -> None:
    """Ensure load_builtin_schema_registry returns SchemaRegistry instance."""

    registry = load_builtin_schema_registry()
    assert isinstance(registry, SchemaRegistry)


def test_load_builtin_registry_contains_stripe_product_feed_from_real_catalog() -> None:
    """Ensure built-in registry contains canonical pair from physical schema-doc."""

    registry = load_builtin_schema_registry()
    doc = registry.get("stripe.product_feed", "1.0.0")

    assert doc["header"]["protocol_id"] == "stripe.product_feed"
    assert doc["header"]["schema_version"] == "1.0.0"


def test_schema_layer_format_error_propagates_from_load_builtin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure SchemaFormatError from schema-layer is propagated without wrapping."""

    format_error = SchemaFormatError([])

    def _raise(*args: object, **kwargs: object) -> None:
        raise format_error

    monkeypatch.setattr(bl, "parse_schema_text", _raise)

    with pytest.raises(SchemaFormatError) as exc_info:
        load_builtin_schema_registry()

    assert exc_info.value is format_error


def test_missing_builtin_schemas_dir_raises_builtin_schema_resolution_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Ensure missing built-in directory raises BuiltinSchemaResolutionError."""

    monkeypatch.setattr(bl, "_BUILTIN_SCHEMAS_ROOT", tmp_path / "nonexistent")

    with pytest.raises(BuiltinSchemaResolutionError) as exc_info:
        load_builtin_schema_registry()

    assert "Built-in schemas directory not found" in str(exc_info.value)


def test_missing_builtin_manifest_raises_builtin_schema_resolution_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Ensure missing built-in manifest raises BuiltinSchemaResolutionError."""

    schema_root = tmp_path / "schemas"
    schema_root.mkdir()
    monkeypatch.setattr(bl, "_BUILTIN_SCHEMAS_ROOT", schema_root)

    with pytest.raises(BuiltinSchemaResolutionError, match="manifest file not found"):
        load_builtin_schema_registry()


def test_manifest_load_failure_is_wrapped_as_builtin_schema_resolution_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Manifest loading failures are wrapped into builtin-resolution errors."""

    schema_root = tmp_path / "schemas"
    schema_root.mkdir()
    get_manifest_path(schema_root).write_text("{}", encoding="utf-8")

    monkeypatch.setattr(bl, "_BUILTIN_SCHEMAS_ROOT", schema_root)

    def _raise(*args: object, **kwargs: object) -> None:
        raise ValueError("manifest broken")

    monkeypatch.setattr(bl, "load_manifest_file", _raise)

    with pytest.raises(BuiltinSchemaResolutionError, match="Failed to load"):
        load_builtin_schema_registry()


def test_schema_loader_exports_no_builtin_default_schema_ref_api() -> None:
    """Ensure provider-specific default schema resolver API is not exposed."""
    assert not hasattr(bl, "get_default_product_shell_schema_ref")


def test_load_builtin_registry_fails_fast_on_manifest_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Fail fast when built-in schema file hash diverges from schema manifest."""

    schema_root = tmp_path / "schemas"
    schema_file = schema_root / "stripe.product_feed" / "stripe.product_feed-1.0.0.yaml"
    schema_file.parent.mkdir(parents=True, exist_ok=True)
    schema_file.write_text(
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

    manifest = build_manifest_document(schema_root)
    write_manifest_file(get_manifest_path(schema_root), manifest)

    schema_file.write_text(
        schema_file.read_text(encoding="utf-8") + "\n# drift\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(bl, "_BUILTIN_SCHEMAS_ROOT", schema_root)

    with pytest.raises(BuiltinSchemaResolutionError, match="integrity verification"):
        load_builtin_schema_registry()
