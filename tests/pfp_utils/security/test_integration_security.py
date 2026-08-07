"""Integration tests for the pfp_utils.security block."""

from __future__ import annotations

from pathlib import Path

import pytest

from pfp_utils.security.secret_resolver import resolve_secret
from pfp_utils.security.secret_types import SecretResolutionError


def test_secret_resolver_handles_env_file_and_provider_sources(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Security block resolves secrets from all supported source kinds.

    Args:
        monkeypatch: Pytest helper used to provide environment variables.
        tmp_path: Temporary directory that stores the secret file fixture.
    """

    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("file-secret\n", encoding="utf-8")
    monkeypatch.setenv("PFP_SECRET_TOKEN", "env-secret")

    env_secret = resolve_secret({"kind": "env", "value": "PFP_SECRET_TOKEN"})
    file_secret = resolve_secret({"kind": "file", "value": str(secret_file)})
    provider_secret = resolve_secret(
        {"kind": "provider", "value": "vault/path"},
        provider=lambda ref: "provider:" + ref,
    )

    assert env_secret.reveal() == "env-secret"
    assert str(env_secret) == "***"
    assert file_secret.reveal() == "file-secret"
    assert provider_secret.reveal() == "provider:vault/path"


def test_secret_resolver_raises_for_missing_environment_variables(
    monkeypatch,
) -> None:
    """Security block raises a stable error when the env source is missing.

    Args:
        monkeypatch: Pytest helper used to remove environment variables.
    """

    monkeypatch.delenv("PFP_SECRET_TOKEN", raising=False)

    with pytest.raises(
        SecretResolutionError,
        match="required environment variable is missing: PFP_SECRET_TOKEN",
    ):
        resolve_secret({"kind": "env", "value": "PFP_SECRET_TOKEN"})


def test_secret_resolver_raises_for_missing_secret_files(tmp_path: Path) -> None:
    """Security block raises a stable error when the file source is missing.

    Args:
        tmp_path: Temporary directory used to build the missing file path.
    """

    missing_path = tmp_path / "missing.secret"

    with pytest.raises(SecretResolutionError, match="cannot read secret file"):
        resolve_secret({"kind": "file", "value": str(missing_path)})
