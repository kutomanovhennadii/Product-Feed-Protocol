"""Mapping op: convert a boolean availability flag to a Stripe availability enum."""

from __future__ import annotations

from typing import Any, Mapping

from pfp_core.ext.ext_types import MISSING, MappingOpSpec, ParamSpec, TypeSpec

_TRUE_STRINGS = frozenset(("true", "1", "yes"))
_FALSE_STRINGS = frozenset(("false", "0", "no"))


def _bool_to_availability(value: Any, args: Mapping[str, Any]) -> Any:
    """Convert Shopify ``availableForSale`` (Boolean) to Stripe availability enum.

    Args:
        value: Input value. Accepts ``bool``, ``str``, or ``int`` (0/1).
        args: Operation args (unused).

    Returns:
        ``MISSING``/``None`` unchanged.
        ``"in_stock"`` when truthy, ``"out_of_stock"`` when falsy.

    Raises:
        ValueError: If a string or int value cannot be unambiguously mapped.
        TypeError: If *value* is not a supported type.
    """
    _ = args
    if value is MISSING or value is None:
        return value
    if isinstance(value, bool):
        return "in_stock" if value else "out_of_stock"
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in _TRUE_STRINGS:
            return "in_stock"
        if normalized in _FALSE_STRINGS:
            return "out_of_stock"
        raise ValueError(
            f"bool_to_availability cannot parse string: {value!r}. "
            f"Expected one of: true/false/yes/no/1/0."
        )
    if isinstance(value, int):
        if value == 1:
            return "in_stock"
        if value == 0:
            return "out_of_stock"
        raise ValueError(
            f"bool_to_availability cannot parse int: {value!r}. Expected 0 or 1."
        )
    raise TypeError(
        f"bool_to_availability requires bool, str, or int; got {type(value).__name__!r}"
    )


def get_spec() -> MappingOpSpec:
    """Return the ``MappingOpSpec`` for the ``bool_to_availability`` operation."""
    return MappingOpSpec(
        op_id="bool_to_availability",
        input_type=TypeSpec("any", nullable=True, optional=True),
        output_type=TypeSpec("string", nullable=True, optional=True),
        args_spec=ParamSpec(),
        call=_bool_to_availability,
    )
