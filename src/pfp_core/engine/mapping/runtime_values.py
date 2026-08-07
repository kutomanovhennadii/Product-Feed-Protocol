"""Mapping runtime helpers for source extraction and transform execution."""

from __future__ import annotations

from typing import Callable, List, Mapping, Tuple, TypeVar

from pfp_core.engine.plan_types import FieldMappingPlan, MappingOpCall
from pfp_core.ext.ext_catalog import ExtCatalog
from pfp_core.ext.ext_types import MISSING

TIssue = TypeVar("TIssue")


def _extract_by_source_path(
    input_record: Mapping[str, object], source_path: str
) -> object:
    """Extract value from record by dot-path with list-index support.

    Args:
        input_record: Input record for current item.
        source_path: Dot-separated path expression.

    Returns:
        Extracted value or `MISSING` when path cannot be resolved.
    """
    if not source_path:
        return MISSING
    current: object = input_record
    for segment in source_path.split("."):
        if isinstance(current, Mapping):
            if segment not in current:
                return MISSING
            current = current[segment]
            continue
        if isinstance(current, list):
            try:
                index = int(segment)
            except ValueError:
                return MISSING
            if index < 0 or index >= len(current):
                return MISSING
            current = current[index]
            continue
        return MISSING
    return current


def _apply_transform(
    *,
    catalog: ExtCatalog,
    current: object,
    op_call: MappingOpCall,
    field_plan: FieldMappingPlan,
    transform_index: int,
    issues: List[TIssue],
    issue_factory: Callable[[str, str, str], TIssue],
) -> Tuple[object, bool]:
    """Apply one transform call with deterministic error handling.

    Args:
        catalog: Ext modules catalog for resolving mapping operations.
        current: Current intermediate value.
        op_call: Transform invocation specification.
        field_plan: Field mapping plan containing transform sequence.
        transform_index: Index of transform in field transform chain.
        issues: Mutable issue list.
        issue_factory: Factory for runtime issue objects.

    Returns:
        Tuple of transformed value and stop flag.
    """

    path_prefix = (
        "mapping.fields."
        + field_plan.field_id
        + ".transforms["
        + str(transform_index)
        + "]"
    )

    if current is MISSING and op_call.on_missing is not None:
        if op_call.on_missing == "omit":
            return MISSING, True
        if op_call.on_missing == "pass":
            return MISSING, False
        if op_call.on_missing == "default":
            if op_call.args is not None and "default" in op_call.args:
                return op_call.args["default"], False
            issues.append(
                issue_factory(
                    "EXEC_MAPPING_ON_MISSING_DEFAULT_REQUIRED",
                    path_prefix + ".args.default",
                    "on_missing=default requires args.default value.",
                )
            )
            return MISSING, True
        if op_call.on_missing == "error":
            issues.append(
                issue_factory(
                    "EXEC_MAPPING_MISSING_ERROR",
                    path_prefix,
                    "on_missing=error triggered on missing input.",
                )
            )
            return MISSING, True

    try:
        op_spec = catalog.get_mapping_op(op_call.op_id)
    except KeyError:
        issues.append(
            issue_factory(
                "EXEC_MAPPING_OP_NOT_FOUND",
                path_prefix + ".op",
                "Mapping op '" + op_call.op_id + "' was not found in catalog.",
            )
        )
        return MISSING, True

    args = op_call.args or {}
    try:
        return op_spec.call(current, args), False
    except Exception:
        issues.append(
            issue_factory(
                "EXEC_MAPPING_OP_FAILED",
                path_prefix,
                "Mapping op '" + op_call.op_id + "' failed during execution.",
            )
        )
        return MISSING, True
