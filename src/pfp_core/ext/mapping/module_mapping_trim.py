"""Mapping op: trim leading/trailing whitespace from strings."""

from __future__ import annotations

from typing import Any, Mapping

from pfp_core.ext.ext_types import MISSING, MappingOpSpec, ParamSpec, TypeSpec


def _trim(value: Any, args: Mapping[str, Any]) -> Any:
    """Trim whitespace from a string input.

    Args:
        value: Input value.
        args: Operation args (unused).

    Returns:
        `MISSING`/`None` unchanged, otherwise a trimmed string.

    Raises:
        ValueError: If input is not a string.
    """
    _ = args
    if value is MISSING or value is None:
        return value
    if not isinstance(value, str):
        raise ValueError("trim expects string input.")
    return value.strip()


def get_spec() -> MappingOpSpec:
    """Return the `MappingOpSpec` for the `trim` operation."""
    return MappingOpSpec(
        op_id="trim",
        input_type=TypeSpec("string", nullable=True, optional=True),
        output_type=TypeSpec("string", nullable=True, optional=True),
        args_spec=ParamSpec(),
        call=_trim,
    )
