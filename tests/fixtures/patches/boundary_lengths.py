"""Boundary-length patch helpers for fixture records."""

from typing import Callable

from ..builders.base import UMRecord, set_path
from ..strings import ascii_text, utf8_text

PatchFunc = Callable[[UMRecord], UMRecord]


def set_title_length(length: int, *, utf8: bool = False) -> PatchFunc:
    """Create patch that sets ``title`` to exact length.

    Args:
        length: Required title length.
        utf8: Use UTF-8 helper when True.

    Returns:
        Patch callable.
    """

    def _patch(record: UMRecord) -> UMRecord:
        text = utf8_text(length) if utf8 else ascii_text(length)
        return set_path(record, "title", text)

    return _patch


def set_description_length(length: int, *, utf8: bool = False) -> PatchFunc:
    """Create patch that sets ``description`` to exact length.

    Args:
        length: Required description length.
        utf8: Use UTF-8 helper when True.

    Returns:
        Patch callable.
    """

    def _patch(record: UMRecord) -> UMRecord:
        text = utf8_text(length) if utf8 else ascii_text(length)
        return set_path(record, "description", text)

    return _patch


def set_brand_length(length: int) -> PatchFunc:
    """Create patch that sets ``brand`` to exact ASCII length.

    Args:
        length: Required brand length.

    Returns:
        Patch callable.
    """

    def _patch(record: UMRecord) -> UMRecord:
        return set_path(record, "brand", ascii_text(length))

    return _patch


def set_path_length(path: str, length: int, *, utf8: bool = False) -> PatchFunc:
    """Create generic patch that sets dotted path to exact-length text.

    Args:
        path: Dotted field path.
        length: Required text length.
        utf8: Use UTF-8 helper when True.

    Returns:
        Patch callable.
    """

    def _patch(record: UMRecord) -> UMRecord:
        text = utf8_text(length) if utf8 else ascii_text(length)
        return set_path(record, path, text)

    return _patch


MAX_LENGTHS = {
    "item_id": 100,
    "title": 150,
    "description": 5000,
    "brand": 70,
}


def set_max_length(path: str) -> PatchFunc:
    """Create patch setting field to configured max length.

    Args:
        path: Dotted path with known max length in ``MAX_LENGTHS``.

    Returns:
        Patch callable.
    """
    if path not in MAX_LENGTHS:
        raise KeyError(f"Unknown max length path: {path}")
    return set_path_length(path, MAX_LENGTHS[path])


def set_over_max_length(path: str) -> PatchFunc:
    """Create patch setting field to max+1 length.

    Args:
        path: Dotted path with known max length in ``MAX_LENGTHS``.

    Returns:
        Patch callable.
    """
    if path not in MAX_LENGTHS:
        raise KeyError(f"Unknown max length path: {path}")
    return set_path_length(path, MAX_LENGTHS[path] + 1)
