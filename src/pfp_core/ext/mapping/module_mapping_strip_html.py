"""Mapping op: strip HTML tags and decode HTML entities from a string."""

from __future__ import annotations

import html
import re
from typing import Any, Mapping

from pfp_core.ext.ext_types import MISSING, MappingOpSpec, ParamSpec, TypeSpec

_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


def _strip_html(value: Any, args: Mapping[str, Any]) -> Any:
    """Remove HTML tags and decode HTML entities from *value*.

    Args:
        value: Input value. Expected to be a string containing HTML markup.
        args: Operation args (unused).

    Returns:
        ``MISSING``/``None`` unchanged.
        String with HTML tags removed, entities decoded, and whitespace
        collapsed to single spaces.

    Raises:
        TypeError: If *value* is not a string (and not MISSING/None).
    """
    _ = args
    if value is MISSING or value is None:
        return value
    if not isinstance(value, str):
        raise TypeError(f"strip_html requires a string, got {type(value).__name__!r}")
    text = _TAG_RE.sub(" ", value)
    text = html.unescape(text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def get_spec() -> MappingOpSpec:
    """Return the ``MappingOpSpec`` for the ``strip_html`` operation."""
    return MappingOpSpec(
        op_id="strip_html",
        input_type=TypeSpec("string", nullable=True, optional=True),
        output_type=TypeSpec("string", nullable=True, optional=True),
        args_spec=ParamSpec(),
        call=_strip_html,
    )
