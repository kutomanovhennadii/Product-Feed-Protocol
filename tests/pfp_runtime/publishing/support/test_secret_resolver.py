"""Tests for publishing/support/secret_resolver.py."""

from __future__ import annotations

import os
import tempfile

import pytest

from pfp_runtime.publishing.support.secret_resolver import (
    SecretResolutionError,
    resolve_secret_ref,
)

# ---------------------------------------------------------------------------
# env kind
# ---------------------------------------------------------------------------


def test_env_kind_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify env secret ref resolves to the env variable string value."""
    monkeypatch.setenv("MY_TEST_KEY", "secret-value")
    result = resolve_secret_ref({"kind": "env", "value": "MY_TEST_KEY"})
    assert result == "secret-value"


def test_env_kind_missing_var(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify SecretResolutionError is raised when env variable is not set."""
    monkeypatch.delenv("NONEXISTENT_VAR_XYZ", raising=False)
    with pytest.raises(SecretResolutionError):
        resolve_secret_ref({"kind": "env", "value": "NONEXISTENT_VAR_XYZ"})


# ---------------------------------------------------------------------------
# file kind
# ---------------------------------------------------------------------------


def test_file_kind_success() -> None:
    """Verify file secret ref resolves to the stripped file contents."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("file-secret-content")
        tmp_path = f.name
    try:
        result = resolve_secret_ref({"kind": "file", "value": tmp_path})
        assert result == "file-secret-content"
    finally:
        os.unlink(tmp_path)


def test_file_kind_missing_file() -> None:
    """Verify SecretResolutionError is raised when secret file does not exist."""
    with pytest.raises(SecretResolutionError):
        resolve_secret_ref({"kind": "file", "value": "/nonexistent/path/secret.txt"})


# ---------------------------------------------------------------------------
# Invalid format
# ---------------------------------------------------------------------------


def test_invalid_format_no_kind() -> None:
    """Verify SecretResolutionError is raised when 'kind' field is missing."""
    with pytest.raises(SecretResolutionError):
        resolve_secret_ref({"value": "MY_KEY"})


def test_invalid_format_unknown_kind() -> None:
    """Verify SecretResolutionError is raised for unknown kind value."""
    with pytest.raises(SecretResolutionError):
        resolve_secret_ref({"kind": "vault", "value": "path/to/secret"})


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------


def test_returns_string(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify resolve_secret_ref returns a plain str, not a ResolvedSecret wrapper."""
    monkeypatch.setenv("RESOLVER_TEST_STR", "hello")
    result = resolve_secret_ref({"kind": "env", "value": "RESOLVER_TEST_STR"})
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Re-export of SecretResolutionError
# ---------------------------------------------------------------------------


def test_secret_resolution_error_importable() -> None:
    """Verify SecretResolutionError can be imported directly from secret_resolver module."""
    from pfp_runtime.publishing.support.secret_resolver import (  # noqa: F401
        SecretResolutionError as SRE,
    )

    assert issubclass(SRE, RuntimeError)
