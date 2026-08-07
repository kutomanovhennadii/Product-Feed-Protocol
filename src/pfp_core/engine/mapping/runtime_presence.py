"""Mapping runtime helpers for presence application."""

from __future__ import annotations

from typing import Callable, List, TypeVar

from pfp_core.engine.plan_types import FieldMappingPlan
from pfp_core.ext.ext_types import MISSING, Emission

TIssue = TypeVar("TIssue")


def _apply_presence(
    *,
    current: object,
    field_plan: FieldMappingPlan,
    issues: List[TIssue],
    issue_factory: Callable[[str, str, str], TIssue],
) -> Emission:
    """Convert intermediate value into emission according to presence rules.

    Args:
        current: Value after transform execution.
        field_plan: Field-level mapping plan with presence semantics.
        issues: Mutable issue list.
        issue_factory: Factory for runtime issue objects.

    Returns:
        Emission object consumed by writer conversion.
    """

    if isinstance(current, Emission):
        return current

    behavior = field_plan.presence.behavior
    if current is MISSING:
        if behavior == "omit_missing":
            return Emission(kind="OMIT")
        if behavior == "emit_null_if_missing":
            return Emission(kind="NULL")
        issues.append(
            issue_factory(
                "EXEC_MAPPING_PRESENCE_ERROR",
                "mapping.fields." + field_plan.field_id + ".presence",
                "error_if_missing triggered for missing field value.",
            )
        )
        return Emission(kind="OMIT")

    if current is None:
        return Emission(kind="NULL")

    return Emission(kind="VALUE", value=str(current))
