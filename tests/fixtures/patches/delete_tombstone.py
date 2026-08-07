"""DELETE tombstone patch helpers for fixture records."""

from typing import Callable

from ..builders.base import UMRecord, set_path

PatchFunc = Callable[[UMRecord], UMRecord]


def as_delete_tombstone(*, include_noise_fields: bool = True) -> PatchFunc:
    """Create patch that enforces tombstone semantics on record.

    Args:
        include_noise_fields: Add irrelevant fields for ignore-behavior checks.

    Returns:
        Patch callable.
    """

    def _patch(record: UMRecord) -> UMRecord:
        updated = record
        if updated.get("delete") is True:
            updated = set_path(updated, "delete", False)
        if include_noise_fields:
            updated = set_path(updated, "title", "SHOULD_BE_IGNORED")
            updated = set_path(updated, "description", "SHOULD_BE_IGNORED")
            updated = set_path(updated, "inventory.availability", "out_of_stock")
        updated = set_path(updated, "delete", True)
        return updated

    return _patch
