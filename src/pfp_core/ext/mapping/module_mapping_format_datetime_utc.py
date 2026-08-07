"""Mapping op: format datetime values in UTC."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from pfp_core.ext.ext_types import (
    MISSING,
    MappingOpSpec,
    ParamFieldSpec,
    ParamSpec,
    TypeSpec,
)

_DEFAULT_FMT = "ISO8601"


def _to_datetime(value: Any) -> datetime:
    """Normalize input to a `datetime`.

    Args:
        value: `datetime` instance or ISO 8601 string.

    Returns:
        A `datetime` instance.

    Raises:
        ValueError: If input cannot be parsed.
    """
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text)
    raise ValueError("format_datetime_utc expects datetime or ISO string.")


def _format_datetime_utc(value: Any, args: Mapping[str, Any]) -> Any:
    """Format an input datetime as UTC.

    Args:
        value: Input value (`datetime` or ISO string).
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
        raise ValueError("format_datetime_utc arg 'out_fmt' must be string.")

    dt_value = _to_datetime(value)
    if dt_value.tzinfo is None:
        dt_value = dt_value.replace(tzinfo=timezone.utc)
    else:
        dt_value = dt_value.astimezone(timezone.utc)

    if out_fmt == "ISO8601":
        return dt_value.strftime("%Y-%m-%dT%H:%M:%SZ")
    return dt_value.strftime(out_fmt)


def get_spec() -> MappingOpSpec:
    """Return the `MappingOpSpec` for the `format_datetime_utc` operation."""
    return MappingOpSpec(
        op_id="format_datetime_utc",
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
        call=_format_datetime_utc,
    )
