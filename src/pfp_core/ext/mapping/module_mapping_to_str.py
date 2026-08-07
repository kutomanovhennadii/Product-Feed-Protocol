"""Mapping op: convert a value to string."""

from __future__ import annotations

from typing import Any, Mapping

from pfp_core.ext.ext_types import MISSING, MappingOpSpec, ParamSpec, TypeSpec


def _to_str(value: Any, args: Mapping[str, Any]) -> Any:
    """Convert `value` to `str`.

    Args:
        value: Input value.
        args: Operation args (unused).

    Returns:
        `MISSING`/`None` unchanged, otherwise `str(value)`.
    """
    _ = args
    if value is MISSING or value is None:
        return value
    return str(value)


def get_spec() -> MappingOpSpec:
    """Return the `MappingOpSpec` for the `to_str` operation."""
    return MappingOpSpec(
        op_id="to_str",
        input_type=TypeSpec("any", nullable=True, optional=True),
        output_type=TypeSpec("string", nullable=True, optional=True),
        args_spec=ParamSpec(),
        call=_to_str,
    )
