"""Mapping compile helpers for field-level plan assembly."""

from __future__ import annotations

from types import MappingProxyType
from typing import Any, List, Mapping, Optional, cast

from pfp_core.engine.catalog_resolver import try_get_mapping_op
from pfp_core.engine.compile_support.diagnostics import add_error
from pfp_core.engine.compile_support.shapes import as_mapping
from pfp_core.engine.compile_support.types import is_type_mismatch, to_plan_type_id
from pfp_core.engine.mapping.compile_presence import compile_field_presence
from pfp_core.engine.plan_types import (
    CompileDiagItem,
    FieldMappingPlan,
    MappingOpCall,
    OnMissingBehavior,
    TypeId,
)
from pfp_core.ext.ext_catalog import ExtCatalog
from pfp_core.ext.ext_types import ProducerContext
from pfp_core.schema.schema_constraints import MAPPING_OP_ALLOWLIST

ALLOWED_ON_MISSING = ("pass", "default", "omit", "error")


def compile_field_mapping(
    *,
    field_id: str,
    field_mapping: Mapping[str, Any],
    field_path: str,
    global_presence_default: str,
    catalog: ExtCatalog,
    diagnostics: List[CompileDiagItem],
    context: Optional[ProducerContext] = None,
) -> FieldMappingPlan:
    """Compile one mapping field block.

    Args:
        field_id: Output field identifier.
        field_mapping: Field mapping payload from schema.
        field_path: Absolute path to field in schema document.
        global_presence_default: Global default presence semantic.
        catalog: Ext-modules catalog used for op resolution.
        diagnostics: Mutable diagnostics accumulator.
        context: Optional compile-time context reserved for transform preparation.

    Returns:
        Compiled field mapping plan.
    """

    source_path = ""
    is_required_source = False
    source_obj = as_mapping(field_mapping.get("source"))
    if source_obj is None:
        add_error(
            diagnostics,
            code="COMPILER_MAPPING_FIELD_INVALID",
            path=field_path + ".source",
            message=field_path + ".source must be an object.",
        )
    else:
        source_path_obj = source_obj.get("path")
        if isinstance(source_path_obj, str):
            source_path = source_path_obj
        else:
            add_error(
                diagnostics,
                code="COMPILER_MAPPING_FIELD_INVALID",
                path=field_path + ".source.path",
                message=field_path + ".source.path must be a string.",
            )
        required_obj = source_obj.get("required", False)
        if isinstance(required_obj, bool):
            is_required_source = required_obj
        else:
            add_error(
                diagnostics,
                code="COMPILER_MAPPING_FIELD_INVALID",
                path=field_path + ".source.required",
                message=field_path + ".source.required must be a boolean.",
            )

    presence = compile_field_presence(
        field_mapping=field_mapping,
        field_path=field_path,
        global_default=global_presence_default,
        diagnostics=diagnostics,
    )

    transforms: List[MappingOpCall] = []
    current_type: Optional[TypeId] = None
    transforms_obj = field_mapping.get("transforms", [])

    if transforms_obj is not None and not isinstance(transforms_obj, list):
        add_error(
            diagnostics,
            code="SCHEMA_TYPE_OP_ARGS_INVALID",
            path=field_path + ".transforms",
            message=field_path + ".transforms must be a list.",
        )
        transforms_obj = []

    for index, transform_raw in enumerate(cast(List[object], transforms_obj)):
        op_path = field_path + ".transforms[" + str(index) + "]"
        transform = as_mapping(transform_raw)
        if transform is None:
            add_error(
                diagnostics,
                code="SCHEMA_TYPE_OP_ARGS_INVALID",
                path=op_path,
                message=op_path + " must be an object.",
            )
            continue

        op_id_obj = transform.get("op")
        if not isinstance(op_id_obj, str) or not op_id_obj:
            add_error(
                diagnostics,
                code="SCHEMA_LINK_OP_INVALID",
                path=op_path + ".op",
                message="mapping transform op must be a non-empty string.",
            )
            continue
        op_id = op_id_obj

        if op_id not in MAPPING_OP_ALLOWLIST:
            add_error(
                diagnostics,
                code="SCHEMA_LINK_OP_NOT_ALLOWED",
                path=op_path + ".op",
                message="Mapping op '" + op_id + "' is not in allowlist.",
            )
            continue

        op_spec = try_get_mapping_op(
            catalog=catalog,
            op_id=op_id,
            path=op_path + ".op",
            diagnostics=diagnostics,
        )
        if op_spec is None:
            continue

        args_obj = transform.get("args")
        args: Optional[Mapping[str, object]] = None
        if args_obj is not None:
            args_map = as_mapping(args_obj)
            if args_map is None:
                add_error(
                    diagnostics,
                    code="SCHEMA_TYPE_OP_ARGS_INVALID",
                    path=op_path + ".args",
                    message=op_path + ".args must be an object.",
                )
            else:
                args = cast(Mapping[str, object], args_map)

        on_missing_obj = transform.get("on_missing")
        on_missing: Optional[OnMissingBehavior] = None
        if on_missing_obj is not None:
            if isinstance(on_missing_obj, str) and on_missing_obj in ALLOWED_ON_MISSING:
                on_missing = cast(OnMissingBehavior, on_missing_obj)
            else:
                add_error(
                    diagnostics,
                    code="SCHEMA_TYPE_ENUM_INVALID",
                    path=op_path + ".on_missing",
                    message=(
                        op_path
                        + ".on_missing must be one of: "
                        + ", ".join(ALLOWED_ON_MISSING)
                        + "."
                    ),
                )

        input_type: Optional[TypeId] = None
        output_type: Optional[TypeId] = None
        raw_input_type_id = op_spec.input_type.type_id
        input_type = to_plan_type_id(raw_input_type_id)
        if input_type is None and raw_input_type_id != "any":
            add_error(
                diagnostics,
                code="SCHEMA_TYPE_INVALID_TYPE_ID",
                path=op_path + ".op",
                message=(
                    "Mapping op input_type is not a supported TypeId: "
                    + str(raw_input_type_id)
                ),
            )
            continue

        raw_output_type_id = op_spec.output_type.type_id
        output_type = to_plan_type_id(raw_output_type_id)
        if output_type is None and raw_output_type_id != "any":
            add_error(
                diagnostics,
                code="SCHEMA_TYPE_INVALID_TYPE_ID",
                path=op_path + ".op",
                message=(
                    "Mapping op output_type is not a supported TypeId: "
                    + str(raw_output_type_id)
                ),
            )
            continue

        if is_type_mismatch(
            current_type=current_type,
            expected_input=input_type,
        ):
            add_error(
                diagnostics,
                code="SCHEMA_TYPE_MISMATCH",
                path=op_path + ".op",
                message=(
                    "Type mismatch in transform chain: expected '"
                    + str(input_type)
                    + "', got '"
                    + str(current_type)
                    + "'."
                ),
            )
        current_type = output_type

        resolved_args: Optional[Mapping[str, object]] = None
        if args is not None:
            enriched = dict(args)
            if op_spec.prepare is not None:
                enriched = dict(op_spec.prepare(enriched, context))
            resolved_args = cast(Mapping[str, object], MappingProxyType(enriched))

        transforms.append(
            MappingOpCall(
                op_id=op_id,
                args=resolved_args,
                on_missing=on_missing,
                input_type=input_type,
                output_type=output_type,
            )
        )

    return FieldMappingPlan(
        field_id=field_id,
        source_path=source_path,
        transforms=tuple(transforms),
        presence=presence,
        final_type=current_type,
        is_required_source=is_required_source,
    )
