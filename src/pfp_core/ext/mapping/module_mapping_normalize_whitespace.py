"""Mapping op: normalize internal whitespace in string values."""

from __future__ import annotations

import re
from typing import Any, Mapping

from pfp_core.ext.ext_types import MISSING, MappingOpSpec, ParamSpec, TypeSpec

_WHITESPACE_RE = re.compile(r"\s+")


def _normalize_whitespace(value: Any, args: Mapping[str, Any]) -> Any:
    """Normalize whitespace (collapse runs and trim).

    Args:
        value: Input value.
        args: Operation args (unused).

    Returns:
        `MISSING`/`None` unchanged, otherwise a normalized string.

    Raises:
        ValueError: If input is not a string.
    """
    _ = args
    if value is MISSING or value is None:
        return value
    if not isinstance(value, str):
        raise ValueError("normalize_whitespace expects string input.")
    return _WHITESPACE_RE.sub(" ", value).strip()


def get_spec() -> MappingOpSpec:
    """Return the `MappingOpSpec` for the `normalize_whitespace` operation."""
    return MappingOpSpec(
        op_id="normalize_whitespace",
        input_type=TypeSpec("string", nullable=True, optional=True),
        output_type=TypeSpec("string", nullable=True, optional=True),
        args_spec=ParamSpec(),
        call=_normalize_whitespace,
    )
