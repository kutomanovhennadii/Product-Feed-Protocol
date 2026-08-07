"""Mapping op: truncate a string to a maximum length."""

from __future__ import annotations

from typing import Any, Mapping

from pfp_core.ext.ext_types import (
    MISSING,
    MappingOpSpec,
    ParamFieldSpec,
    ParamSpec,
    TypeSpec,
)


def _truncate(value: Any, args: Mapping[str, Any]) -> Any:
    """Truncate *value* to at most *args["max_length"]* characters.

    Args:
        value: Input value (may be ``MISSING`` or ``None``).
        args: Operation args. Requires ``max_length``.

    Returns:
        Truncated string, or original if within limit.

    Raises:
        ValueError: If required arg ``max_length`` is missing or invalid.
    """
    max_length = args.get("max_length")
    if (
        not isinstance(max_length, int)
        or isinstance(max_length, bool)
        or max_length < 1
    ):
        raise ValueError("truncate requires int arg 'max_length' >= 1.")

    if value is MISSING or value is None:
        return value

    s = str(value)
    if len(s) > max_length:
        return s[:max_length]
    return s


def get_spec() -> MappingOpSpec:
    """Return the ``MappingOpSpec`` for the ``truncate`` operation."""
    return MappingOpSpec(
        op_id="truncate",
        input_type=TypeSpec("any", nullable=True, optional=True),
        output_type=TypeSpec("string", nullable=True, optional=True),
        args_spec=ParamSpec(
            fields=(
                ParamFieldSpec(
                    name="max_length",
                    type_spec=TypeSpec("int", nullable=False, optional=False),
                    required=True,
                    constraints={"min": 1},
                ),
            ),
            allow_extra=False,
        ),
        call=_truncate,
    )
