"""Enum-invalid patch helpers for fixture records."""

from typing import Callable, Tuple

from ..builders.base import UMRecord, set_path
from ..enums import (
    VALID_AVAILABILITY,
    VALID_CONDITION,
    VALID_GENDER,
    invalid_enum_value,
)

PatchFunc = Callable[[UMRecord], UMRecord]


def set_invalid_availability(path: str = "inventory.availability") -> PatchFunc:
    """Create patch that sets invalid availability enum value.

    Args:
        path: Availability dotted path.

    Returns:
        Patch callable.
    """

    def _patch(record: UMRecord) -> UMRecord:
        return set_path(record, path, invalid_enum_value(VALID_AVAILABILITY))

    return _patch


def set_invalid_condition(path: str = "condition") -> PatchFunc:
    """Create patch that sets invalid condition enum value.

    Args:
        path: Condition dotted path.

    Returns:
        Patch callable.
    """

    def _patch(record: UMRecord) -> UMRecord:
        return set_path(record, path, invalid_enum_value(VALID_CONDITION))

    return _patch


def set_invalid_gender(path: str = "gender") -> PatchFunc:
    """Create patch that sets invalid gender enum value.

    Args:
        path: Gender dotted path.

    Returns:
        Patch callable.
    """

    def _patch(record: UMRecord) -> UMRecord:
        return set_path(record, path, invalid_enum_value(VALID_GENDER))

    return _patch


def set_invalid_enum(path: str, valid_values: Tuple[str, ...]) -> PatchFunc:
    """Create patch that sets deterministic invalid enum for custom field.

    Args:
        path: Dotted path to enum field.
        valid_values: Tuple of valid enum values.

    Returns:
        Patch callable.
    """

    def _patch(record: UMRecord) -> UMRecord:
        return set_path(record, path, invalid_enum_value(valid_values))

    return _patch
