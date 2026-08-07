"""Mapping op: convert an integer inventory quantity to a Stripe availability enum."""

from __future__ import annotations

from typing import Any, Mapping

from pfp_core.ext.ext_types import MISSING, MappingOpSpec, ParamSpec, TypeSpec


def _int_to_availability(value: Any, args: Mapping[str, Any]) -> Any:
    """Convert Shopify ``available`` inventory quantity (Integer/null) to Stripe availability enum.

    Args:
        value: Input value. Accepts ``int`` or ``None``.
        args: Operation args (unused).

    Returns:
        ``MISSING`` unchanged (passthrough).
        ``"in_stock"`` when value is a positive integer (> 0).
        ``"out_of_stock"`` when value is zero, negative, or ``None``.

    Raises:
        TypeError: If *value* is not ``int``, ``None``, or ``MISSING``.
    """
    _ = args
    if value is MISSING:
        return MISSING
    if value is None:
        return "out_of_stock"
    if isinstance(value, bool):
        raise TypeError(
            "int_to_availability requires int or None; got bool. "
            "Use bool_to_availability for boolean values."
        )
    if isinstance(value, int):
        return "in_stock" if value > 0 else "out_of_stock"
    raise TypeError(
        f"int_to_availability requires int or None; got {type(value).__name__!r}"
    )


def get_spec() -> MappingOpSpec:
    """Return the ``MappingOpSpec`` for the ``int_to_availability`` operation."""
    return MappingOpSpec(
        op_id="int_to_availability",
        input_type=TypeSpec("any", nullable=True, optional=True),
        output_type=TypeSpec("string", nullable=False, optional=True),
        args_spec=ParamSpec(),
        call=_int_to_availability,
    )
