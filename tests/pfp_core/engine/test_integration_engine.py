"""Integration tests for the pfp_core.engine block."""

from __future__ import annotations

from typing import Any, cast

from pfp_core.engine.compiler import SchemaCompiler
from pfp_core.engine.mapping_executor import MappingExecutor
from pfp_core.engine.validation_executor import ValidationExecutor
from pfp_core.ext.ext_builtin_catalog import build_builtin_catalog
from pfp_core.ext.ext_types import Emission


def _schema_doc() -> dict[str, Any]:
    """Return a schema document that exercises compile, validate, and map.

    Returns:
        Schema document covering the minimal engine integration flow.
    """

    return {
        "header": {
            "protocol_id": "test.engine.integration",
            "schema_version": "1.0.0",
            "artifact_profile": "catalog_snapshot",
            "title": "Engine integration schema",
            "source_protocol": {
                "provider": "test",
                "url": "N/A",
                "revision": "snapshot",
                "retrieved_at": "2026-05-07",
            },
        },
        "input": {"um_contract": "Unified Model items as dict-like objects."},
        "output": {
            "output_kind": "json_object",
            "writer_id": "jsonl",
            "writer_config": {
                "ensure_ascii": False,
                "sort_keys": True,
                "omit_nulls": False,
                "line_terminator": "\n",
            },
            "artifact": {
                "content_type": "application/x-ndjson",
                "file_ext": ".jsonl",
                "file_extension": ".jsonl",
                "encoding": "utf-8",
            },
        },
        "mapping": {
            "output_kind": "json_object",
            "presence": {"default": "omit_missing"},
            "fields": {
                "sku": {
                    "source": {"path": "sku", "required": False},
                    "transforms": [{"op": "to_str"}, {"op": "trim"}],
                },
                "stock": {
                    "source": {"path": "stock", "required": False},
                    "transforms": [{"op": "to_int"}],
                },
            },
        },
        "validation": {
            "rules": [
                {
                    "id": "sku_required",
                    "applies_to": {"field": "sku"},
                    "module_id": "required",
                    "config": {},
                    "on_fail": {
                        "code": "SKU_REQUIRED",
                        "message": "sku is required",
                        "severity_hint": "ERROR",
                    },
                },
                {
                    "id": "stock_range",
                    "applies_to": {"field": "stock"},
                    "module_id": "range",
                    "config": {"min": 0, "max": 10},
                    "on_fail": {
                        "code": "STOCK_RANGE",
                        "message": "stock must be within the allowed range",
                        "severity_hint": "ERROR",
                    },
                },
            ]
        },
    }


def test_engine_compile_validate_and_map_happy_path() -> None:
    """Engine block compiles the schema and executes validation and mapping."""

    catalog = build_builtin_catalog()
    compiled = SchemaCompiler(catalog=catalog).compile(_schema_doc())

    assert compiled.is_valid is True
    assert compiled.diagnostics == ()

    validation = ValidationExecutor(catalog=catalog).run_one(
        plan=compiled.validation_plan,
        input_record={"sku": "  SKU-1  ", "stock": "3"},
        artifact_profile="catalog_snapshot",
    )
    assert validation.decision == "PASS"
    assert validation.items == ()

    mapped = MappingExecutor(catalog=catalog).run_one(
        plan=compiled.mapping_plan,
        input_record={"sku": "  SKU-1  ", "stock": "3"},
        artifact_profile="catalog_snapshot",
    )

    output = cast(dict[str, Emission], mapped.output)
    assert mapped.issues == ()
    assert output["sku"] == Emission(kind="VALUE", value="SKU-1")
    assert output["stock"] == Emission(kind="VALUE", value="3")


def test_engine_validation_reports_rule_failures_from_compiled_plan() -> None:
    """Engine block propagates validation failures from the compiled rule plan."""

    catalog = build_builtin_catalog()
    compiled = SchemaCompiler(catalog=catalog).compile(_schema_doc())

    validation = ValidationExecutor(catalog=catalog).run_one(
        plan=compiled.validation_plan,
        input_record={"stock": "99"},
        artifact_profile="catalog_snapshot",
    )

    assert validation.decision == "FAIL"
    assert {item.code for item in validation.items} == {"SKU_REQUIRED", "STOCK_RANGE"}


def test_engine_compilation_surfaces_invalid_schema_diagnostics() -> None:
    """Engine block returns deterministic compile diagnostics for invalid schemas."""

    invalid_doc = _schema_doc()
    invalid_doc["mapping"]["fields"]["broken"] = {  # type: ignore[index]
        "source": {"path": "broken", "required": False},
        "transforms": [{"op": "missing_op"}],
    }

    compiled = SchemaCompiler(catalog=build_builtin_catalog()).compile(invalid_doc)

    assert compiled.is_valid is False
    assert any(
        item.code == "SCHEMA_LINK_OP_NOT_ALLOWED" for item in compiled.diagnostics
    )
