"""Mapping op: extract a capture group from a value using a regex pattern."""

from __future__ import annotations

import re
from typing import Any, Mapping

from pfp_core.ext.ext_types import (
    MISSING,
    MappingOpSpec,
    ParamFieldSpec,
    ParamSpec,
    TypeSpec,
)


def _regex_extract(value: Any, args: Mapping[str, Any]) -> Any:
    """Apply regex to *value* and return the specified capture group.

    Args:
        value: Input value (may be ``MISSING`` or ``None``).
        args: Operation args. Requires ``pattern``; ``group`` is optional (default 1).

    Returns:
        Matched capture group string, or ``MISSING`` if no match.

    Raises:
        ValueError: If required args are missing, invalid, or group is out of range.
    """
    pattern = args.get("pattern")
    if not isinstance(pattern, str) or pattern == "":
        raise ValueError("regex_extract requires non-empty string arg 'pattern'.")

    group = args.get("group", 1)
    if not isinstance(group, int) or isinstance(group, bool) or group < 0:
        raise ValueError("regex_extract arg 'group' must be int >= 0.")

    if value is MISSING or value is None:
        return value

    match = re.search(pattern, str(value))
    if match is None:
        return MISSING

    try:
        return match.group(group)
    except IndexError:
        raise ValueError(
            f"regex_extract group {group} out of range for pattern {pattern!r}."
        )


def get_spec() -> MappingOpSpec:
    """Return the ``MappingOpSpec`` for the ``regex_extract`` operation."""
    return MappingOpSpec(
        op_id="regex_extract",
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
                    name="group",
                    type_spec=TypeSpec("int", nullable=False, optional=True),
                    required=False,
                    constraints={"min": 0},
                ),
            ),
            allow_extra=False,
        ),
        call=_regex_extract,
    )
