"""Compiler shape helpers."""

from __future__ import annotations

from typing import Any, Mapping, Optional, cast


def as_mapping(value: object) -> Optional[Mapping[str, Any]]:
    """Return mapping value or `None` if input is not a mapping.

    Args:
        value: Raw object to inspect.

    Returns:
        Mapping object when input is mapping-compatible, otherwise None.
    """

    if isinstance(value, Mapping):
        return cast(Mapping[str, Any], value)
    return None
