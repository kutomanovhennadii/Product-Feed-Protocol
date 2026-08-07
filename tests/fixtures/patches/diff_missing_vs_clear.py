"""DIFF missing-vs-clear patch helpers."""

from typing import Any, Callable

from ..builders.base import UMRecord, delete_path, set_path
from ..diff_semantics import MISSING, clear_for_type, normalize_diff_value

PatchFunc = Callable[[UMRecord], UMRecord]


def set_missing(path: str) -> PatchFunc:
    """Create patch ensuring field is truly missing (key removed).

    Args:
        path: Dotted field path.

    Returns:
        Patch callable.
    """

    def _patch(record: UMRecord) -> UMRecord:
        return delete_path(record, path)

    return _patch


def set_clear(path: str, *, clear_kind: str = "null") -> PatchFunc:
    """Create patch setting explicit clear value.

    Args:
        path: Dotted field path.
        clear_kind: Clear semantic kind (``null``, ``string``, ``list``, ``object``).

    Returns:
        Patch callable.
    """

    def _patch(record: UMRecord) -> UMRecord:
        return set_path(record, path, clear_for_type(clear_kind))

    return _patch


def set_diff_value(
    path: str,
    value: Any,
) -> PatchFunc:
    """Create DIFF-aware patch from value or ``MISSING`` sentinel.

    Args:
        path: Dotted field path.
        value: Desired value or ``MISSING`` sentinel.

    Returns:
        Patch callable.
    """

    def _patch(record: UMRecord) -> UMRecord:
        normalized = normalize_diff_value(value)
        if normalized is MISSING:
            return delete_path(record, path)
        return set_path(record, path, normalized)

    return _patch
