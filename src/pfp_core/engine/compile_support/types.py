"""Compiler type helpers."""

from __future__ import annotations

from typing import Optional, Tuple, cast

from pfp_core.engine.plan_types import TypeId

ALLOWED_TYPE_IDS: Tuple[TypeId, ...] = (
    "string",
    "int",
    "decimal",
    "bool",
    "date",
    "datetime",
    "array[string]",
    "object",
)


def to_plan_type_id(raw_type_id: object) -> Optional[TypeId]:
    """Normalize external type id into compiler TypeId contract.

    Args:
        raw_type_id: Raw type id from ext module signature.

    Returns:
        Contract type id when recognized, otherwise None.
    """

    if isinstance(raw_type_id, str) and raw_type_id in ALLOWED_TYPE_IDS:
        return cast(TypeId, raw_type_id)
    return None


def is_type_mismatch(
    *,
    current_type: Optional[TypeId],
    expected_input: Optional[TypeId],
) -> bool:
    """Check transform-chain type mismatch for known compiler types.

    Args:
        current_type: Current inferred type in transform chain.
        expected_input: Expected input type for next transform.

    Returns:
        True if types are incompatible, otherwise False.
    """

    if current_type is None or expected_input is None:
        return False
    return current_type != expected_input


def is_validation_type_mismatch(
    *,
    field_type: Optional[TypeId],
    expected_value_type: TypeId,
) -> bool:
    """Check validation-vs-field type mismatch for known compiler types.

    Args:
        field_type: Inferred field type from mapping plan.
        expected_value_type: Validation module expected value type.

    Returns:
        True if types are incompatible, otherwise False.
    """

    if field_type is None:
        return False
    return field_type != expected_value_type
