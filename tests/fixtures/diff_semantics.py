"""DIFF semantics helpers for fixtures: explicit missing vs explicit clear."""

from typing import Any, List


class MissingSentinel:
    """Sentinel for explicit DIFF missing semantics in fixture APIs."""

    __slots__ = ()

    def __repr__(self) -> str:
        return "MISSING"


MISSING = MissingSentinel()


def is_missing(value: Any) -> bool:
    """Return True when value equals fixture missing sentinel.

    Args:
        value: Arbitrary value.

    Returns:
        Whether value is the ``MISSING`` sentinel.
    """
    return value is MISSING


def clear_null() -> None:
    """Return explicit null clear marker.

    Returns:
        ``None`` as explicit clear value.
    """
    return None


def clear_empty_string() -> str:
    """Return explicit clear marker for string field.

    Returns:
        Empty string.
    """
    return ""


def clear_empty_list() -> List[Any]:
    """Return explicit clear marker for list field.

    Returns:
        New empty list instance.
    """
    return []


def clear_for_type(kind: str) -> Any:
    """Return deterministic clear value for a simple semantic kind.

    Args:
        kind: Semantic kind: ``string``, ``list``, ``object`` or ``null``.

    Returns:
        Clear value suitable for patching.
    """
    if kind == "string":
        return clear_empty_string()
    if kind == "list":
        return clear_empty_list()
    if kind == "object":
        return {}
    if kind == "null":
        return clear_null()
    raise ValueError(f"Unknown clear kind: {kind}")


def normalize_diff_value(value: Any) -> Any:
    """Return DIFF value as-is while preserving the missing sentinel.

    Args:
        value: Requested fixture value.

    Returns:
        ``MISSING`` when provided, otherwise the original value.
    """
    if is_missing(value):
        return MISSING
    return value
