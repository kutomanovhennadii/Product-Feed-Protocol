"""Mirror tests for secret_resolver — resolve_secret() for env/file/provider."""

from __future__ import annotations

from pathlib import Path

import pytest

from pfp_utils.security import SecretResolutionError, resolve_secret

# ---------------------------------------------------------------------------
# kind=env
# ---------------------------------------------------------------------------


def test_resolve_secret_env_and_masked_render(monkeypatch: pytest.MonkeyPatch) -> None:
    """Resolves env secret and keeps default string rendering masked."""
    monkeypatch.setenv("MY_TOKEN", "super-secret-token")

    secret = resolve_secret({"kind": "env", "value": "MY_TOKEN"})

    assert secret.reveal() == "super-secret-token"
    assert str(secret) == "***"
    assert "super-secret-token" not in repr(secret)


def test_resolve_secret_missing_env_raises_safe_error() -> None:
    """Raises safe error when required environment variable is missing."""
    with pytest.raises(SecretResolutionError) as exc:
        resolve_secret({"kind": "env", "value": "NO_SUCH_SECRET_VAR"})

    assert "NO_SUCH_SECRET_VAR" in str(exc.value)


# ---------------------------------------------------------------------------
# kind=file
# ---------------------------------------------------------------------------


def test_resolve_secret_file_reads_and_trims_value(tmp_path: Path) -> None:
    """Resolves file secret source and trims trailing newline from payload."""
    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("file-secret-value\n", encoding="utf-8")

    secret = resolve_secret({"kind": "file", "value": str(secret_file)})

    assert secret.reveal() == "file-secret-value"


def test_resolve_secret_file_missing_raises_error() -> None:
    """Raises SecretResolutionError when secret file does not exist."""
    with pytest.raises(SecretResolutionError, match="cannot read secret file"):
        resolve_secret({"kind": "file", "value": "/no/such/file.txt"})


def test_resolve_secret_file_empty_raises_error(tmp_path: Path) -> None:
    """Raises SecretResolutionError when the secret file contains no value."""
    secret_file = tmp_path / "empty.txt"
    secret_file.write_text("   \n", encoding="utf-8")

    with pytest.raises(SecretResolutionError, match="secret file value is empty"):
        resolve_secret({"kind": "file", "value": str(secret_file)})


# ---------------------------------------------------------------------------
# kind=provider
# ---------------------------------------------------------------------------


def test_resolve_secret_provider_uses_callback() -> None:
    """Resolves provider secret via callback for provider references."""

    def _provider(name: str) -> str:
        assert name == "stripe/api-key"
        return "provided-secret"

    secret = resolve_secret(
        {"kind": "provider", "value": "stripe/api-key"},
        provider=_provider,
    )

    assert secret.reveal() == "provided-secret"


def test_resolve_secret_provider_without_callback_raises() -> None:
    """Raises SecretResolutionError when provider callback is not supplied."""
    with pytest.raises(SecretResolutionError, match="requires provider callback"):
        resolve_secret({"kind": "provider", "value": "vault/key"})


def test_resolve_secret_provider_callback_failure_raises() -> None:
    """Raises SecretResolutionError when the provider callback fails."""

    def _provider(_name: str) -> str:
        raise RuntimeError("boom")

    with pytest.raises(SecretResolutionError, match="provider resolution failed"):
        resolve_secret({"kind": "provider", "value": "vault/key"}, provider=_provider)


def test_resolve_secret_provider_empty_value_raises() -> None:
    """Raises SecretResolutionError when the provider returns an empty value."""

    def _provider(_name: str) -> str:
        return ""

    with pytest.raises(SecretResolutionError, match="returned empty value"):
        resolve_secret({"kind": "provider", "value": "vault/key"}, provider=_provider)


# ---------------------------------------------------------------------------
# Invalid payload
# ---------------------------------------------------------------------------


def test_resolve_secret_invalid_payload_raises() -> None:
    """Raises SecretResolutionError for payload missing required fields."""
    with pytest.raises(SecretResolutionError, match="invalid secret reference"):
        resolve_secret({"not_kind": "env"})
