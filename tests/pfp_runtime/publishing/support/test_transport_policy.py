"""Tests for publishing/support/transport_policy.py."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from pydantic import ValidationError

from pfp_runtime.publishing.support.transport_policy import (
    SftpTransportPolicy,
    TlsTransportPolicy,
    TransportPolicy,
    TransportRetryExhaustedError,
    classify_transport_error,
    execute_with_retry,
    format_transport_runtime_error,
    is_retryable_category,
    mark_transport_error,
)

# ---------------------------------------------------------------------------
# TransportPolicy — base validation
# ---------------------------------------------------------------------------


def test_transport_policy_happy_path() -> None:
    """Verify default field values when policy is created with required args."""
    policy = TransportPolicy(timeout_seconds=30.0, max_retries=3)
    assert policy.timeout_seconds == 30.0
    assert policy.max_retries == 3
    assert policy.retry_backoff_seconds == 0.0


def test_transport_policy_no_args_uses_defaults() -> None:
    """Verify TransportPolicy() with no args uses all defaults."""
    policy = TransportPolicy()
    assert policy.timeout_seconds == 60.0
    assert policy.max_retries == 3
    assert policy.retry_backoff_seconds == 0.0


def test_transport_policy_max_retries_upper_bound() -> None:
    """Verify max_retries=10 is accepted and max_retries=11 raises ValidationError."""
    TransportPolicy(timeout_seconds=10.0, max_retries=10)
    with pytest.raises(ValidationError):
        TransportPolicy(timeout_seconds=10.0, max_retries=11)


def test_transport_policy_max_retries_negative() -> None:
    """Verify negative max_retries raises ValidationError."""
    with pytest.raises(ValidationError):
        TransportPolicy(timeout_seconds=10.0, max_retries=-1)


def test_transport_policy_backoff_negative() -> None:
    """Verify negative retry_backoff_seconds raises ValidationError."""
    with pytest.raises(ValidationError):
        TransportPolicy(timeout_seconds=10.0, retry_backoff_seconds=-1.0)


def test_transport_policy_timeout_zero() -> None:
    """Verify timeout_seconds=0.0 raises ValidationError (must be >0)."""
    with pytest.raises(ValidationError):
        TransportPolicy(timeout_seconds=0.0)


def test_transport_policy_timeout_negative() -> None:
    """Verify negative timeout_seconds raises ValidationError."""
    with pytest.raises(ValidationError):
        TransportPolicy(timeout_seconds=-5.0)


def test_transport_policy_extra_field_forbidden() -> None:
    """Verify extra fields are rejected due to extra='forbid' config."""
    with pytest.raises(ValidationError):
        TransportPolicy(timeout_seconds=10.0, unknown_field="x")  # type: ignore[call-arg]


def test_transport_policy_model_validate() -> None:
    """Verify model_validate coerces int timeout to float correctly."""
    policy = TransportPolicy.model_validate({"timeout_seconds": 60, "max_retries": 2})
    assert policy.timeout_seconds == 60.0
    assert policy.max_retries == 2


# ---------------------------------------------------------------------------
# TlsTransportPolicy
# ---------------------------------------------------------------------------


def test_tls_policy_defaults() -> None:
    """Verify verify_tls defaults to True."""
    policy = TlsTransportPolicy(timeout_seconds=30.0, max_retries=0)
    assert policy.verify_tls is True


def test_tls_policy_verify_false_allowed() -> None:
    """Verify verify_tls=False is accepted (enforcement is in clients, not model)."""
    policy = TlsTransportPolicy(timeout_seconds=30.0, verify_tls=False)
    assert policy.verify_tls is False


def test_tls_policy_is_transport_policy() -> None:
    """Verify TlsTransportPolicy is a subclass of TransportPolicy."""
    policy = TlsTransportPolicy(timeout_seconds=10.0)
    assert isinstance(policy, TransportPolicy)


def test_tls_policy_inherits_base_fields() -> None:
    """Verify base fields max_retries and retry_backoff_seconds are accessible."""
    policy = TlsTransportPolicy(
        timeout_seconds=15.0, max_retries=5, retry_backoff_seconds=2.0
    )
    assert policy.max_retries == 5
    assert policy.retry_backoff_seconds == 2.0


# ---------------------------------------------------------------------------
# SftpTransportPolicy
# ---------------------------------------------------------------------------


def test_sftp_policy_defaults() -> None:
    """Verify verify_ssh_host_key defaults to True and all algorithm lists default to None."""
    policy = SftpTransportPolicy(timeout_seconds=60.0)
    assert policy.verify_ssh_host_key is True
    assert policy.ssh_ciphers is None
    assert policy.ssh_macs is None
    assert policy.ssh_kex is None
    assert policy.ssh_key_types is None


def test_sftp_policy_algorithm_fields() -> None:
    """Verify each SSH algorithm field is stored independently."""
    policy = SftpTransportPolicy(
        timeout_seconds=60.0,
        ssh_ciphers=["aes256-ctr", "chacha20-poly1305@openssh.com"],
        ssh_macs=["hmac-sha2-256"],
        ssh_kex=["ecdh-sha2-nistp256"],
        ssh_key_types=["ssh-ed25519"],
    )
    assert policy.ssh_ciphers == ["aes256-ctr", "chacha20-poly1305@openssh.com"]
    assert policy.ssh_macs == ["hmac-sha2-256"]
    assert policy.ssh_kex == ["ecdh-sha2-nistp256"]
    assert policy.ssh_key_types == ["ssh-ed25519"]


def test_sftp_policy_is_transport_policy() -> None:
    """Verify SftpTransportPolicy is a subclass of TransportPolicy."""
    policy = SftpTransportPolicy(timeout_seconds=10.0)
    assert isinstance(policy, TransportPolicy)


def test_sftp_policy_not_tls() -> None:
    """Verify SftpTransportPolicy is not a subclass of TlsTransportPolicy."""
    policy = SftpTransportPolicy(timeout_seconds=10.0)
    assert not isinstance(policy, TlsTransportPolicy)


# ---------------------------------------------------------------------------
# execute_with_retry
# ---------------------------------------------------------------------------


def test_execute_with_retry_success_first_attempt() -> None:
    """Verify operation result is returned immediately on first successful attempt."""
    policy = TransportPolicy(timeout_seconds=10.0, max_retries=3)
    result = execute_with_retry(
        lambda: 42, policy=policy, classify_error=lambda e: "timeout"
    )
    assert result == 42


def test_execute_with_retry_exhausted() -> None:
    """Verify TransportRetryExhaustedError is raised after initial + max_retries attempts."""
    policy = TransportPolicy(
        timeout_seconds=10.0, max_retries=2, retry_backoff_seconds=0.0
    )
    calls = [0]

    def flaky() -> None:
        calls[0] += 1
        raise RuntimeError("timed out")

    with pytest.raises(TransportRetryExhaustedError):
        execute_with_retry(
            flaky,
            policy=policy,
            classify_error=lambda e: "timeout",
        )
    assert calls[0] == 3  # initial + 2 retries


def test_execute_with_retry_non_retryable_raises_original() -> None:
    """Verify non-retryable error propagates immediately without retry."""
    policy = TransportPolicy(timeout_seconds=10.0, max_retries=5)
    original = ValueError("auth error")

    with pytest.raises(ValueError, match="auth error"):
        execute_with_retry(
            lambda: (_ for _ in ()).throw(original),
            policy=policy,
            classify_error=lambda e: "auth_failure",
        )


def test_execute_with_retry_success_after_one_failure() -> None:
    """Verify successful result is returned when operation succeeds on second attempt."""
    policy = TransportPolicy(
        timeout_seconds=10.0, max_retries=3, retry_backoff_seconds=0.0
    )
    attempts = [0]

    def operation() -> str:
        attempts[0] += 1
        if attempts[0] < 2:
            raise RuntimeError("network")
        return "ok"

    result = execute_with_retry(
        operation,
        policy=policy,
        classify_error=lambda e: "network",
    )
    assert result == "ok"
    assert attempts[0] == 2


def test_execute_with_retry_no_sleep_when_backoff_zero() -> None:
    """Verify time.sleep is not called when retry_backoff_seconds=0.0."""
    policy = TransportPolicy(
        timeout_seconds=10.0, max_retries=1, retry_backoff_seconds=0.0
    )
    calls = [0]

    def flaky() -> None:
        calls[0] += 1
        raise RuntimeError("network error")

    with patch(
        "pfp_runtime.publishing.support.transport_policy.time.sleep"
    ) as mock_sleep:
        with pytest.raises(TransportRetryExhaustedError):
            execute_with_retry(flaky, policy=policy, classify_error=lambda e: "network")
        mock_sleep.assert_not_called()


def test_execute_with_retry_sleeps_when_backoff_set() -> None:
    """Verify time.sleep is called with the configured backoff value between retries."""
    policy = TransportPolicy(
        timeout_seconds=10.0, max_retries=1, retry_backoff_seconds=0.5
    )

    def flaky() -> None:
        raise RuntimeError("network error")

    with patch(
        "pfp_runtime.publishing.support.transport_policy.time.sleep"
    ) as mock_sleep:
        with pytest.raises(TransportRetryExhaustedError):
            execute_with_retry(flaky, policy=policy, classify_error=lambda e: "network")
        mock_sleep.assert_called_once_with(0.5)


# ---------------------------------------------------------------------------
# is_retryable_category
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "category",
    ["timeout", "network", "transient_service_failure", "remote_5xx", "remote_429"],
)
def test_is_retryable_true(category: str) -> None:
    """Verify retryable categories return True."""
    assert is_retryable_category(category) is True


@pytest.mark.parametrize(
    "category",
    ["auth_failure", "tls_failure", "access_denied", "remote_4xx", "retry_exhausted"],
)
def test_is_retryable_false(category: str) -> None:
    """Verify non-retryable categories return False."""
    assert is_retryable_category(category) is False


# ---------------------------------------------------------------------------
# classify_transport_error
# ---------------------------------------------------------------------------


def test_classify_explicit_category() -> None:
    """Verify explicit category attribute on exception takes precedence over message."""
    exc = RuntimeError("something")
    exc.category = "timeout"  # type: ignore[attr-defined]
    assert classify_transport_error(exc, transport="http") == "timeout"


def test_classify_timed_out_message() -> None:
    """Verify 'timed out' in message maps to timeout category."""
    assert (
        classify_transport_error(RuntimeError("timed out"), transport="http")
        == "timeout"
    )


def test_classify_ssl_message() -> None:
    """Verify 'ssl' in message maps to tls_failure category."""
    assert (
        classify_transport_error(RuntimeError("ssl error"), transport="http")
        == "tls_failure"
    )


def test_classify_host_key() -> None:
    """Verify 'host key' in message maps to ssh_host_key_failure category."""
    assert (
        classify_transport_error(RuntimeError("host key mismatch"), transport="sftp")
        == "ssh_host_key_failure"
    )


def test_classify_algorithm() -> None:
    """Verify 'cipher' in message maps to ssh_algorithm_failure category."""
    assert (
        classify_transport_error(RuntimeError("cipher not supported"), transport="sftp")
        == "ssh_algorithm_failure"
    )


def test_classify_auth() -> None:
    """Verify 'auth' in message maps to auth_failure category."""
    assert (
        classify_transport_error(RuntimeError("auth failed"), transport="http")
        == "auth_failure"
    )


def test_classify_unknown_s3() -> None:
    """Verify unrecognized error on s3 transport defaults to transient_service_failure."""
    assert (
        classify_transport_error(RuntimeError("something odd"), transport="s3")
        == "transient_service_failure"
    )


def test_classify_unknown_s3_compat() -> None:
    """Verify unrecognized error on s3_compat transport defaults to transient_service_failure."""
    assert (
        classify_transport_error(RuntimeError("something odd"), transport="s3_compat")
        == "transient_service_failure"
    )


def test_classify_unknown_http() -> None:
    """Verify unrecognized error on http transport defaults to network category."""
    assert (
        classify_transport_error(RuntimeError("something odd"), transport="http")
        == "network"
    )


def test_classify_access_denied() -> None:
    """Verify 'access denied' in message maps to access_denied category."""
    assert (
        classify_transport_error(RuntimeError("access denied"), transport="http")
        == "access_denied"
    )


def test_classify_endpoint_region() -> None:
    """Verify 'region' in message maps to endpoint_region_mismatch category."""
    assert (
        classify_transport_error(RuntimeError("wrong region"), transport="s3")
        == "endpoint_region_mismatch"
    )


def test_classify_remote_4xx() -> None:
    """Verify 'status 4xx' in message maps to remote_4xx category."""
    assert (
        classify_transport_error(
            RuntimeError("status 400 bad request"), transport="http"
        )
        == "remote_4xx"
    )


def test_classify_remote_5xx() -> None:
    """Verify 'status 5xx' in message maps to remote_5xx category."""
    assert (
        classify_transport_error(
            RuntimeError("status 500 internal server error"), transport="http"
        )
        == "remote_5xx"
    )


def test_classify_connection_error() -> None:
    """Verify 'connection' keyword in message maps to network category."""
    assert (
        classify_transport_error(RuntimeError("connection refused"), transport="http")
        == "network"
    )


# ---------------------------------------------------------------------------
# format_transport_runtime_error
# ---------------------------------------------------------------------------


def test_format_error_contains_prefix_and_category() -> None:
    """Verify formatted message contains prefix and category tag."""
    msg = format_transport_runtime_error(
        prefix="s3_archiver",
        category="timeout",
        exc=RuntimeError("connection timed out"),
    )
    assert "s3_archiver" in msg
    assert "[category=timeout]" in msg


def test_format_error_redacts_secret_values() -> None:
    """Verify known secret values passed in secret_values are redacted from output."""
    msg = format_transport_runtime_error(
        prefix="http_client",
        category="auth_failure",
        exc=RuntimeError("token sk-1234 rejected"),
        secret_values=["sk-1234"],
    )
    assert "sk-1234" not in msg


def test_format_error_redacts_sensitive_fragment() -> None:
    """Verify tokens matching sensitive-word pattern (api_key) are auto-redacted."""
    msg = format_transport_runtime_error(
        prefix="sftp",
        category="auth_failure",
        exc=RuntimeError("api_key_value is wrong"),
    )
    assert "api_key_value" not in msg


# ---------------------------------------------------------------------------
# mark_transport_error
# ---------------------------------------------------------------------------


def test_mark_transport_error_carries_category() -> None:
    """Verify created exception carries the given category attribute and message."""
    exc = mark_transport_error(category="tls_failure", message="cert invalid")
    assert getattr(exc, "category", None) == "tls_failure"
    assert "cert invalid" in str(exc)
