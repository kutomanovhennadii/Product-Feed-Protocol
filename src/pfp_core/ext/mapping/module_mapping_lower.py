"""Mapping op: lowercase string values."""

from __future__ import annotations

from typing import Any, Mapping

from pfp_core.ext.ext_types import MISSING, MappingOpSpec, ParamSpec, TypeSpec


def _lower(value: Any, args: Mapping[str, Any]) -> Any:
    """Convert a string input to lowercase.

    Args:
        value: Input value.
        args: Operation args (unused).

    Returns:
        `MISSING`/`None` unchanged, otherwise a lowercase string.

    Raises:
        ValueError: If input is not a string.
    """
    _ = args
    if value is MISSING or value is None:
        return value
    if not isinstance(value, str):
        raise ValueError("lower expects string input.")
    return value.lower()


def get_spec() -> MappingOpSpec:
    """Return the `MappingOpSpec` for the `lower` operation."""
    return MappingOpSpec(
        op_id="lower",
        input_type=TypeSpec("string", nullable=True, optional=True),
        output_type=TypeSpec("string", nullable=True, optional=True),
        args_spec=ParamSpec(),
        call=_lower,
    )
