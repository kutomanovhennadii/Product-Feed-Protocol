"""Mapping op: round numeric values using Decimal quantization."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, Mapping

from pfp_core.ext.ext_types import (
    MISSING,
    MappingOpSpec,
    ParamFieldSpec,
    ParamSpec,
    TypeSpec,
)


def _get_decimals(args: Mapping[str, Any]) -> int:
    """Extract and validate the `decimals` argument.

    Args:
        args: Operation args.

    Returns:
        The number of decimal places.

    Raises:
        ValueError: If `decimals` is missing or invalid.
    """
    decimals = args.get("decimals")
    if not isinstance(decimals, int) or decimals < 0:
        raise ValueError("round_decimal requires int arg 'decimals' >= 0.")
    return decimals


def _round_decimal(value: Any, args: Mapping[str, Any]) -> Any:
    """Round an input numeric value to a fixed number of decimal places.

    Args:
        value: Input value.
        args: Operation args. Requires `decimals: int`.

    Returns:
        `MISSING`/`None` unchanged, otherwise a quantized `Decimal`.

    Raises:
        ValueError: If conversion fails or args are invalid.
    """
    if value is MISSING or value is None:
        return value

    decimals = _get_decimals(args)
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("round_decimal failed conversion to Decimal.") from exc

    quantum = Decimal("1").scaleb(-decimals)
    return decimal_value.quantize(quantum, rounding=ROUND_HALF_UP)


def get_spec() -> MappingOpSpec:
    """Return the `MappingOpSpec` for the `round_decimal` operation."""
    return MappingOpSpec(
        op_id="round_decimal",
        input_type=TypeSpec("any", nullable=True, optional=True),
        output_type=TypeSpec("decimal", nullable=True, optional=True),
        args_spec=ParamSpec(
            fields=(
                ParamFieldSpec(
                    name="decimals",
                    type_spec=TypeSpec("int", nullable=False, optional=False),
                    required=True,
                    constraints={"min": 0},
                ),
            ),
            allow_extra=False,
        ),
        call=_round_decimal,
    )
