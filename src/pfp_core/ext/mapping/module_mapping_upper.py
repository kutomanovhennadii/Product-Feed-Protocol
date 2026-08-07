"""Mapping op: uppercase string values."""

from __future__ import annotations

from typing import Any, Mapping

from pfp_core.ext.ext_types import MISSING, MappingOpSpec, ParamSpec, TypeSpec


def _upper(value: Any, args: Mapping[str, Any]) -> Any:
    """Convert a string input to uppercase.

    Args:
        value: Input value.
        args: Operation args (unused).

    Returns:
        `MISSING`/`None` unchanged, otherwise an uppercase string.

    Raises:
        ValueError: If input is not a string.
    """
    _ = args
    if value is MISSING or value is None:
        return value
    if not isinstance(value, str):
        raise ValueError("upper expects string input.")
    return value.upper()


def get_spec() -> MappingOpSpec:
    """Return the `MappingOpSpec` for the `upper` operation."""
    return MappingOpSpec(
        op_id="upper",
        input_type=TypeSpec("string", nullable=True, optional=True),
        output_type=TypeSpec("string", nullable=True, optional=True),
        args_spec=ParamSpec(),
        call=_upper,
    )
