"""Domain types for shared secret handling.

This module defines the core types used across the security package:

- **SecretRef**: Pydantic model representing a pointer to a secret source
  (environment variable, file, or external provider). Used as a type hint
  in publisher/archiver config models (e.g. ``api_key_ref: SecretRef``).
  Never contains the secret value itself — only the source kind and lookup key.

- **ResolvedSecret**: Opaque wrapper returned by ``resolve_secret()``.
  Keeps the raw secret value private and renders as ``***`` in ``str()``/``repr()``
  to prevent accidental leakage in logs and error messages. Call ``.reveal()``
  only at transport boundaries (HTTP headers, SFTP credentials).

- **SecretResolutionError**: Raised when a secret reference cannot be resolved
  (missing env var, unreadable file, provider failure). Caught by publisher
  components for fail-fast initialization.

When to use:
    Import ``SecretRef`` for config model type hints.
    Import ``SecretResolutionError`` for error handling in secret consumers.
    ``ResolvedSecret`` is internal to the secrets package — external code
    should use ``resolve_secret_ref()`` from ``publishing.support`` instead.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator


class SecretRef(BaseModel):
    """Reference to secret source without inline secret value."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["env", "file", "provider"]
    value: str

    @field_validator("value")
    @classmethod
    def _validate_non_empty_value(cls, value: str) -> str:
        """Validate non-empty secret reference payload.

        Args:
            value: Raw secret reference value.

        Returns:
            Trimmed non-empty secret reference value.
        """
        normalized = value.strip()
        if not normalized:
            raise ValueError("secret ref value must be non-empty")
        return normalized


class SecretResolutionError(RuntimeError):
    """Raised when a secret reference cannot be resolved safely."""


class ResolvedSecret:
    """Runtime wrapper that keeps raw value private and masked by default."""

    __slots__ = ("_raw", "_mask")

    def __init__(self, raw_value: str, mask: str = "***") -> None:
        normalized = raw_value
        if isinstance(raw_value, str):
            normalized = raw_value
        else:
            normalized = str(raw_value)
        if not normalized:
            raise SecretResolutionError("resolved secret value is empty")
        self._raw = normalized
        self._mask = mask or "***"

    def reveal(self) -> str:
        """Return raw secret value for boundary-only transport usage."""
        return self._raw

    def masked(self) -> str:
        """Return masked secret representation."""
        return self._mask

    def __str__(self) -> str:
        return self._mask

    def __repr__(self) -> str:
        return "ResolvedSecret(masked='" + self._mask + "')"
