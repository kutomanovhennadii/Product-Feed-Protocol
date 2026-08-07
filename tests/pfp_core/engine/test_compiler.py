"""Entrypoint tests for `pfp_core.engine.compiler.SchemaCompiler`."""

import copy
from types import SimpleNamespace
from typing import Any, Dict

import pfp_core.engine.compiler as compiler_mod
from pfp_core.engine.compiler import SchemaCompiler
from pfp_core.ext.ext_builtin_catalog import build_builtin_catalog
from pfp_core.ext.ext_types import ProducerContext

SKELETON_SCHEMA_DOC: Dict[str, Any] = {
    "header": {
        "protocol_id": "stripe.product_feed",
        "schema_version": "1.0.0",
        "artifact_profile": "catalog_snapshot",
        "title": "Stripe Product Feed v1",
    },
    "input": {"um_contract": "um.v1"},
    "modes": {},
    "output": {
        "writer_id": "csv",
        "writer_config": {"include_header": True},
        "artifact": {
            "content_type": "text/csv",
            "file_extension": ".csv",
        },
    },
    "mapping": {
        "output_kind": "csv_row",
        "presence": {"default": "omit_missing"},
        "output_order": ["id", "title"],
        "fields": {
            "id": {
                "source": {"path": "id", "required": True},
                "transforms": [{"op": "to_str"}],
            },
            "title": {
                "source": {"path": "attributes.title"},
                "transforms": [{"op": "to_str"}, {"op": "trim"}],
            },
        },
    },
    "validation": {
        "rules": [
            {
                "id": "req_id",
                "applies_to": {"field": "id", "mode": ["FULL", "DIFF", "DELETE"]},
                "module_id": "required",
                "config": {},
                "on_fail": {"code": "REQ_ID", "message": "id is required"},
            }
        ]
    },
}


def test_schema_compiler_builds_all_root_plans() -> None:
    compiler = SchemaCompiler(catalog=build_builtin_catalog())
    result = compiler.compile(copy.deepcopy(SKELETON_SCHEMA_DOC))

    assert result.is_valid is True
    assert result.diagnostics == ()
    assert result.writer_spec.writer_id == "csv"
    assert sorted(result.mapping_plan.fields.keys()) == ["id", "title"]
    assert len(result.validation_plan.rules) == 1


def test_schema_compiler_is_deterministic_for_same_invalid_input() -> None:
    compiler = SchemaCompiler(catalog=build_builtin_catalog())
    schema_doc = copy.deepcopy(SKELETON_SCHEMA_DOC)
    schema_doc["mapping"]["output_order"] = ["z_missing", "id"]
    schema_doc["validation"]["rules"][0]["applies_to"]["field"] = "unknown"

    first = compiler.compile(copy.deepcopy(schema_doc))
    second = compiler.compile(copy.deepcopy(schema_doc))

    first_tuples = [
        (item.DiagnosticSeverity, item.code, item.path, item.message)
        for item in first.diagnostics
    ]
    second_tuples = [
        (item.DiagnosticSeverity, item.code, item.path, item.message)
        for item in second.diagnostics
    ]

    assert first.is_valid is False
    assert first_tuples == second_tuples
    assert first_tuples == sorted(first_tuples)


def test_schema_compiler_passes_context_into_compile_mapping(
    monkeypatch,
) -> None:
    """Forward optional ProducerContext from SchemaCompiler into compile_mapping."""
    observed: dict[str, Any] = {}
    compiler = SchemaCompiler(catalog=build_builtin_catalog())
    context = ProducerContext(tax_mapping={"mappings": {"Pet Supplies": "txcd_1"}})

    def _fake_compile_mapping(*, schema_doc, catalog, diagnostics, context):
        observed["schema_doc"] = schema_doc
        observed["catalog"] = catalog
        observed["diagnostics"] = diagnostics
        observed["context"] = context
        return (SimpleNamespace(fields={}), {}, {})

    def _fake_compile_writer_spec(schema_doc, diagnostics):
        del schema_doc, diagnostics
        return type("_WriterSpec", (), {"writer_id": "csv"})()

    def _fake_compile_validation(**kwargs):
        del kwargs
        return (type("_ValidationPlan", (), {"rules": ()})(), set())

    monkeypatch.setattr(compiler_mod, "compile_mapping", _fake_compile_mapping)
    monkeypatch.setattr(compiler_mod, "compile_writer_spec", _fake_compile_writer_spec)
    monkeypatch.setattr(compiler_mod, "compile_validation", _fake_compile_validation)
    monkeypatch.setattr(
        compiler_mod,
        "check_presence_required_contradictions",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        compiler_mod, "sort_compile_diagnostics", lambda items: tuple(items)
    )

    result = compiler.compile(copy.deepcopy(SKELETON_SCHEMA_DOC), context=context)

    assert observed["context"] is context
    assert observed["schema_doc"]["header"]["protocol_id"] == "stripe.product_feed"
    assert result.is_valid is True
