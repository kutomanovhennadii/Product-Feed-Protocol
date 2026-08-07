"""Entrypoint tests for `pfp_core.engine.mapping_compiler.compile_mapping`."""

from typing import List, Tuple, cast

import pytest

import pfp_core.engine.mapping_compiler as mapping_compiler_mod
from pfp_core.engine.mapping_compiler import compile_mapping
from pfp_core.engine.plan_types import CompileDiagItem
from pfp_core.ext import ExtCatalog, build_builtin_catalog
from pfp_core.ext.ext_types import MappingOpSpec, ParamSpec, ProducerContext, TypeSpec


def _diag_codes(items: Tuple[CompileDiagItem, ...]) -> List[str]:
    """Return diagnostic codes list."""

    return [item.code for item in items]


def _schema_doc(mapping: dict, artifact_profile: str = "catalog_snapshot") -> dict:
    """Build minimal schema doc for compile_mapping tests."""

    return {
        "header": {"artifact_profile": artifact_profile},
        "mapping": mapping,
    }


def test_compile_mapping_uses_schema_presence_default_regardless_of_profile() -> None:
    """Presence default comes from schema-doc, not from artifact profile."""

    diagnostics: List[CompileDiagItem] = []
    _, _, field_presence = compile_mapping(
        _schema_doc(
            {
                "output_kind": "json_object",
                "presence": {"default": "emit_null_if_missing"},
                "fields": {"id": {"source": {"path": "id"}}},
            },
            artifact_profile="catalog_delta",
        ),
        build_builtin_catalog(),
        diagnostics,
    )

    assert diagnostics == []
    assert field_presence["id"].behavior == "emit_null_if_missing"


def test_compile_mapping_invalid_root_mapping_type() -> None:
    """Ensure mapping non-object returns empty defaults and root diagnostic."""

    diagnostics: List[CompileDiagItem] = []
    plan, field_types, presence = compile_mapping(
        {"header": {"artifact_profile": "catalog_snapshot"}, "mapping": "invalid"},
        build_builtin_catalog(),
        diagnostics,
    )

    assert plan.output_kind == "json_object"
    assert plan.output_order is None
    assert dict(plan.fields) == {}
    assert field_types == {}
    assert presence == {}
    assert _diag_codes(tuple(diagnostics)) == ["COMPILER_MAPPING_OUTPUT_KIND_INVALID"]


def test_compile_mapping_invalid_output_kind_and_fields_shape() -> None:
    """Ensure invalid output_kind and fields shape branches emit diagnostics."""

    diagnostics: List[CompileDiagItem] = []
    compile_mapping(
        _schema_doc(
            {
                "output_kind": "bad_kind",
                "fields": "bad",
            }
        ),
        build_builtin_catalog(),
        diagnostics,
    )

    codes = _diag_codes(tuple(diagnostics))
    assert "COMPILER_MAPPING_OUTPUT_KIND_INVALID" in codes
    assert "COMPILER_MAPPING_FIELDS_INVALID" in codes


def test_compile_mapping_invalid_fields_shapes_and_transforms() -> None:
    """Ensure invalid field block and transform shapes produce diagnostics."""

    diagnostics: List[CompileDiagItem] = []
    compile_mapping(
        _schema_doc(
            {
                "output_kind": "csv_row",
                "output_order": "bad",
                "fields": {
                    "a": "bad",
                    "b": {
                        "source": {"path": 1, "required": "bad"},
                        "transforms": "bad",
                    },
                    "c": {
                        "source": {"path": "x"},
                        "transforms": [
                            {"op": "to_str", "args": []},
                            {"op": "to_str", "on_missing": 1},
                        ],
                    },
                },
            }
        ),
        build_builtin_catalog(),
        diagnostics,
    )

    codes = _diag_codes(tuple(diagnostics))
    assert "COMPILER_MAPPING_FIELD_INVALID" in codes
    assert "SCHEMA_TYPE_OP_ARGS_INVALID" in codes
    assert "SCHEMA_TYPE_ENUM_INVALID" in codes
    assert "COMPILER_MAPPING_OUTPUT_ORDER_INVALID" in codes


def test_compile_mapping_skips_ops_with_invalid_type_contracts() -> None:
    """Ensure ops with unsupported input/output TypeId are diagnosed and not planned."""

    diagnostics: List[CompileDiagItem] = []
    catalog = ExtCatalog()

    class _UnsupportedTypeSpec:
        type_id = "unsupported"

    catalog.register_mapping_op(
        MappingOpSpec(
            op_id="to_str",
            input_type=cast(TypeSpec, _UnsupportedTypeSpec()),
            output_type=TypeSpec(type_id="string"),
            args_spec=ParamSpec(),
            call=lambda value, args: str(value),
        )
    )

    plan, _, _ = compile_mapping(
        _schema_doc(
            {
                "output_kind": "json_object",
                "fields": {
                    "id": {
                        "source": {"path": "id"},
                        "transforms": [{"op": "to_str"}],
                    }
                },
            }
        ),
        catalog,
        diagnostics,
    )

    field = plan.fields["id"]
    assert field.transforms == ()
    assert "SCHEMA_TYPE_INVALID_TYPE_ID" in _diag_codes(tuple(diagnostics))


def test_compile_mapping_transform_with_valid_args_and_on_missing() -> None:
    """Ensure transform branch with valid args and on_missing is compiled."""

    diagnostics: List[CompileDiagItem] = []
    plan, _, _ = compile_mapping(
        _schema_doc(
            {
                "output_kind": "json_object",
                "fields": {
                    "id": {
                        "source": {"path": "id"},
                        "transforms": [
                            {
                                "op": "to_str",
                                "args": {"x": "y"},
                                "on_missing": "pass",
                            }
                        ],
                    }
                },
            }
        ),
        build_builtin_catalog(),
        diagnostics,
    )

    assert diagnostics == []
    field = plan.fields["id"]
    assert len(field.transforms) == 1
    assert field.transforms[0].args == {"x": "y"}
    assert field.transforms[0].on_missing == "pass"


def test_compile_mapping_skips_invalid_and_unresolved_ops_in_plan() -> None:
    """Ensure invalid/unknown ops produce diagnostics but are not added to transforms."""

    diagnostics: List[CompileDiagItem] = []
    plan, _, _ = compile_mapping(
        _schema_doc(
            {
                "output_kind": "json_object",
                "fields": {
                    "id": {
                        "source": {"path": "id"},
                        "transforms": [
                            {"op": ""},
                            {"op": "not_allowlisted"},
                            {"op": "map_enum"},
                            {"op": "to_str"},
                        ],
                    }
                },
            }
        ),
        build_builtin_catalog(),
        diagnostics,
    )

    field = plan.fields["id"]
    assert [item.op_id for item in field.transforms] == ["to_str"]

    codes = _diag_codes(tuple(diagnostics))
    assert "SCHEMA_LINK_OP_INVALID" in codes
    assert "SCHEMA_LINK_OP_NOT_ALLOWED" in codes
    assert "SCHEMA_LINK_OP_NOT_FOUND" in codes


def test_compile_mapping_csv_output_order_duplicates_unknown_and_missing() -> None:
    """Ensure csv output_order catches unknown, duplicate and missing field cases."""

    diagnostics: List[CompileDiagItem] = []
    compile_mapping(
        _schema_doc(
            {
                "output_kind": "csv_row",
                "output_order": ["x", "x"],
                "fields": {
                    "id": {
                        "source": {"path": "id"},
                        "transforms": [{"op": "to_str"}],
                    }
                },
            }
        ),
        build_builtin_catalog(),
        diagnostics,
    )

    codes = _diag_codes(tuple(diagnostics))
    assert codes.count("COMPILER_FIELD_UNDEFINED") >= 1
    assert codes.count("COMPILER_MAPPING_OUTPUT_ORDER_INVALID") >= 2


def test_compile_mapping_auxiliary_outputs_are_immutable() -> None:
    """Ensure field_final_types and field_presence are immutable mappings."""

    diagnostics: List[CompileDiagItem] = []
    _, field_types, field_presence = compile_mapping(
        _schema_doc(
            {
                "output_kind": "json_object",
                "fields": {
                    "id": {
                        "source": {"path": "id"},
                        "transforms": [{"op": "to_str"}],
                    }
                },
            }
        ),
        build_builtin_catalog(),
        diagnostics,
    )

    assert diagnostics == []

    from typing import Any

    with pytest.raises(TypeError):
        cast(Any, field_types)["x"] = "string"

    with pytest.raises(TypeError):
        cast(Any, field_presence)["x"] = field_presence["id"]


def test_compile_mapping_passes_context_into_field_compiler(monkeypatch) -> None:
    """Forward optional ProducerContext from compile_mapping into field compilation."""
    diagnostics: List[CompileDiagItem] = []
    context = ProducerContext(tax_mapping={"mappings": {"Pet Supplies": "txcd_1"}})
    observed: dict[str, object] = {}

    def _fake_compile_field_mapping(**kwargs):
        observed.update(kwargs)
        return cast(
            object,
            type(
                "_FieldPlan",
                (),
                {
                    "final_type": None,
                    "presence": type("_Presence", (), {"behavior": "omit_missing"})(),
                },
            )(),
        )

    monkeypatch.setattr(
        mapping_compiler_mod._field_compiler,
        "compile_field_mapping",
        _fake_compile_field_mapping,
    )

    plan, _, _ = compile_mapping(
        _schema_doc(
            {
                "output_kind": "json_object",
                "fields": {
                    "id": {
                        "source": {"path": "id"},
                        "transforms": [{"op": "to_str"}],
                    }
                },
            }
        ),
        build_builtin_catalog(),
        diagnostics,
        context=context,
    )

    assert diagnostics == []
    assert observed["context"] is context
    assert sorted(plan.fields.keys()) == ["id"]
