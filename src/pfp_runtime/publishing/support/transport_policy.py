"""Transport policy models and retry/error helpers for publishing components.

Provides three Pydantic transport policy models (TransportPolicy,
TlsTransportPolicy, SftpTransportPolicy) plus retry and error-classification
helpers. IaC models for archivers and clients embed the relevant policy type
as a nested field and validate it via model_validate().

Supersedes the legacy transport_security_policy.py frozen-dataclass approach.
The legacy module remains active for old publishers until Story 38.
"""

from __future__ import annotations

import re
import time
from typing import Any, Callable, Iterable, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from pfp_utils.sanitization import sanitize_text

# ---------------------------------------------------------------------------
# Transport policy models
# ---------------------------------------------------------------------------


class TransportPolicy(BaseModel):
    """Base transport policy embedded in all IaC models.

    Common retry and timeout fields shared by every transport type.

    Attributes:
        timeout_seconds: Maximum seconds to wait for a single transport operation.
            Must be greater than zero.
        max_retries: Maximum number of retry attempts after an initial failure.
            Allowed range: 0–10.
        retry_backoff_seconds: Fixed delay in seconds between retry attempts.
            Zero disables sleep between retries.
    """

    model_config = ConfigDict(extra="forbid")

    timeout_seconds: float = Field(default=60.0, gt=0.0)
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_backoff_seconds: float = Field(default=0.0, ge=0.0)


class TlsTransportPolicy(TransportPolicy):
    """Transport policy for TLS-based transports (HTTP, S3, S3-compat).

    Used in: HttpClientIaC, S3ArchiverIaC, S3CompatArchiverIaC.

    Attributes:
        verify_tls: When True, the transport client verifies the server TLS certificate.
            Set to False only in controlled environments (e.g. local dev with self-signed certs).
            Enforcement is done in the client, not in this model.
    """

    verify_tls: bool = True


class SftpTransportPolicy(TransportPolicy):
    """Transport policy for SSH/SFTP transport.

    Used in: SftpClientIaC.

    Attributes:
        verify_ssh_host_key: When True, the SFTP client verifies the remote host key.
            Disabling is only appropriate in isolated test environments.
        ssh_ciphers: Optional allowlist of SSH encryption ciphers.
            Maps to paramiko SecurityOptions.ciphers. None = paramiko defaults.
        ssh_macs: Optional allowlist of SSH MAC algorithms.
            Maps to paramiko SecurityOptions.digests. None = paramiko defaults.
        ssh_kex: Optional allowlist of SSH key-exchange algorithms.
            Maps to paramiko SecurityOptions.kex. None = paramiko defaults.
        ssh_key_types: Optional allowlist of SSH server host-key types.
            Maps to paramiko SecurityOptions.key_types. None = paramiko defaults.
    """

    verify_ssh_host_key: bool = True
    ssh_ciphers: Optional[List[str]] = None
    ssh_macs: Optional[List[str]] = None
    ssh_kex: Optional[List[str]] = None
    ssh_key_types: Optional[List[str]] = None


# ---------------------------------------------------------------------------
# Retry helpers
# ---------------------------------------------------------------------------


class TransportRetryExhaustedError(RuntimeError):
    """Raised when retry budget is exhausted for a retryable transport error."""

    def __init__(self, message: str = "retry budget exhausted") -> None:
        """Initialise with an optional message and set category to ``retry_exhausted``.

        Args:
            message: Human-readable description of the exhaustion. Defaults to
                ``"retry budget exhausted"``.
        """
        super().__init__(message)
        self.category = "retry_exhausted"


class _TransportCategoryError(RuntimeError):
    """Internal marker exception carrying stable transport category."""

    def __init__(self, *, category: str, message: str) -> None:
        """Initialise with an explicit category code and a human-readable message.

        Args:
            category: Stable transport category code (e.g. ``"tls_failure"``).
            message: Human-readable non-secret error detail.
        """
        super().__init__(message)
        self.category = category


def mark_transport_error(*, category: str, message: str) -> BaseException:
    """Create internal transport exception with explicit stable category.

    Args:
        category: Stable transport category code.
        message: Human-readable non-secret error detail.

    Returns:
        Internal exception carrying category attribute for classifier.
    """
    return _TransportCategoryError(category=category, message=message)


def execute_with_retry(
    operation: Callable[[], Any],
    *,
    policy: TransportPolicy,
    classify_error: Callable[[BaseException], str],
) -> Any:
    """Execute transport operation with bounded retries for retryable failures.

    Args:
        operation: Zero-argument callable performing transport I/O.
        policy: Validated transport policy supplying retry budget and backoff.
        classify_error: Callable that maps exception to transport category.

    Returns:
        Operation result.

    Raises:
        BaseException: Original non-retryable exception.
        TransportRetryExhaustedError: If retry budget is exhausted.
    """
    attempts = 0
    while True:
        try:
            return operation()
        except Exception as exc:
            category = classify_error(exc)
            if not is_retryable_category(category):
                raise
            if attempts >= policy.max_retries:
                raise TransportRetryExhaustedError() from exc
            attempts += 1
            if policy.retry_backoff_seconds > 0:
                time.sleep(policy.retry_backoff_seconds)


def is_retryable_category(category: str) -> bool:
    """Return whether transport error category is retryable.

    Args:
        category: Stable transport category code.

    Returns:
        True if the category warrants a retry attempt, False otherwise.
    """
    return category in {
        "timeout",
        "network",
        "transient_service_failure",
        "remote_5xx",
        "remote_429",
    }


# ---------------------------------------------------------------------------
# Error classification and formatting
# ---------------------------------------------------------------------------


def classify_transport_error(exc: BaseException, *, transport: str) -> str:
    """Classify transport exception into stable category code.

    Args:
        exc: Original transport-layer exception.
        transport: Transport identifier (sftp, s3, s3_compat, http).

    Returns:
        Stable category code string.
    """
    explicit_category = getattr(exc, "category", None)
    if isinstance(explicit_category, str) and explicit_category.strip():
        return explicit_category.strip()

    message = str(exc).lower()

    if "timed out" in message or "timeout" in message:
        return "timeout"
    if "tls" in message or "ssl" in message or "certificate" in message:
        return "tls_failure"
    if "host key" in message:
        return "ssh_host_key_failure"
    if "algorithm" in message or "cipher" in message:
        return "ssh_algorithm_failure"
    if "auth" in message or "credentials" in message or "forbidden" in message:
        return "auth_failure"
    if "access denied" in message or "permission denied" in message:
        return "access_denied"
    if "endpoint" in message or "region" in message:
        return "endpoint_region_mismatch"
    if "remote 4xx" in message or "status 4" in message:
        return "remote_4xx"
    if "remote 5xx" in message or "status 5" in message:
        return "remote_5xx"
    if "connection" in message or "network" in message:
        return "network"

    if transport in ("s3", "s3_compat"):
        return "transient_service_failure"
    return "network"


def format_transport_runtime_error(
    *,
    prefix: str,
    category: str,
    exc: BaseException,
    secret_values: Iterable[str] = (),
) -> str:
    """Build sanitized runtime error text with stable category code.

    Args:
        prefix: Message prefix for publisher context.
        category: Stable transport category code.
        exc: Original exception.
        secret_values: Known secret values that must be redacted.

    Returns:
        Sanitized runtime error message.
    """
    details = sanitize_text(str(exc), secret_values=secret_values)
    details = _redact_sensitive_fragments(details)
    return f"{prefix} [category={category}]: {details}"


def _redact_sensitive_fragments(details: str) -> str:
    """Replace tokens that look like secrets with redaction marker.

    Args:
        details: Raw error detail string potentially containing sensitive tokens.

    Returns:
        String with sensitive word tokens replaced by ``***``.
    """
    pattern = re.compile(
        r"\b[^\s]*(secret|token|api[_-]?key|password)[^\s]*\b", re.IGNORECASE
    )
    return pattern.sub("***", details)


__all__ = [
    "TransportPolicy",
    "TlsTransportPolicy",
    "SftpTransportPolicy",
    "TransportRetryExhaustedError",
    "classify_transport_error",
    "execute_with_retry",
    "format_transport_runtime_error",
    "is_retryable_category",
    "mark_transport_error",
]
