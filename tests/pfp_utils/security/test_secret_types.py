"""Mirror tests for secret_types — SecretRef, ResolvedSecret, SecretResolutionError."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pfp_utils.security.secret_types import (
    ResolvedSecret,
    SecretRef,
    SecretResolutionError,
)

# ---------------------------------------------------------------------------
# SecretRef
# ---------------------------------------------------------------------------


def test_secret_ref_accepts_env_kind() -> None:
    """SecretRef accepts kind='env' with non-empty value."""
    ref = SecretRef(kind="env", value="MY_VAR")
    assert ref.kind == "env"
    assert ref.value == "MY_VAR"


def test_secret_ref_accepts_file_kind() -> None:
    """SecretRef accepts kind='file' with non-empty value."""
    ref = SecretRef(kind="file", value="/path/to/secret")
    assert ref.kind == "file"


def test_secret_ref_accepts_provider_kind() -> None:
    """SecretRef accepts kind='provider' with non-empty value."""
    ref = SecretRef(kind="provider", value="vault/key")
    assert ref.kind == "provider"


def test_secret_ref_rejects_unknown_kind() -> None:
    """SecretRef rejects unknown kind values."""
    with pytest.raises(ValidationError):
        SecretRef(kind="unknown", value="x")  # type: ignore[arg-type]


def test_secret_ref_rejects_empty_value() -> None:
    """SecretRef rejects empty or whitespace-only value."""
    with pytest.raises(ValidationError, match="non-empty"):
        SecretRef(kind="env", value="")

    with pytest.raises(ValidationError, match="non-empty"):
        SecretRef(kind="env", value="   ")


def test_secret_ref_trims_value() -> None:
    """SecretRef trims whitespace from value."""
    ref = SecretRef(kind="env", value="  MY_VAR  ")
    assert ref.value == "MY_VAR"


def test_secret_ref_forbids_extra_fields() -> None:
    """SecretRef rejects unknown fields (extra='forbid')."""
    with pytest.raises(ValidationError):
        SecretRef(kind="env", value="X", extra_field="bad")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# SecretResolutionError
# ---------------------------------------------------------------------------


def test_secret_resolution_error_is_runtime_error() -> None:
    """SecretResolutionError inherits from RuntimeError."""
    assert issubclass(SecretResolutionError, RuntimeError)


def test_secret_resolution_error_message() -> None:
    """SecretResolutionError preserves message."""
    exc = SecretResolutionError("missing env var")
    assert str(exc) == "missing env var"


# ---------------------------------------------------------------------------
# ResolvedSecret
# ---------------------------------------------------------------------------


def test_resolved_secret_reveal_returns_raw_value() -> None:
    """ResolvedSecret.reveal() returns the original raw value."""
    secret = ResolvedSecret("super-secret")
    assert secret.reveal() == "super-secret"


def test_resolved_secret_str_returns_mask() -> None:
    """str(ResolvedSecret) returns mask, not the raw value."""
    secret = ResolvedSecret("super-secret")
    assert str(secret) == "***"
    assert "super-secret" not in str(secret)


def test_resolved_secret_repr_returns_mask() -> None:
    """repr(ResolvedSecret) does not leak the raw value."""
    secret = ResolvedSecret("super-secret")
    assert "super-secret" not in repr(secret)
    assert "***" in repr(secret)


def test_resolved_secret_masked_returns_mask() -> None:
    """ResolvedSecret.masked() returns the configured mask string."""
    secret = ResolvedSecret("value", mask="[REDACTED]")
    assert secret.masked() == "[REDACTED]"
    assert str(secret) == "[REDACTED]"


def test_resolved_secret_rejects_empty_value() -> None:
    """ResolvedSecret raises SecretResolutionError for empty raw_value."""
    with pytest.raises(SecretResolutionError, match="empty"):
        ResolvedSecret("")


def test_resolved_secret_coerces_non_string_value() -> None:
    """ResolvedSecret coerces non-string raw values to string before storing."""
    secret = ResolvedSecret(123)  # type: ignore[arg-type]
    assert secret.reveal() == "123"
