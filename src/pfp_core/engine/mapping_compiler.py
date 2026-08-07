"""Compilation of schema mapping section into `MappingPlan`."""

from __future__ import annotations

from types import MappingProxyType
from typing import Dict, List, Mapping, Optional, Tuple, cast

from pfp_core.engine.compile_support.diagnostics import add_error
from pfp_core.engine.compile_support.shapes import as_mapping
from pfp_core.engine.mapping import compile_presence as _compile_presence
from pfp_core.engine.mapping import field_compiler as _field_compiler
from pfp_core.engine.mapping import output as _mapping_output
from pfp_core.engine.plan_types import (
    CompileDiagItem,
    FieldMappingPlan,
    FieldPresencePlan,
    MappingPlan,
    OutputKind,
    TypeId,
)
from pfp_core.ext.ext_catalog import ExtCatalog
from pfp_core.ext.ext_types import ProducerContext
from pfp_core.schema.schema_types import SchemaDoc


def compile_mapping(
    schema_doc: SchemaDoc,
    catalog: ExtCatalog,
    diagnostics: List[CompileDiagItem],
    context: Optional[ProducerContext] = None,
) -> Tuple[
    MappingPlan,
    Mapping[str, Optional[TypeId]],
    Mapping[str, FieldPresencePlan],
]:
    """Compile `mapping` section into `MappingPlan`.

    Args:
        schema_doc: Source schema document.
        catalog: Ext-modules catalog used for op resolution.
        diagnostics: Mutable diagnostics accumulator.
        context: Optional compile-time context propagated to field compilation.

    Returns:
        Mapping plan, field final types, and field presence map.
    """

    mapping_section = as_mapping(schema_doc.get("mapping"))
    if mapping_section is None:
        add_error(
            diagnostics,
            code="COMPILER_MAPPING_OUTPUT_KIND_INVALID",
            path="mapping",
            message="mapping must be an object.",
        )
        return (
            MappingPlan(
                output_kind="json_object",
                output_order=None,
                fields=cast(Mapping[str, FieldMappingPlan], MappingProxyType({})),
                delete_tombstone_enabled=False,
                delete_tombstone_flag_path="delete",
                delete_tombstone_id_field="id",
            ),
            cast(Mapping[str, Optional[TypeId]], MappingProxyType({})),
            cast(Mapping[str, FieldPresencePlan], MappingProxyType({})),
        )

    global_presence_default = _compile_presence.read_global_presence(
        mapping_section,
        diagnostics,
    )

    output_kind_obj = mapping_section.get("output_kind")
    output_kind = "json_object"
    if isinstance(output_kind_obj, str) and output_kind_obj in (
        "csv_row",
        "json_object",
    ):
        output_kind = output_kind_obj
    else:
        add_error(
            diagnostics,
            code="COMPILER_MAPPING_OUTPUT_KIND_INVALID",
            path="mapping.output_kind",
            message="mapping.output_kind must be one of: csv_row, json_object.",
        )

    fields_obj = as_mapping(mapping_section.get("fields"))
    if fields_obj is None:
        add_error(
            diagnostics,
            code="COMPILER_MAPPING_FIELDS_INVALID",
            path="mapping.fields",
            message="mapping.fields must be an object.",
        )
        fields_obj = {}

    fields: Dict[str, FieldMappingPlan] = {}
    field_final_types: Dict[str, Optional[TypeId]] = {}
    field_presence: Dict[str, FieldPresencePlan] = {}

    for field_id in sorted(fields_obj.keys()):
        field_path = "mapping.fields." + field_id
        field_mapping = as_mapping(fields_obj.get(field_id))
        if field_mapping is None:
            add_error(
                diagnostics,
                code="COMPILER_MAPPING_FIELD_INVALID",
                path=field_path,
                message=field_path + " must be an object.",
            )
            continue

        compiled_field = _field_compiler.compile_field_mapping(
            field_id=field_id,
            field_mapping=field_mapping,
            field_path=field_path,
            global_presence_default=global_presence_default,
            catalog=catalog,
            diagnostics=diagnostics,
            context=context,
        )
        fields[field_id] = compiled_field
        field_final_types[field_id] = compiled_field.final_type
        field_presence[field_id] = compiled_field.presence

    output_order = _mapping_output.compile_output_order(
        output_kind=output_kind,
        mapping_section=mapping_section,
        known_fields=set(fields.keys()),
        diagnostics=diagnostics,
    )
    (
        delete_tombstone_enabled,
        delete_tombstone_flag_path,
        delete_tombstone_id_field,
    ) = _mapping_output.read_delete_tombstone_settings(
        mapping_section=mapping_section,
        diagnostics=diagnostics,
    )

    return (
        MappingPlan(
            output_kind=cast(OutputKind, output_kind),
            output_order=output_order,
            fields=cast(Mapping[str, FieldMappingPlan], MappingProxyType(dict(fields))),
            delete_tombstone_enabled=delete_tombstone_enabled,
            delete_tombstone_flag_path=delete_tombstone_flag_path,
            delete_tombstone_id_field=delete_tombstone_id_field,
        ),
        cast(
            Mapping[str, Optional[TypeId]],
            MappingProxyType(dict(field_final_types)),
        ),
        cast(
            Mapping[str, FieldPresencePlan],
            MappingProxyType(dict(field_presence)),
        ),
    )
