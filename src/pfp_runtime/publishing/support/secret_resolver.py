"""Thin secret resolution facade for publishing components.

Single entry point for archivers and delivery clients to resolve SecretRef
mappings without importing pfp_utils.security directly from each implementation.

SecretResolutionError is re-exported so callers can catch it without a direct
dependency on pfp_utils.security.
"""

from __future__ import annotations

from typing import Any

from pfp_utils.security import SecretResolutionError, resolve_secret

__all__ = ["resolve_secret_ref", "SecretResolutionError"]


def resolve_secret_ref(secret_ref: Any) -> str:
    """Resolve a SecretRef-like mapping to its raw string value.

    Accepts a dict-like payload with 'kind' and 'value' fields,
    delegates to pfp_utils.security.resolve_secret, and returns
    the raw resolved string for use in transport clients.

    Args:
        secret_ref: Mapping with 'kind' ('env', 'file', 'provider') and 'value'.

    Returns:
        Resolved secret string value.

    Raises:
        SecretResolutionError: If the reference is invalid or source is unavailable.
    """
    resolved = resolve_secret(secret_ref)
    return resolved.reveal()
