"""Mapping op: format numeric values as money-like strings."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, Mapping, Tuple

from pfp_core.ext.ext_types import (
    MISSING,
    MappingOpSpec,
    ParamFieldSpec,
    ParamSpec,
    TypeSpec,
)


def _parse_config(args: Mapping[str, Any]) -> Tuple[int, str, str]:
    """Parse and validate formatting args.

    Args:
        args: Operation args.

    Returns:
        Tuple of (decimals, pattern, currency).

    Raises:
        ValueError: If required args are missing or invalid.
    """
    decimals = args.get("decimals")
    pattern = args.get("pattern")
    currency = args.get("currency", "")

    if not isinstance(decimals, int) or decimals < 0:
        raise ValueError("format_money requires int arg 'decimals' >= 0.")
    if not isinstance(pattern, str) or pattern == "":
        raise ValueError("format_money requires non-empty string arg 'pattern'.")
    if not isinstance(currency, str):
        raise ValueError("format_money arg 'currency' must be string when provided.")

    return decimals, pattern, currency


def _format_money(value: Any, args: Mapping[str, Any]) -> Any:
    """Format a numeric input using Decimal rounding and a format pattern.

    Args:
        value: Input numeric value.
        args: Operation args. Requires `decimals` and `pattern`; `currency` is optional.

    Returns:
        `MISSING`/`None` unchanged, otherwise a formatted string.

    Raises:
        ValueError: If conversion fails, args are invalid, or pattern formatting fails.
    """
    if value is MISSING or value is None:
        return value

    decimals, pattern, currency = _parse_config(args)

    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("format_money failed conversion to Decimal.") from exc

    quantum = Decimal("1").scaleb(-decimals)
    rounded = amount.quantize(quantum, rounding=ROUND_HALF_UP)

    try:
        return pattern.format(amount=rounded, currency=currency)
    except (KeyError, ValueError) as exc:
        raise ValueError("format_money pattern formatting failed.") from exc


def get_spec() -> MappingOpSpec:
    """Return the `MappingOpSpec` for the `format_money` operation."""
    return MappingOpSpec(
        op_id="format_money",
        input_type=TypeSpec("any", nullable=True, optional=True),
        output_type=TypeSpec("string", nullable=True, optional=True),
        args_spec=ParamSpec(
            fields=(
                ParamFieldSpec(
                    name="decimals",
                    type_spec=TypeSpec("int", nullable=False, optional=False),
                    required=True,
                    constraints={"min": 0},
                ),
                ParamFieldSpec(
                    name="pattern",
                    type_spec=TypeSpec("string", nullable=False, optional=False),
                    required=True,
                ),
                ParamFieldSpec(
                    name="currency",
                    type_spec=TypeSpec("string", nullable=False, optional=True),
                    required=False,
                ),
            ),
            allow_extra=False,
        ),
        call=_format_money,
    )
