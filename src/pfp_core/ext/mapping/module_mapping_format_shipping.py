"""Mapping op: format shipping entries into a string via a pattern."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Mapping, Tuple

from pfp_core.ext.ext_types import (
    MISSING,
    MappingOpSpec,
    ParamFieldSpec,
    ParamSpec,
    TypeSpec,
)

_PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")

_SPEED_RANGE_FIELDS = (
    "min_handling_time",
    "max_handling_time",
    "min_transit_time",
    "max_transit_time",
)


def _parse_config(
    args: Mapping[str, Any],
) -> Tuple[str, Dict[str, Any], str, bool]:
    """Parse and validate formatting args.

    Args:
        args: Operation args.

    Returns:
        Tuple of (pattern, defaults, separator, strip_colons).

    Raises:
        ValueError: If required args are missing or invalid.
    """
    pattern = args.get("pattern")
    if not isinstance(pattern, str) or pattern == "":
        raise ValueError("format_shipping requires non-empty string arg 'pattern'.")

    defaults = args.get("defaults", {})
    if not isinstance(defaults, dict):
        raise ValueError("format_shipping arg 'defaults' must be a dict.")

    separator = args.get("separator", ",")
    if not isinstance(separator, str):
        raise ValueError("format_shipping arg 'separator' must be a string.")

    strip_colons = args.get("strip_colons", True)
    if not isinstance(strip_colons, bool):
        raise ValueError("format_shipping arg 'strip_colons' must be a bool.")

    return pattern, defaults, separator, strip_colons


def _sanitize(value: Any, strip_colons: bool) -> str:
    """Sanitize a field value for substitution.

    Args:
        value: Raw field value.
        strip_colons: Whether to remove colons.

    Returns:
        Cleaned string.
    """
    text = str(value).strip()
    if strip_colons:
        return text.replace(":", "")
    return text


def _safe_int(value: Any, field_name: str) -> int:
    """Convert a value to int with clear error message.

    Args:
        value: Value to convert.
        field_name: Field name for error message.

    Returns:
        Integer value.

    Raises:
        ValueError: If conversion fails.
    """
    try:
        return int(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(
            f"format_shipping field '{field_name}' must be an integer, got: {value!r}."
        ) from exc


def _compute_speed_range(
    entry: Mapping[str, Any],
    defaults: Mapping[str, Any],
) -> str:
    """Compute speed_range from handling and transit time fields.

    Args:
        entry: Shipping entry dict.
        defaults: Default values.

    Returns:
        Speed range string like "2-5".
    """
    vals = []
    for field in _SPEED_RANGE_FIELDS:
        raw = entry.get(field)
        if raw is None or raw == "":
            raw = defaults.get(field, 0)
        vals.append(_safe_int(raw, field))

    min_days = vals[0] + vals[2]
    max_days = vals[1] + vals[3]
    return f"{min_days}-{max_days}"


def _format_entry(
    entry: Mapping[str, Any],
    pattern: str,
    defaults: Dict[str, Any],
    strip_colons: bool,
    placeholders: List[str],
) -> str:
    """Format a single shipping entry dict via pattern.

    Args:
        entry: Shipping entry dict.
        pattern: Format pattern string.
        defaults: Default values for missing fields.
        strip_colons: Whether to remove colons from values.
        placeholders: List of placeholder names extracted from pattern.

    Returns:
        Formatted string.

    Raises:
        ValueError: If a placeholder cannot be resolved.
    """
    resolved = {}
    for name in placeholders:
        if name == "speed_range":
            resolved[name] = _compute_speed_range(entry, defaults)
            continue

        raw = entry.get(name)
        if raw is None or raw == "":
            raw = defaults.get(name)
        if raw is None:
            raise ValueError(
                f"format_shipping: field '{name}' missing from entry and no default."
            )
        resolved[name] = _sanitize(raw, strip_colons)

    try:
        return pattern.format(**resolved)
    except (KeyError, ValueError) as exc:
        raise ValueError("format_shipping pattern formatting failed.") from exc


def _format_shipping(value: Any, args: Mapping[str, Any]) -> Any:
    """Format shipping entries into a string via a configurable pattern.

    Args:
        value: Input value — list of dicts/strings, single dict, string,
               or ``MISSING``/``None``.
        args: Operation args. Requires ``pattern``.

    Returns:
        Formatted shipping string, or passthrough for MISSING/None/str.

    Raises:
        ValueError: If args are invalid or entry fields are missing.
    """
    pattern, defaults, separator, strip_colons = _parse_config(args)

    if value is MISSING or value is None:
        return value

    if isinstance(value, str):
        return value

    placeholders = _PLACEHOLDER_RE.findall(pattern)

    if isinstance(value, dict):
        entries = [value]
    elif isinstance(value, list):
        entries = value
    else:
        entries = [value]

    parts = []
    for entry in entries:
        if isinstance(entry, str):
            parts.append(entry)
        elif isinstance(entry, dict):
            parts.append(
                _format_entry(entry, pattern, defaults, strip_colons, placeholders)
            )
        else:
            raise ValueError(
                f"format_shipping: entry must be dict or str, got {type(entry).__name__}."
            )

    return separator.join(parts)


def get_spec() -> MappingOpSpec:
    """Return the ``MappingOpSpec`` for the ``format_shipping`` operation."""
    return MappingOpSpec(
        op_id="format_shipping",
        input_type=TypeSpec("any", nullable=True, optional=True),
        output_type=TypeSpec("string", nullable=True, optional=True),
        args_spec=ParamSpec(
            fields=(
                ParamFieldSpec(
                    name="pattern",
                    type_spec=TypeSpec("string", nullable=False, optional=False),
                    required=True,
                ),
                ParamFieldSpec(
                    name="defaults",
                    type_spec=TypeSpec("object", nullable=False, optional=True),
                    required=False,
                ),
                ParamFieldSpec(
                    name="separator",
                    type_spec=TypeSpec("string", nullable=False, optional=True),
                    required=False,
                ),
                ParamFieldSpec(
                    name="strip_colons",
                    type_spec=TypeSpec("bool", nullable=False, optional=True),
                    required=False,
                ),
            ),
            allow_extra=False,
        ),
        call=_format_shipping,
    )
