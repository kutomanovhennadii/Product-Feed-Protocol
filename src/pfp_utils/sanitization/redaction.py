"""Redaction helpers for runtime secret-aware logging and reporting.

This module provides two stateless free functions for masking sensitive
fragments in text and structured payloads before they reach logs, error
reports, or diagnostics surfaces.

Functions:
    - **sanitize_text(value, *, secret_values=(), mask="***")**: redact a
      plain string. Masks three common patterns automatically:

        1. ``Bearer <token>`` (Authorization headers).
        2. Inline ``token=...``/``api_key=...``/``password=...``/``secret=...``
           key-value pairs in free-form text.
        3. URL query parameters with sensitive names
           (``?token=...``, ``&api_key=...``, etc.).

      Additionally, any explicitly supplied ``secret_values`` (known raw
      secrets) are replaced verbatim. Non-string input returns the mask.

    - **sanitize_mapping(payload, *, mask="***")**: return a deep copy of a
      mapping with sensitive-keyed entries masked. A key is considered
      sensitive if its lowercased name contains any of
      ``secret``/``token``/``password``/``api_key``. Nested dicts and lists
      are processed recursively; string leaves are passed through
      ``sanitize_text`` so inline patterns are masked as well.

When to use:
    Call these functions on any string/mapping that may carry secrets before
    logging it, returning it in a ``Diagnostic`` or ``ExecutionReport``, or
    rendering it in an exception message. Prefer ``sanitize_mapping`` for
    config snapshots and ``sanitize_text`` for free-form messages.

Guarantees:
    - Functions never mutate the input value.
    - Non-string / unknown types inside mappings are preserved as-is.
    - The mask never contains the original secret.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Mapping

_DEFAULT_MASK = "***"
_URL_SECRET_PARAM_PATTERN = re.compile(
    r"([?&](?:token|api[_-]?key|password|secret|access[_-]?token)=)([^&#\s]+)",
    re.IGNORECASE,
)
_INLINE_SECRET_PATTERN = re.compile(
    r"\b(token|api[_-]?key|password|secret|access[_-]?token)\b\s*[:=]\s*([^\s,;&#]+)",
    re.IGNORECASE,
)
_BEARER_PATTERN = re.compile(r"(Bearer\s+)([^\s]+)", re.IGNORECASE)


def sanitize_text(
    value: str,
    *,
    secret_values: Iterable[str] = (),
    mask: str = _DEFAULT_MASK,
) -> str:
    """Sanitize arbitrary text by redacting sensitive fragments.

    Args:
        value: Source text potentially containing sensitive content.
        secret_values: Known raw secret values to replace exactly.
        mask: Mask token used for replacement.

    Returns:
        Sanitized text safe for logs/errors/diagnostics surfaces.
    """
    if not isinstance(value, str):
        return mask

    sanitized = value
    for secret in secret_values:
        if isinstance(secret, str) and secret:
            sanitized = sanitized.replace(secret, mask)

    sanitized = _BEARER_PATTERN.sub(r"\1" + mask, sanitized)
    sanitized = _URL_SECRET_PARAM_PATTERN.sub(r"\1" + mask, sanitized)
    sanitized = _INLINE_SECRET_PATTERN.sub(lambda m: m.group(1) + "=" + mask, sanitized)
    return sanitized


def sanitize_mapping(
    payload: Mapping[str, Any],
    *,
    mask: str = _DEFAULT_MASK,
) -> Mapping[str, Any]:
    """Return safe copy of mapping with secret-like keys masked recursively."""

    def _sanitize_value(value: Any) -> Any:
        if isinstance(value, Mapping):
            return sanitize_mapping(value, mask=mask)
        if isinstance(value, list):
            return [_sanitize_value(item) for item in value]
        if isinstance(value, str):
            return sanitize_text(value, mask=mask)
        return value

    sanitized = {}
    for key, raw_value in payload.items():
        key_text = str(key)
        lower_key = key_text.lower()
        if any(
            token in lower_key for token in ("secret", "token", "password", "api_key")
        ):
            sanitized[key_text] = mask
            continue
        sanitized[key_text] = _sanitize_value(raw_value)
    return sanitized
