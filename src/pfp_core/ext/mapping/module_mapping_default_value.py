"""Mapping op: substitute a default value when input is missing or null."""

from __future__ import annotations

from typing import Any, Mapping

from pfp_core.ext.ext_types import (
    MISSING,
    MappingOpSpec,
    ParamFieldSpec,
    ParamSpec,
    TypeSpec,
)


def _default_value(value: Any, args: Mapping[str, Any]) -> Any:
    """Return *value* unchanged, or substitute *args["value"]* when absent.

    Args:
        value: Input value (may be ``MISSING`` or ``None``).
        args: Operation args. Requires ``value``.

    Returns:
        Original *value* if present, otherwise *args["value"]*.

    Raises:
        ValueError: If required arg ``value`` is missing from *args*.
    """
    if "value" not in args:
        raise ValueError("default_value requires arg 'value'.")
    if value is MISSING or value is None:
        return args["value"]
    return value


def get_spec() -> MappingOpSpec:
    """Return the ``MappingOpSpec`` for the ``default_value`` operation."""
    return MappingOpSpec(
        op_id="default_value",
        input_type=TypeSpec("any", nullable=True, optional=True),
        output_type=TypeSpec("any", nullable=True, optional=True),
        args_spec=ParamSpec(
            fields=(
                ParamFieldSpec(
                    name="value",
                    type_spec=TypeSpec("any", nullable=True, optional=False),
                    required=True,
                ),
            ),
            allow_extra=False,
        ),
        call=_default_value,
    )
