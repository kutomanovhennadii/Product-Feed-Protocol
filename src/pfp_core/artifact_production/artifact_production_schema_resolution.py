from __future__ import annotations


def normalize_target_id(target_id: str) -> str:
    """Normalize target identifier without semantic remapping."""
    return _normalize_target_id(target_id)


def _normalize_target_id(value: str) -> str:
    """Normalize and validate target identifier string."""
    if not isinstance(value, str):
        raise ValueError("target_id must be a string")
    normalized = value.strip().lower()
    if not normalized:
        raise ValueError("target_id must be a non-empty string")
    return normalized
