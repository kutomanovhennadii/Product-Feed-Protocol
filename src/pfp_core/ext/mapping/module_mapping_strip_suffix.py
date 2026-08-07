"""Mapping op: strip suffix by cutting at the rightmost delimiter."""

from __future__ import annotations

from typing import Any, List, Mapping

from pfp_core.ext.ext_types import (
    MISSING,
    MappingOpSpec,
    ParamFieldSpec,
    ParamSpec,
    TypeSpec,
)


def _parse_delimiters(args: Mapping[str, Any]) -> List[str]:
    """Parse and validate delimiters arg.

    Args:
        args: Operation args.

    Returns:
        List of delimiter strings.

    Raises:
        ValueError: If delimiters are missing, empty, or contain non-strings.
    """
    delimiters = args.get("delimiters")
    if not isinstance(delimiters, list) or len(delimiters) == 0:
        raise ValueError("strip_suffix requires non-empty list arg 'delimiters'.")
    for d in delimiters:
        if not isinstance(d, str):
            raise ValueError("strip_suffix 'delimiters' must contain only strings.")
    return delimiters


def _strip_suffix(value: Any, args: Mapping[str, Any]) -> Any:
    """Strip the last segment after the rightmost delimiter occurrence.

    Args:
        value: Input value (may be ``MISSING`` or ``None``).
        args: Operation args. Requires ``delimiters``.

    Returns:
        Substring before the rightmost delimiter, or original string if none found.

    Raises:
        ValueError: If required args are missing or invalid.
    """
    delimiters = _parse_delimiters(args)

    if value is MISSING or value is None:
        return value

    s = str(value)
    best_pos = -1
    for d in delimiters:
        pos = s.rfind(d)
        if pos > best_pos:
            best_pos = pos

    if best_pos >= 0:
        return s[:best_pos]
    return s


def get_spec() -> MappingOpSpec:
    """Return the ``MappingOpSpec`` for the ``strip_suffix`` operation."""
    return MappingOpSpec(
        op_id="strip_suffix",
        input_type=TypeSpec("any", nullable=True, optional=True),
        output_type=TypeSpec("string", nullable=True, optional=True),
        args_spec=ParamSpec(
            fields=(
                ParamFieldSpec(
                    name="delimiters",
                    type_spec=TypeSpec("array[string]", nullable=False, optional=False),
                    required=True,
                    constraints={"min_items": 1},
                ),
            ),
            allow_extra=False,
        ),
        call=_strip_suffix,
    )
