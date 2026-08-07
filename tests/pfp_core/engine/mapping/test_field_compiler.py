from typing import Any, Dict, Mapping, cast

import pytest

from pfp_core.engine.mapping.field_compiler import compile_field_mapping
from pfp_core.engine.plan_types import CompileDiagItem
from pfp_core.ext import ExtCatalog, build_builtin_catalog
from pfp_core.ext.ext_types import MappingOpSpec, ParamSpec, ProducerContext, TypeSpec


def test_compile_field_mapping_builds_transform_chain() -> None:
    """Compile a valid single-transform mapping field without diagnostics."""
    diagnostics: list[CompileDiagItem] = []
    field = compile_field_mapping(
        field_id="id",
        field_mapping={
            "source": {"path": "id"},
            "transforms": [{"op": "to_str"}],
        },
        field_path="mapping.fields.id",
        global_presence_default="omit_missing",
        catalog=build_builtin_catalog(),
        diagnostics=diagnostics,
    )

    assert field.field_id == "id"
    assert field.presence.behavior == "omit_missing"
    assert len(field.transforms) == 1
    assert diagnostics == []


def test_compile_field_mapping_invalid_source_and_transform_shapes() -> None:
    """Report deterministic diagnostics for invalid source/transform payload shapes."""
    diagnostics: list[CompileDiagItem] = []
    field = compile_field_mapping(
        field_id="id",
        field_mapping={
            "source": {"path": 10, "required": "bad"},
            "transforms": [
                "bad",
                {"op": ""},
                {"op": "not_allowlisted"},
                {"op": "to_str", "args": []},
                {"op": "to_str", "on_missing": "bad"},
            ],
        },
        field_path="mapping.fields.id",
        global_presence_default="omit_missing",
        catalog=build_builtin_catalog(),
        diagnostics=diagnostics,
    )

    codes = {item.code for item in diagnostics}
    assert field.source_path == ""
    assert field.is_required_source is False
    assert "COMPILER_MAPPING_FIELD_INVALID" in codes
    assert "SCHEMA_TYPE_OP_ARGS_INVALID" in codes
    assert "SCHEMA_LINK_OP_INVALID" in codes
    assert "SCHEMA_LINK_OP_NOT_ALLOWED" in codes
    assert "SCHEMA_TYPE_ENUM_INVALID" in codes


def test_compile_field_mapping_reports_type_mismatch_chain() -> None:
    """Emit type-mismatch diagnostic when transform chain input/output contracts diverge."""
    diagnostics: list[CompileDiagItem] = []
    catalog = ExtCatalog()
    catalog.register_mapping_op(
        MappingOpSpec(
            op_id="to_str",
            input_type=TypeSpec(type_id="any"),
            output_type=TypeSpec(type_id="string"),
            args_spec=ParamSpec(),
            call=lambda value, args: str(value),
        )
    )
    catalog.register_mapping_op(
        MappingOpSpec(
            op_id="trim",
            input_type=TypeSpec(type_id="int"),
            output_type=TypeSpec(type_id="int"),
            args_spec=ParamSpec(),
            call=lambda value, args: value,
        )
    )
    field = compile_field_mapping(
        field_id="id",
        field_mapping={
            "source": {"path": "id"},
            "transforms": [{"op": "to_str"}, {"op": "trim"}],
        },
        field_path="mapping.fields.id",
        global_presence_default="omit_missing",
        catalog=catalog,
        diagnostics=diagnostics,
    )

    assert len(field.transforms) == 2
    assert any(item.code == "SCHEMA_TYPE_MISMATCH" for item in diagnostics)


def test_compile_field_mapping_reports_missing_source_object() -> None:
    """Reject missing source object and keep empty source path in compiled field."""
    diagnostics: list[CompileDiagItem] = []
    field = compile_field_mapping(
        field_id="id",
        field_mapping={"transforms": []},
        field_path="mapping.fields.id",
        global_presence_default="omit_missing",
        catalog=build_builtin_catalog(),
        diagnostics=diagnostics,
    )

    assert field.source_path == ""
    assert len(diagnostics) == 1
    assert diagnostics[0].code == "COMPILER_MAPPING_FIELD_INVALID"


def test_compile_field_mapping_reports_invalid_output_type_id() -> None:
    """Reject mapping op with unsupported output type id during compilation."""
    diagnostics: list[CompileDiagItem] = []
    catalog = ExtCatalog()

    class _UnsupportedTypeSpec:
        type_id = "unsupported"

    catalog.register_mapping_op(
        MappingOpSpec(
            op_id="to_str",
            input_type=TypeSpec(type_id="any"),
            output_type=cast(TypeSpec, _UnsupportedTypeSpec()),
            args_spec=ParamSpec(),
            call=lambda value, args: str(value),
        )
    )
    field = compile_field_mapping(
        field_id="id",
        field_mapping={"source": {"path": "id"}, "transforms": [{"op": "to_str"}]},
        field_path="mapping.fields.id",
        global_presence_default="omit_missing",
        catalog=catalog,
        diagnostics=diagnostics,
    )

    assert field.transforms == ()
    assert any(item.code == "SCHEMA_TYPE_INVALID_TYPE_ID" for item in diagnostics)


def test_compile_field_mapping_rejects_non_list_transforms_shape() -> None:
    """Reject non-list `transforms` payload with deterministic shape diagnostic."""
    diagnostics: list[CompileDiagItem] = []
    field = compile_field_mapping(
        field_id="id",
        field_mapping={
            "source": {"path": "id"},
            "transforms": {"op": "to_str"},
        },
        field_path="mapping.fields.id",
        global_presence_default="omit_missing",
        catalog=build_builtin_catalog(),
        diagnostics=diagnostics,
    )

    assert field.transforms == ()
    assert any(
        item.code == "SCHEMA_TYPE_OP_ARGS_INVALID"
        and item.path == "mapping.fields.id.transforms"
        for item in diagnostics
    )


def test_compile_field_mapping_allows_known_on_missing_behavior() -> None:
    """Preserve valid `on_missing` behavior in compiled transform metadata."""
    diagnostics: list[CompileDiagItem] = []
    field = compile_field_mapping(
        field_id="id",
        field_mapping={
            "source": {"path": "id"},
            "transforms": [{"op": "to_str", "on_missing": "default"}],
        },
        field_path="mapping.fields.id",
        global_presence_default="omit_missing",
        catalog=build_builtin_catalog(),
        diagnostics=diagnostics,
    )

    assert diagnostics == []
    assert len(field.transforms) == 1
    assert field.transforms[0].on_missing == "default"


def test_compile_field_mapping_reports_op_missing_in_catalog() -> None:
    """Skip transform and record diagnostic when allowlisted op is absent in catalog."""
    diagnostics: list[CompileDiagItem] = []
    field = compile_field_mapping(
        field_id="id",
        field_mapping={
            "source": {"path": "id"},
            "transforms": [{"op": "to_str"}],
        },
        field_path="mapping.fields.id",
        global_presence_default="omit_missing",
        catalog=ExtCatalog(),
        diagnostics=diagnostics,
    )

    assert field.transforms == ()
    assert any(item.code == "SCHEMA_LINK_OP_NOT_FOUND" for item in diagnostics)


def test_compile_field_mapping_reports_invalid_input_type_id() -> None:
    """Reject mapping op with unsupported input type id during compilation."""
    diagnostics: list[CompileDiagItem] = []
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

    field = compile_field_mapping(
        field_id="id",
        field_mapping={"source": {"path": "id"}, "transforms": [{"op": "to_str"}]},
        field_path="mapping.fields.id",
        global_presence_default="omit_missing",
        catalog=catalog,
        diagnostics=diagnostics,
    )

    assert field.transforms == ()
    assert any(item.code == "SCHEMA_TYPE_INVALID_TYPE_ID" for item in diagnostics)


def test_compile_field_mapping_calls_prepare_and_freezes_args() -> None:
    """Prepare callback enriches args once and stored args are immutable."""
    diagnostics: list[CompileDiagItem] = []
    catalog = ExtCatalog()
    calls: list[int] = []

    def _prepare(
        args: Mapping[str, Any],
        context: ProducerContext | None,
    ) -> Mapping[str, Any]:
        """Return enriched args and track invocation count."""
        assert context is None
        calls.append(1)
        return {**args, "prepared": "yes"}

    catalog.register_mapping_op(
        MappingOpSpec(
            op_id="to_str",
            input_type=TypeSpec(type_id="any"),
            output_type=TypeSpec(type_id="string"),
            args_spec=ParamSpec(),
            call=lambda value, args: str(value),
            prepare=_prepare,
        )
    )

    field = compile_field_mapping(
        field_id="id",
        field_mapping={
            "source": {"path": "id"},
            "transforms": [{"op": "to_str", "args": {"raw": "x"}}],
        },
        field_path="mapping.fields.id",
        global_presence_default="omit_missing",
        catalog=catalog,
        diagnostics=diagnostics,
    )

    assert diagnostics == []
    assert calls == [1]
    assert field.transforms[0].args == {"raw": "x", "prepared": "yes"}
    assert field.transforms[0].args is not None
    with pytest.raises(TypeError):
        cast(Dict[str, Any], field.transforms[0].args)["new"] = "value"


def test_compile_field_mapping_passes_context_to_two_arg_prepare() -> None:
    """Pass ProducerContext into prepare hooks that declare a context parameter."""
    diagnostics: list[CompileDiagItem] = []
    catalog = ExtCatalog()
    observed: dict[str, object] = {}
    context = ProducerContext(tax_mapping={"mappings": {"Pet Supplies": "txcd_1"}})

    def _prepare(
        args: Mapping[str, Any],
        context: ProducerContext | None,
    ) -> Mapping[str, Any]:
        """Return enriched args and capture the forwarded compile-time context."""
        observed["context"] = context
        return {**args, "prepared": "with-context"}

    catalog.register_mapping_op(
        MappingOpSpec(
            op_id="to_str",
            input_type=TypeSpec(type_id="any"),
            output_type=TypeSpec(type_id="string"),
            args_spec=ParamSpec(),
            call=lambda value, args: str(value),
            prepare=_prepare,
        )
    )

    field = compile_field_mapping(
        field_id="id",
        field_mapping={
            "source": {"path": "id"},
            "transforms": [{"op": "to_str", "args": {"raw": "x"}}],
        },
        field_path="mapping.fields.id",
        global_presence_default="omit_missing",
        catalog=catalog,
        diagnostics=diagnostics,
        context=context,
    )

    assert diagnostics == []
    assert observed["context"] is context
    assert field.transforms[0].args == {"raw": "x", "prepared": "with-context"}
