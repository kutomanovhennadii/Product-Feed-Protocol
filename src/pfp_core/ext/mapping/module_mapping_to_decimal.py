"""Mapping op: convert a value to Decimal."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from pfp_core.ext.ext_types import MISSING, MappingOpSpec, ParamSpec, TypeSpec


def _to_decimal(value: Any, args: Mapping[str, Any]) -> Any:
    """Convert `value` to `Decimal`.

    Args:
        value: Input value.
        args: Operation args (unused).

    Returns:
        `MISSING`/`None` unchanged, otherwise a `Decimal`.

    Raises:
        ValueError: If conversion fails or input is a bool.
    """
    _ = args
    if value is MISSING or value is None:
        return value
    if isinstance(value, bool):
        raise ValueError("to_decimal does not accept bool input.")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("to_decimal failed conversion.") from exc


def get_spec() -> MappingOpSpec:
    """Return the `MappingOpSpec` for the `to_decimal` operation."""
    return MappingOpSpec(
        op_id="to_decimal",
        input_type=TypeSpec("any", nullable=True, optional=True),
        output_type=TypeSpec("decimal", nullable=True, optional=True),
        args_spec=ParamSpec(),
        call=_to_decimal,
    )
