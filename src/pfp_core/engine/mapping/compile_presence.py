"""Mapping compile helpers for presence semantics."""

from __future__ import annotations

from typing import Any, List, Mapping, cast

from pfp_core.engine.compile_support.diagnostics import add_error
from pfp_core.engine.compile_support.shapes import as_mapping
from pfp_core.engine.plan_types import (
    CompileDiagItem,
    EmissionSemantics,
    FieldPresencePlan,
)

ALLOWED_PRESENCE = (
    "omit_missing",
    "emit_null_if_missing",
    "error_if_missing",
)


def compile_field_presence(
    *,
    field_mapping: Mapping[str, Any],
    field_path: str,
    global_default: str,
    diagnostics: List[CompileDiagItem],
) -> FieldPresencePlan:
    """Compile per-field presence semantics with global fallback.

    Args:
        field_mapping: Field mapping payload from schema.
        field_path: Absolute path to field in schema document.
        global_default: Global default presence semantic.
        diagnostics: Mutable diagnostics accumulator.

    Returns:
        Compiled field presence plan.
    """

    presence_raw = as_mapping(field_mapping.get("presence"))
    presence_path = field_path + ".presence"

    default_raw = global_default

    if presence_raw is not None:
        default_candidate = presence_raw.get("default", default_raw)
        if isinstance(default_candidate, str) and default_candidate in ALLOWED_PRESENCE:
            default_raw = default_candidate
        else:
            add_error(
                diagnostics,
                code="COMPILER_PRESENCE_DEFAULT_INVALID",
                path=presence_path + ".default",
                message=(
                    presence_path
                    + ".default must be one of: "
                    + ", ".join(ALLOWED_PRESENCE)
                    + "."
                ),
            )

    if default_raw not in ALLOWED_PRESENCE:
        default_raw = "omit_missing"

    return FieldPresencePlan(behavior=cast(EmissionSemantics, default_raw))


def read_global_presence(
    mapping_section: Mapping[str, Any],
    diagnostics: List[CompileDiagItem],
) -> str:
    """Read global presence defaults from `mapping.presence`.

    Args:
        mapping_section: Mapping section payload.
        diagnostics: Mutable diagnostics accumulator.

    Returns:
        Global default semantic.
    """

    presence_obj = as_mapping(mapping_section.get("presence")) or {}

    default_obj = presence_obj.get("default", "omit_missing")
    default = "omit_missing"
    if isinstance(default_obj, str) and default_obj in ALLOWED_PRESENCE:
        default = default_obj
    elif default_obj is not None:
        add_error(
            diagnostics,
            code="COMPILER_PRESENCE_DEFAULT_INVALID",
            path="mapping.presence.default",
            message=(
                "mapping.presence.default must be one of: "
                + ", ".join(ALLOWED_PRESENCE)
                + "."
            ),
        )

    return default
