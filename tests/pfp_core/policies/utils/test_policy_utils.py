"""Tests for policy utility helpers."""

import pytest

from pfp_core.policies.utils.policy_utils import (
    _normalize_version,
    _require_key,
    _require_mapping,
    _validate_keys,
)


def test_require_mapping_rejects_non_dict() -> None:
    """_require_mapping rejects non-mapping values."""
    with pytest.raises(ValueError, match="Expected mapping"):
        _require_mapping([], "root")


def test_validate_keys_rejects_unknown() -> None:
    """_validate_keys raises on unknown keys."""
    with pytest.raises(ValueError, match="Unknown keys"):
        _validate_keys({"a": 1, "b": 2}, {"a"}, "root")


def test_normalize_version_accepts_numeric() -> None:
    """_normalize_version accepts numbers and converts them to strings."""
    assert _normalize_version(1.0) == "1.0"
    assert _normalize_version("1.0") == "1.0"


def test_require_key_raises_if_missing() -> None:
    """_require_key raises when required key is absent."""
    with pytest.raises(ValueError, match="Missing required key"):
        _require_key({}, "version", "root")


def test_normalize_version_rejects_non_string_like_values() -> None:
    """_normalize_version rejects unsupported object values."""

    with pytest.raises(ValueError, match="must be a string"):
        _normalize_version(object())
