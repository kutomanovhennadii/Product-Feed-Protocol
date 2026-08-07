"""Mapping op: format price as 'amount currency' string."""

from __future__ import annotations

from typing import Any, Mapping

from pfp_core.ext.ext_types import (
    MISSING,
    MappingOpSpec,
    ParamFieldSpec,
    ParamSpec,
    TypeSpec,
)


def _format_price(value: Any, args: Mapping[str, Any]) -> Any:
    """Concatenate price amount and currency into Stripe price format.

    Args:
        value: Price amount. Expected to be a string (e.g. ``"29.99"``),
            ``int``, or ``float``.
        args: May contain ``"currency"`` key with an ISO 4217 currency code
            (e.g. ``"USD"``).

    Returns:
        ``MISSING``/``None`` unchanged.
        ``MISSING`` when *value* is an empty or whitespace-only string.
        ``"<amount> <currency>"`` when both amount and currency are present.
        ``"<amount>"`` when currency is absent, ``None``, ``MISSING``, or empty.

    Raises:
        TypeError: If *value* is not ``str``, ``int``, or ``float``
            (and not ``MISSING``/``None``).
    """
    if value is MISSING or value is None:
        return value
    if isinstance(value, bool):
        raise TypeError(
            f"format_price requires str, int, or float; got {type(value).__name__!r}"
        )
    if not isinstance(value, (str, int, float)):
        raise TypeError(
            f"format_price requires str, int, or float; got {type(value).__name__!r}"
        )
    amount_str = str(value).strip()
    if not amount_str:
        return MISSING
    currency = args.get("currency")
    if currency is None or currency is MISSING:
        return amount_str
    currency_str = str(currency).strip()
    if not currency_str:
        return amount_str
    return f"{amount_str} {currency_str}"


def get_spec() -> MappingOpSpec:
    """Return the ``MappingOpSpec`` for the ``format_price`` operation."""
    return MappingOpSpec(
        op_id="format_price",
        input_type=TypeSpec("any", nullable=True, optional=True),
        output_type=TypeSpec("string", nullable=True, optional=True),
        args_spec=ParamSpec(
            fields=(
                ParamFieldSpec(
                    name="currency",
                    type_spec=TypeSpec("string", nullable=True, optional=True),
                    required=False,
                ),
            ),
            allow_extra=False,
        ),
        call=_format_price,
    )
