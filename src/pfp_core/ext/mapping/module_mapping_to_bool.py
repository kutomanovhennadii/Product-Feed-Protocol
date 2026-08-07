"""Mapping op: convert a value to boolean."""

from __future__ import annotations

from typing import Any, Mapping

from pfp_core.ext.ext_types import MISSING, MappingOpSpec, ParamSpec, TypeSpec

_TRUE_SET = {"true", "1", "yes", "y", "on"}
_FALSE_SET = {"false", "0", "no", "n", "off"}


def _to_bool(value: Any, args: Mapping[str, Any]) -> Any:
    """Convert `value` to `bool`.

    Args:
        value: Input value.
        args: Operation args (unused).

    Returns:
        `MISSING`/`None` unchanged, otherwise a `bool`.

    Raises:
        ValueError: If conversion is not possible.
    """
    _ = args
    if value is MISSING or value is None:
        return value
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        if value in (0, 1):
            return bool(value)
        raise ValueError("to_bool accepts only int values 0 or 1.")
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in _TRUE_SET:
            return True
        if normalized in _FALSE_SET:
            return False
        raise ValueError("to_bool string value is not recognized.")
    raise ValueError(f"to_bool cannot convert value of type {type(value).__name__}.")


def get_spec() -> MappingOpSpec:
    """Return the `MappingOpSpec` for the `to_bool` operation."""
    return MappingOpSpec(
        op_id="to_bool",
        input_type=TypeSpec("any", nullable=True, optional=True),
        output_type=TypeSpec("bool", nullable=True, optional=True),
        args_spec=ParamSpec(),
        call=_to_bool,
    )
