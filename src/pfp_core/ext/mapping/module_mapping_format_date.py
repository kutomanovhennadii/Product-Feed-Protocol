"""Mapping op: format date-like values to a string."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Mapping

from pfp_core.ext.ext_types import (
    MISSING,
    MappingOpSpec,
    ParamFieldSpec,
    ParamSpec,
    TypeSpec,
)

_DEFAULT_FMT = "YYYY-MM-DD"


def _format_date(value: Any, args: Mapping[str, Any]) -> Any:
    """Format an input date/datetime/ISO-date string.

    Args:
        value: Input value.
        args: Operation args. Optional `out_fmt` string.

    Returns:
        `MISSING`/`None` unchanged, otherwise a formatted string.

    Raises:
        ValueError: If input or args are invalid.
    """
    if value is MISSING or value is None:
        return value

    out_fmt = args.get("out_fmt", _DEFAULT_FMT)
    if not isinstance(out_fmt, str):
        raise ValueError("format_date arg 'out_fmt' must be string.")

    normalized: date
    if isinstance(value, datetime):
        normalized = value.date()
    elif isinstance(value, date):
        normalized = value
    elif isinstance(value, str):
        normalized = date.fromisoformat(value)
    else:
        raise ValueError("format_date expects date/datetime/ISO-string input.")

    if out_fmt == "YYYY-MM-DD":
        return normalized.strftime("%Y-%m-%d")
    return normalized.strftime(out_fmt)


def get_spec() -> MappingOpSpec:
    """Return the `MappingOpSpec` for the `format_date` operation."""
    return MappingOpSpec(
        op_id="format_date",
        input_type=TypeSpec("any", nullable=True, optional=True),
        output_type=TypeSpec("string", nullable=True, optional=True),
        args_spec=ParamSpec(
            fields=(
                ParamFieldSpec(
                    name="out_fmt",
                    type_spec=TypeSpec("string", nullable=False, optional=True),
                    required=False,
                ),
            ),
            allow_extra=False,
        ),
        call=_format_date,
    )
