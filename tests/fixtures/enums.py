"""Enum helper values for fixture builders and patches."""

from typing import Iterable, List, Tuple

VALID_AVAILABILITY: Tuple[str, ...] = (
    "in_stock",
    "out_of_stock",
    "pre_order",
    "backorder",
)

VALID_CONDITION: Tuple[str, ...] = (
    "new",
    "used",
    "refurbished",
)

VALID_GENDER: Tuple[str, ...] = (
    "male",
    "female",
    "unisex",
)

INVALID_SENTINEL = "invalid"


def invalid_enum_value(
    valid_values: Iterable[str], prefix: str = INVALID_SENTINEL
) -> str:
    """Return deterministic value not present in provided enum values.

    Args:
        valid_values: Iterable of valid enum values.
        prefix: Prefix for generated invalid value.

    Returns:
        Deterministic invalid enum value.
    """
    used = set(valid_values)
    candidate = prefix
    idx = 1
    attempts = 0
    while candidate in used:
        if attempts >= 1000:
            raise RuntimeError("Failed to generate invalid enum value")
        candidate = prefix + "_" + str(idx)
        idx += 1
        attempts += 1
    return candidate


__all__: List[str] = [
    "VALID_AVAILABILITY",
    "VALID_CONDITION",
    "VALID_GENDER",
    "invalid_enum_value",
]
