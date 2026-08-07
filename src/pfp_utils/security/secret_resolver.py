"""Resolve secret references to their runtime values.

This module provides ``resolve_secret()`` — the single entry point for turning
a ``SecretRef``-like payload (dict with ``kind`` and ``value``) into a
``ResolvedSecret`` wrapper whose raw value is hidden from logs by default.

Supported source kinds:
    - **env**: reads an environment variable by name.
    - **file**: reads a UTF-8 file and strips trailing whitespace.
    - **provider**: delegates to a caller-supplied callback (e.g. Vault, SSM).

When to use:
    Call ``resolve_secret()`` during component initialisation (fail-fast).
    Publishing components should prefer the thin facade
    ``publishing.support.secret_resolver.resolve_secret_ref()`` which
    unwraps the ``ResolvedSecret`` to a plain ``str`` automatically.

Errors:
    Every failure raises ``SecretResolutionError`` (a ``RuntimeError``) with
    a human-readable message that never contains the secret value itself.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable, Optional

from pydantic import ValidationError

from pfp_utils.security.secret_types import (
    ResolvedSecret,
    SecretRef,
    SecretResolutionError,
)


def resolve_secret(
    secret_ref_payload: Any,
    *,
    provider: Optional[Callable[[str], str]] = None,
) -> ResolvedSecret:
    """Resolve secret reference into secret-aware runtime wrapper.

    Args:
        secret_ref_payload: Mapping-like payload with ``kind`` and ``value``.
        provider: Optional provider callback used when ``kind=provider``.

    Returns:
        ResolvedSecret wrapper.

    Raises:
        SecretResolutionError: When reference is invalid or source is unavailable.
    """
    try:
        secret_ref = SecretRef.model_validate(secret_ref_payload)
    except ValidationError as exc:
        raise SecretResolutionError("invalid secret reference format") from exc

    if secret_ref.kind == "env":
        raw = os.getenv(secret_ref.value)
        if not raw:
            raise SecretResolutionError(
                "required environment variable is missing: " + secret_ref.value
            )
        return ResolvedSecret(raw)

    if secret_ref.kind == "file":
        path = Path(secret_ref.value)
        try:
            raw_file = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise SecretResolutionError(
                "cannot read secret file: " + str(path)
            ) from exc
        normalized = raw_file.strip()
        if not normalized:
            raise SecretResolutionError("secret file value is empty")
        return ResolvedSecret(normalized)

    provider_callback = provider
    if provider_callback is None:
        raise SecretResolutionError(
            "provider secret resolution requires provider callback"
        )
    try:
        provided = provider_callback(secret_ref.value)
    except Exception as exc:
        raise SecretResolutionError("secret provider resolution failed") from exc
    if not isinstance(provided, str) or not provided:
        raise SecretResolutionError("secret provider returned empty value")
    return ResolvedSecret(provided)
