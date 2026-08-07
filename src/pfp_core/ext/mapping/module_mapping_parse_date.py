"""Mapping op: parse date-like values to `datetime.date`."""

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


def _parse_date(value: Any, args: Mapping[str, Any]) -> Any:
    """Parse an input into a `date`.

    Args:
        value: Input value (ISO date string, `date`, or `datetime`).
        args: Operation args. Optional `fmt` string for `datetime.strptime`.

    Returns:
        `MISSING`/`None` unchanged, otherwise a `date`.

    Raises:
        ValueError: If input or args are invalid.
    """
    if value is MISSING or value is None:
        return value

    fmt = args.get("fmt")
    if fmt is not None and not isinstance(fmt, str):
        raise ValueError("parse_date arg 'fmt' must be string when provided.")

    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise ValueError("parse_date expects string/date/datetime input.")

    if fmt:
        return datetime.strptime(value, fmt).date()
    return date.fromisoformat(value)


def get_spec() -> MappingOpSpec:
    """Return the `MappingOpSpec` for the `parse_date` operation."""
    return MappingOpSpec(
        op_id="parse_date",
        input_type=TypeSpec("any", nullable=True, optional=True),
        output_type=TypeSpec("date", nullable=True, optional=True),
        args_spec=ParamSpec(
            fields=(
                ParamFieldSpec(
                    name="fmt",
                    type_spec=TypeSpec("string", nullable=False, optional=True),
                    required=False,
                ),
            ),
            allow_extra=False,
        ),
        call=_parse_date,
    )
