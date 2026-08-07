"""Mapping compile helpers for output order and tombstone settings."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Set, Tuple, cast

from pfp_core.engine.compile_support.diagnostics import add_error
from pfp_core.engine.compile_support.shapes import as_mapping
from pfp_core.engine.plan_types import CompileDiagItem


def compile_output_order(
    *,
    output_kind: str,
    mapping_section: Mapping[str, Any],
    known_fields: Set[str],
    diagnostics: List[CompileDiagItem],
) -> Optional[Tuple[str, ...]]:
    """Compile output order with csv-specific checks.

    Args:
        output_kind: Declared mapping output kind.
        mapping_section: Mapping section payload.
        known_fields: Set of compiled field identifiers.
        diagnostics: Mutable diagnostics accumulator.

    Returns:
        Tuple of output field ids for CSV output, otherwise None.
    """

    if output_kind != "csv_row":
        return None

    output_order_obj = mapping_section.get("output_order")
    if not isinstance(output_order_obj, list) or any(
        not isinstance(item, str) for item in output_order_obj
    ):
        add_error(
            diagnostics,
            code="COMPILER_MAPPING_OUTPUT_ORDER_INVALID",
            path="mapping.output_order",
            message="mapping.output_order must be list[str] for csv_row.",
        )
        return None

    output_order = cast(List[str], output_order_obj)
    seen: Dict[str, int] = {}
    for index, field_id in enumerate(output_order):
        if field_id not in known_fields:
            add_error(
                diagnostics,
                code="COMPILER_FIELD_UNDEFINED",
                path="mapping.output_order[" + str(index) + "]",
                message="Unknown field in output_order: '" + field_id + "'.",
            )
        if field_id in seen:
            add_error(
                diagnostics,
                code="COMPILER_MAPPING_OUTPUT_ORDER_INVALID",
                path="mapping.output_order[" + str(index) + "]",
                message=(
                    "Duplicate field in output_order: '"
                    + field_id
                    + "' (first index "
                    + str(seen[field_id])
                    + ")."
                ),
            )
        else:
            seen[field_id] = index

    for field_id in sorted(known_fields):
        if field_id not in seen:
            add_error(
                diagnostics,
                code="COMPILER_MAPPING_OUTPUT_ORDER_INVALID",
                path="mapping.fields." + field_id,
                message=(
                    "Field '"
                    + field_id
                    + "' is missing in mapping.output_order for csv_row."
                ),
            )

    return tuple(output_order)


def read_delete_tombstone_settings(
    *,
    mapping_section: Mapping[str, Any],
    diagnostics: List[CompileDiagItem],
) -> Tuple[bool, str, str]:
    """Read optional DELETE tombstone configuration from mapping section.

    Args:
        mapping_section: Mapping section payload.
        diagnostics: Mutable diagnostics accumulator.

    Returns:
        Tuple(enabled, flag_path, id_field).
    """
    config_obj = mapping_section.get("delete_tombstone")
    if config_obj is None:
        return False, "delete", "id"

    config = as_mapping(config_obj)
    if config is None:
        add_error(
            diagnostics,
            code="COMPILER_MAPPING_DELETE_TOMBSTONE_INVALID",
            path="mapping.delete_tombstone",
            message="mapping.delete_tombstone must be an object.",
        )
        return False, "delete", "id"

    enabled_obj = config.get("enabled", False)
    enabled = False
    if isinstance(enabled_obj, bool):
        enabled = enabled_obj
    else:
        add_error(
            diagnostics,
            code="COMPILER_MAPPING_DELETE_TOMBSTONE_INVALID",
            path="mapping.delete_tombstone.enabled",
            message="mapping.delete_tombstone.enabled must be a boolean.",
        )

    flag_path_obj = config.get("flag_path", "delete")
    flag_path = "delete"
    if isinstance(flag_path_obj, str) and flag_path_obj:
        flag_path = flag_path_obj
    else:
        add_error(
            diagnostics,
            code="COMPILER_MAPPING_DELETE_TOMBSTONE_INVALID",
            path="mapping.delete_tombstone.flag_path",
            message=("mapping.delete_tombstone.flag_path must be a non-empty string."),
        )

    id_field_obj = config.get("id_field", "id")
    id_field = "id"
    if isinstance(id_field_obj, str) and id_field_obj:
        id_field = id_field_obj
    else:
        add_error(
            diagnostics,
            code="COMPILER_MAPPING_DELETE_TOMBSTONE_INVALID",
            path="mapping.delete_tombstone.id_field",
            message="mapping.delete_tombstone.id_field must be a non-empty string.",
        )

    return enabled, flag_path, id_field
