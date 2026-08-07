"""Integration tests for the pfp_core.schema block."""

from __future__ import annotations

from pfp_core.engine.compiler import SchemaCompiler
from pfp_core.ext.ext_builtin_catalog import build_builtin_catalog
from pfp_core.schema import load_builtin_schema_registry


def test_builtin_schema_registry_feeds_schema_compiler_for_product_feed() -> None:
    """Built-in schema registry and compiler work together for product feed docs."""

    registry = load_builtin_schema_registry()
    schema_doc = registry.get("stripe.product_feed", "1.0.0")
    compiled = SchemaCompiler(catalog=build_builtin_catalog()).compile(schema_doc)

    assert compiled.is_valid is True
    assert compiled.diagnostics == ()
    assert compiled.artifact_profile == "catalog_delta"
    assert "id" in compiled.mapping_plan.fields


def test_builtin_schema_registry_lists_versions_for_loaded_protocol() -> None:
    """Built-in schema registry exposes deterministic version lookup after loading."""

    registry = load_builtin_schema_registry()

    assert registry.list("stripe.product_feed") == ["1.0.0"]
