"""Mapping op: convert a value to integer."""

from __future__ import annotations

from typing import Any, Mapping

from pfp_core.ext.ext_types import MISSING, MappingOpSpec, ParamSpec, TypeSpec


def _to_int(value: Any, args: Mapping[str, Any]) -> Any:
    """Convert `value` to `int`.

    Args:
        value: Input value.
        args: Operation args (unused).

    Returns:
        `MISSING`/`None` unchanged, otherwise an `int`.

    Raises:
        ValueError: If conversion is not possible or input is a bool.
    """
    _ = args
    if value is MISSING or value is None:
        return value
    if isinstance(value, bool):
        raise ValueError("to_int does not accept bool input.")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            raise ValueError("to_int cannot parse empty string.")
        return int(stripped)
    raise ValueError(f"to_int cannot convert value of type {type(value).__name__}.")


def get_spec() -> MappingOpSpec:
    """Return the `MappingOpSpec` for the `to_int` operation."""
    return MappingOpSpec(
        op_id="to_int",
        input_type=TypeSpec("any", nullable=True, optional=True),
        output_type=TypeSpec("int", nullable=True, optional=True),
        args_spec=ParamSpec(),
        call=_to_int,
    )
