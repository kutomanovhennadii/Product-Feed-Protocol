"""Tests for publishing/clients/sftp_client.py."""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import MagicMock, patch

import paramiko
import paramiko.message as paramiko_message
import pytest
from pydantic import ValidationError

from pfp_runtime.publishing.clients.client_contract import (
    DeliveryClient,
    DeliveryResult,
)
from pfp_runtime.publishing.clients.sftp_client import (
    SftpClientError,
    SftpClientIaC,
    SftpDeliveryClient,
    _load_private_key,
    _parse_host_key,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_iac(**kwargs: Any) -> SftpClientIaC:
    """Build a SftpClientIaC with verify_ssh_host_key=False by default."""
    defaults: Dict[str, Any] = {
        "host": "sftp.example.com",
        "username": "feed-user",
        "remote_path": "/feeds/product.jsonl.gz",
        "private_key_ref": {"kind": "env", "value": "SFTP_KEY"},
        "transport": {"timeout_seconds": 10.0, "verify_ssh_host_key": False},
    }
    defaults.update(kwargs)
    return SftpClientIaC.model_validate(defaults)


def _make_mock_sftp() -> MagicMock:
    mock_file = MagicMock()
    mock_sftp = MagicMock(spec=paramiko.SFTPClient)
    mock_sftp.open.return_value = mock_file
    return mock_sftp


def _make_client(iac: SftpClientIaC, monkeypatch: Any) -> SftpDeliveryClient:
    """Build a SftpDeliveryClient with injected sftp_factory (no real SFTP)."""
    monkeypatch.setenv("SFTP_KEY", "fake-pem-key-for-test")
    mock_sftp = _make_mock_sftp()
    return SftpDeliveryClient(iac, sftp_factory=lambda: mock_sftp)


def _patch_paramiko_key_types(mock_paramiko: Any) -> None:
    """Populate key-related paramiko attributes on a patched module mock."""
    mock_paramiko.RSAKey = paramiko.RSAKey
    mock_paramiko.ECDSAKey = paramiko.ECDSAKey
    mock_paramiko.Ed25519Key = paramiko.Ed25519Key
    dss_key_class = getattr(paramiko, "DSSKey", None)
    if dss_key_class is not None:
        mock_paramiko.DSSKey = dss_key_class
    mock_paramiko.message = paramiko_message


# ---------------------------------------------------------------------------
# IaC validation
# ---------------------------------------------------------------------------


def test_iac_host_required() -> None:
    """Verify host is required."""
    with pytest.raises(ValidationError):
        SftpClientIaC.model_validate(
            {
                "username": "u",
                "remote_path": "/p",
                "private_key_ref": {"kind": "env", "value": "K"},
                "transport": {"timeout_seconds": 10.0, "verify_ssh_host_key": False},
            }
        )


def test_iac_username_required() -> None:
    """Verify username is required."""
    with pytest.raises(ValidationError):
        SftpClientIaC.model_validate(
            {
                "host": "h",
                "remote_path": "/p",
                "private_key_ref": {"kind": "env", "value": "K"},
                "transport": {"timeout_seconds": 10.0, "verify_ssh_host_key": False},
            }
        )


def test_iac_remote_path_required() -> None:
    """Verify remote_path is required."""
    with pytest.raises(ValidationError):
        SftpClientIaC.model_validate(
            {
                "host": "h",
                "username": "u",
                "private_key_ref": {"kind": "env", "value": "K"},
                "transport": {"timeout_seconds": 10.0, "verify_ssh_host_key": False},
            }
        )


def test_iac_both_auth_refs_forbidden() -> None:
    """Verify password_ref and private_key_ref simultaneously raises ValidationError."""
    with pytest.raises(ValidationError):
        _make_iac(
            password_ref={"kind": "env", "value": "PASS"},
            private_key_ref={"kind": "env", "value": "KEY"},
        )


def test_iac_no_auth_ref_forbidden() -> None:
    """Verify omitting both password_ref and private_key_ref raises ValidationError."""
    with pytest.raises(ValidationError):
        SftpClientIaC.model_validate(
            {
                "host": "h",
                "username": "u",
                "remote_path": "/p",
                "transport": {"timeout_seconds": 10.0, "verify_ssh_host_key": False},
            }
        )


def test_iac_port_defaults_to_22() -> None:
    """Verify port defaults to 22."""
    iac = _make_iac()
    assert iac.port == 22


def test_iac_transport_optional() -> None:
    """Verify transport block is optional (uses SftpTransportPolicy defaults)."""
    iac = SftpClientIaC.model_validate(
        {
            "host": "h",
            "username": "u",
            "remote_path": "/p",
            "private_key_ref": {"kind": "env", "value": "K"},
            "host_key_ref": {"kind": "env", "value": "HK"},
            # no transport block → uses defaults (verify_ssh_host_key=True requires host_key_ref)
        }
    )
    assert iac.transport.timeout_seconds == 60.0


def test_iac_extra_field_forbidden() -> None:
    """Verify extra fields raise ValidationError."""
    with pytest.raises(ValidationError):
        _make_iac(unknown="x")


def test_iac_verify_host_key_true_requires_host_key_ref() -> None:
    """Verify verify_ssh_host_key=True without host_key_ref raises ValidationError."""
    with pytest.raises(ValidationError, match="host_key_ref"):
        SftpClientIaC.model_validate(
            {
                "host": "h",
                "username": "u",
                "remote_path": "/p",
                "private_key_ref": {"kind": "env", "value": "K"},
                "transport": {"timeout_seconds": 10.0, "verify_ssh_host_key": True},
            }
        )


def test_iac_verify_host_key_false_without_host_key_ref_ok() -> None:
    """Verify verify_ssh_host_key=False without host_key_ref is valid."""
    iac = _make_iac()  # uses verify_ssh_host_key=False by default
    assert iac.host_key_ref is None


def test_iac_atomic_write_defaults_true() -> None:
    """Verify atomic_write defaults to True."""
    assert _make_iac().atomic_write is True


def test_iac_atomic_write_can_be_disabled() -> None:
    """Verify atomic_write=False is accepted."""
    iac = _make_iac(atomic_write=False)
    assert iac.atomic_write is False


# ---------------------------------------------------------------------------
# __init__ — credential resolution
# ---------------------------------------------------------------------------


def test_init_resolves_private_key_from_env(monkeypatch: Any) -> None:
    """Verify __init__ resolves private_key_ref from environment variable."""
    monkeypatch.setenv("SFTP_KEY", "pem-content")
    iac = _make_iac()
    client = SftpDeliveryClient(iac, sftp_factory=lambda: _make_mock_sftp())
    assert client._private_key_pem == "pem-content"
    assert client._password is None


def test_init_resolves_password_from_env(monkeypatch: Any) -> None:
    """Verify __init__ resolves password_ref from environment variable."""
    monkeypatch.setenv("SFTP_PASS", "s3cr3t")
    iac = _make_iac(
        private_key_ref=None,
        password_ref={"kind": "env", "value": "SFTP_PASS"},
    )
    client = SftpDeliveryClient(iac, sftp_factory=lambda: _make_mock_sftp())
    assert client._password == "s3cr3t"
    assert client._private_key_pem is None


def test_init_credential_resolution_failure_raises_sftp_error(monkeypatch: Any) -> None:
    """Verify SecretResolutionError is wrapped in SftpClientError."""
    monkeypatch.delenv("SFTP_KEY", raising=False)
    iac = _make_iac()
    with pytest.raises(SftpClientError, match="Failed to resolve SFTP credential"):
        SftpDeliveryClient(iac, sftp_factory=lambda: _make_mock_sftp())


def test_init_does_not_connect_without_open(monkeypatch: Any) -> None:
    """Verify sftp_factory is not called during __init__."""
    monkeypatch.setenv("SFTP_KEY", "pem")
    factory_calls = [0]

    def factory() -> MagicMock:
        factory_calls[0] += 1
        return _make_mock_sftp()

    iac = _make_iac()
    SftpDeliveryClient(iac, sftp_factory=factory)
    assert factory_calls[0] == 0


def test_init_parses_host_key_when_verify_enabled(monkeypatch: Any) -> None:
    """Verify host_key_ref is resolved and parsed when verify_ssh_host_key=True."""
    # Generate a real RSA key to use as the expected host key
    key = paramiko.RSAKey.generate(2048)
    raw = f"ssh-rsa {key.get_base64()}"
    monkeypatch.setenv("SFTP_KEY", "pem")
    monkeypatch.setenv("HOST_KEY", raw)
    iac = SftpClientIaC.model_validate(
        {
            "host": "h",
            "username": "u",
            "remote_path": "/p",
            "private_key_ref": {"kind": "env", "value": "SFTP_KEY"},
            "host_key_ref": {"kind": "env", "value": "HOST_KEY"},
            "transport": {"timeout_seconds": 10.0, "verify_ssh_host_key": True},
        }
    )
    client = SftpDeliveryClient(iac, sftp_factory=lambda: _make_mock_sftp())
    assert client._expected_host_key is not None
    assert client._expected_host_key.get_name() == "ssh-rsa"


def test_init_invalid_host_key_format_raises_sftp_error(monkeypatch: Any) -> None:
    """Verify malformed host_key_ref raises SftpClientError in __init__."""
    monkeypatch.setenv("SFTP_KEY", "pem")
    monkeypatch.setenv("HOST_KEY", "not-valid-format")  # no space
    iac = SftpClientIaC.model_validate(
        {
            "host": "h",
            "username": "u",
            "remote_path": "/p",
            "private_key_ref": {"kind": "env", "value": "SFTP_KEY"},
            "host_key_ref": {"kind": "env", "value": "HOST_KEY"},
            "transport": {"timeout_seconds": 10.0, "verify_ssh_host_key": True},
        }
    )
    with pytest.raises(SftpClientError):
        SftpDeliveryClient(iac, sftp_factory=lambda: _make_mock_sftp())


def test_init_host_key_ref_resolution_failure(monkeypatch: Any) -> None:
    """Verify missing host_key_ref env var raises SftpClientError in __init__."""
    monkeypatch.setenv("SFTP_KEY", "pem")
    monkeypatch.delenv("HOST_KEY", raising=False)
    iac = SftpClientIaC.model_validate(
        {
            "host": "h",
            "username": "u",
            "remote_path": "/p",
            "private_key_ref": {"kind": "env", "value": "SFTP_KEY"},
            "host_key_ref": {"kind": "env", "value": "HOST_KEY"},
            "transport": {"timeout_seconds": 10.0, "verify_ssh_host_key": True},
        }
    )
    with pytest.raises(SftpClientError, match="Failed to resolve host_key_ref"):
        SftpDeliveryClient(iac, sftp_factory=lambda: _make_mock_sftp())


# ---------------------------------------------------------------------------
# open()
# ---------------------------------------------------------------------------


def test_open_calls_sftp_factory(monkeypatch: Any) -> None:
    """Verify open() invokes sftp_factory exactly once."""
    monkeypatch.setenv("SFTP_KEY", "pem")
    mock_sftp = _make_mock_sftp()
    calls = [0]

    def factory() -> MagicMock:
        calls[0] += 1
        return mock_sftp

    iac = _make_iac()
    client = SftpDeliveryClient(iac, sftp_factory=factory)
    client.open()
    assert calls[0] == 1


def test_open_atomic_write_false_opens_remote_path(monkeypatch: Any) -> None:
    """Verify open() calls sftp.open(remote_path, 'wb') when atomic_write=False."""
    monkeypatch.setenv("SFTP_KEY", "pem")
    mock_sftp = _make_mock_sftp()
    iac = _make_iac(atomic_write=False)
    client = SftpDeliveryClient(iac, sftp_factory=lambda: mock_sftp)
    client.open()
    mock_sftp.open.assert_called_once_with("/feeds/product.jsonl.gz", "wb")


def test_open_atomic_write_true_opens_tmp_path(monkeypatch: Any) -> None:
    """Verify open() opens a .tmp file when atomic_write=True (default)."""
    monkeypatch.setenv("SFTP_KEY", "pem")
    mock_sftp = _make_mock_sftp()
    iac = _make_iac()  # atomic_write=True by default
    client = SftpDeliveryClient(iac, sftp_factory=lambda: mock_sftp)
    client.open()
    call_args = mock_sftp.open.call_args
    opened_path = call_args[0][0]
    assert opened_path.startswith("/feeds/product.jsonl.gz.")
    assert opened_path.endswith(".tmp")
    assert call_args[0][1] == "wb"


def test_open_enables_pipelining_on_remote_file(monkeypatch: Any) -> None:
    """Verify open() calls set_pipelined(True) on the opened remote file."""
    monkeypatch.setenv("SFTP_KEY", "pem")
    mock_sftp = _make_mock_sftp()
    iac = _make_iac()
    client = SftpDeliveryClient(iac, sftp_factory=lambda: mock_sftp)
    client.open()
    remote_file = mock_sftp.open.return_value
    remote_file.set_pipelined.assert_called_once_with(True)


def test_open_sftp_factory_raises_sftp_error_propagated(monkeypatch: Any) -> None:
    """Verify SftpClientError from sftp_factory is propagated without wrapping."""
    monkeypatch.setenv("SFTP_KEY", "pem")

    def raising_factory() -> MagicMock:
        raise SftpClientError("factory failure")

    client = SftpDeliveryClient(_make_iac(), sftp_factory=raising_factory)
    with pytest.raises(SftpClientError, match="factory failure"):
        client.open()


def test_double_open_closes_previous_connection(monkeypatch: Any) -> None:
    """Verify second open() closes the previous SFTP connection first."""
    monkeypatch.setenv("SFTP_KEY", "pem")
    mock_sftp1 = _make_mock_sftp()
    mock_sftp2 = _make_mock_sftp()
    sftps = [mock_sftp1, mock_sftp2]
    idx = [0]

    def factory() -> MagicMock:
        sftp = sftps[idx[0]]
        idx[0] += 1
        return sftp

    iac = _make_iac()
    client = SftpDeliveryClient(iac, sftp_factory=factory)
    client.open()
    client.open()  # second call — should close mock_sftp1 first
    mock_sftp1.close.assert_called()


# ---------------------------------------------------------------------------
# send_chunk()
# ---------------------------------------------------------------------------


def test_send_chunk_before_open_raises(monkeypatch: Any) -> None:
    """Verify send_chunk() before open() raises SftpClientError."""
    monkeypatch.setenv("SFTP_KEY", "pem")
    client = SftpDeliveryClient(_make_iac(), sftp_factory=lambda: _make_mock_sftp())
    with pytest.raises(SftpClientError, match="before open"):
        client.send_chunk(b"data")


def test_send_chunk_after_finalize_raises(monkeypatch: Any) -> None:
    """Verify send_chunk() after finalize() raises SftpClientError."""
    monkeypatch.setenv("SFTP_KEY", "pem")
    mock_sftp = _make_mock_sftp()
    client = SftpDeliveryClient(_make_iac(), sftp_factory=lambda: mock_sftp)
    client.open()
    client.finalize()
    with pytest.raises(SftpClientError, match="after finalize"):
        client.send_chunk(b"late")


def test_send_chunk_writes_to_remote_file(monkeypatch: Any) -> None:
    """Verify send_chunk() calls remote_file.write() with the chunk."""
    monkeypatch.setenv("SFTP_KEY", "pem")
    mock_sftp = _make_mock_sftp()
    client = SftpDeliveryClient(_make_iac(), sftp_factory=lambda: mock_sftp)
    client.open()
    client.send_chunk(b"payload")
    mock_sftp.open.return_value.write.assert_called_once_with(b"payload")


# ---------------------------------------------------------------------------
# finalize()
# ---------------------------------------------------------------------------


def test_finalize_before_open_raises(monkeypatch: Any) -> None:
    """Verify finalize() before open() raises SftpClientError."""
    monkeypatch.setenv("SFTP_KEY", "pem")
    client = SftpDeliveryClient(_make_iac(), sftp_factory=lambda: _make_mock_sftp())
    with pytest.raises(SftpClientError, match="before open"):
        client.finalize()


def test_finalize_double_call_raises(monkeypatch: Any) -> None:
    """Verify calling finalize() twice raises SftpClientError."""
    monkeypatch.setenv("SFTP_KEY", "pem")
    mock_sftp = _make_mock_sftp()
    client = SftpDeliveryClient(_make_iac(), sftp_factory=lambda: mock_sftp)
    client.open()
    client.finalize()
    with pytest.raises(SftpClientError, match="already called"):
        client.finalize()


def test_finalize_closes_remote_file(monkeypatch: Any) -> None:
    """Verify finalize() calls remote_file.close()."""
    monkeypatch.setenv("SFTP_KEY", "pem")
    mock_sftp = _make_mock_sftp()
    client = SftpDeliveryClient(_make_iac(), sftp_factory=lambda: mock_sftp)
    client.open()
    client.finalize()
    mock_sftp.open.return_value.close.assert_called()


def test_finalize_closes_sftp_connection(monkeypatch: Any) -> None:
    """Verify finalize() closes the SFTP client."""
    monkeypatch.setenv("SFTP_KEY", "pem")
    mock_sftp = _make_mock_sftp()
    client = SftpDeliveryClient(_make_iac(), sftp_factory=lambda: mock_sftp)
    client.open()
    client.finalize()
    mock_sftp.close.assert_called()


def test_finalize_returns_delivery_result(monkeypatch: Any) -> None:
    """Verify finalize() returns DeliveryResult(skipped=False, status_code=0)."""
    monkeypatch.setenv("SFTP_KEY", "pem")
    mock_sftp = _make_mock_sftp()
    client = SftpDeliveryClient(_make_iac(), sftp_factory=lambda: mock_sftp)
    client.open()
    result = client.finalize()
    assert isinstance(result, DeliveryResult)
    assert result.skipped is False
    assert result.status_code == 0


# ---------------------------------------------------------------------------
# atomic_write
# ---------------------------------------------------------------------------


def test_finalize_renames_tmp_to_remote_path(monkeypatch: Any) -> None:
    """Verify finalize() calls sftp.rename(tmp_path, remote_path) when atomic_write=True."""
    monkeypatch.setenv("SFTP_KEY", "pem")
    mock_sftp = _make_mock_sftp()
    iac = _make_iac()  # atomic_write=True by default
    client = SftpDeliveryClient(iac, sftp_factory=lambda: mock_sftp)
    client.open()
    tmp_path = client._tmp_path
    assert tmp_path is not None
    client.finalize()
    mock_sftp.rename.assert_called_once_with(tmp_path, "/feeds/product.jsonl.gz")


def test_finalize_atomic_write_false_does_not_rename(monkeypatch: Any) -> None:
    """Verify finalize() does not call sftp.rename() when atomic_write=False."""
    monkeypatch.setenv("SFTP_KEY", "pem")
    mock_sftp = _make_mock_sftp()
    iac = _make_iac(atomic_write=False)
    client = SftpDeliveryClient(iac, sftp_factory=lambda: mock_sftp)
    client.open()
    client.finalize()
    mock_sftp.rename.assert_not_called()


def test_finalize_rename_failure_raises_sftp_error(monkeypatch: Any) -> None:
    """Verify SftpClientError raised when sftp.rename() fails."""
    monkeypatch.setenv("SFTP_KEY", "pem")
    mock_sftp = _make_mock_sftp()
    mock_sftp.rename.side_effect = OSError("permission denied")
    iac = _make_iac()
    client = SftpDeliveryClient(iac, sftp_factory=lambda: mock_sftp)
    client.open()
    with pytest.raises(SftpClientError, match="atomic rename failed"):
        client.finalize()


def test_finalize_rename_failure_removes_tmp_file(monkeypatch: Any) -> None:
    """Verify tmp file is removed best-effort when sftp.rename() fails."""
    monkeypatch.setenv("SFTP_KEY", "pem")
    mock_sftp = _make_mock_sftp()
    mock_sftp.rename.side_effect = OSError("permission denied")
    iac = _make_iac()
    client = SftpDeliveryClient(iac, sftp_factory=lambda: mock_sftp)
    client.open()
    tmp_path = client._tmp_path
    with pytest.raises(SftpClientError):
        client.finalize()
    mock_sftp.remove.assert_called_once_with(tmp_path)


def test_finalize_rename_failure_remove_also_raises_is_suppressed(
    monkeypatch: Any,
) -> None:
    """Verify sftp.remove() exception during rename cleanup is suppressed."""
    monkeypatch.setenv("SFTP_KEY", "pem")
    mock_sftp = _make_mock_sftp()
    mock_sftp.rename.side_effect = OSError("rename failed")
    mock_sftp.remove.side_effect = OSError("remove failed")
    iac = _make_iac()
    client = SftpDeliveryClient(iac, sftp_factory=lambda: mock_sftp)
    client.open()
    with pytest.raises(SftpClientError, match="atomic rename failed"):
        client.finalize()  # remove error must be suppressed, rename error propagated


def test_double_open_removes_unrenamed_tmp_file(monkeypatch: Any) -> None:
    """Verify second open() removes the tmp file from the abandoned first cycle."""
    monkeypatch.setenv("SFTP_KEY", "pem")
    mock_sftp1 = _make_mock_sftp()
    mock_sftp2 = _make_mock_sftp()
    sftps = [mock_sftp1, mock_sftp2]
    idx = [0]

    def factory() -> MagicMock:
        sftp = sftps[idx[0]]
        idx[0] += 1
        return sftp

    iac = _make_iac()  # atomic_write=True
    client = SftpDeliveryClient(iac, sftp_factory=factory)
    client.open()
    tmp_path = client._tmp_path
    client.open()  # abandons first cycle without finalize
    mock_sftp1.remove.assert_called_once_with(tmp_path)


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------


def test_close_connection_remote_file_close_raises_is_suppressed(
    monkeypatch: Any,
) -> None:
    """Verify _close_connection() suppresses remote_file.close() error during double open."""
    monkeypatch.setenv("SFTP_KEY", "pem")
    mock_sftp = _make_mock_sftp()
    client = SftpDeliveryClient(_make_iac(), sftp_factory=lambda: mock_sftp)
    client.open()
    # Make the already-opened remote file's close() raise inside _close_connection()
    client._remote_file.close.side_effect = OSError("io error in _close_connection")
    # Second open calls _close_connection() while _remote_file is still set — must not raise
    client.open()
    client.finalize()


def test_close_connection_remove_raises_is_suppressed(monkeypatch: Any) -> None:
    """Verify _close_connection() suppresses sftp.remove() error during tmp cleanup."""
    monkeypatch.setenv("SFTP_KEY", "pem")
    mock_sftp = _make_mock_sftp()
    iac = _make_iac()  # atomic_write=True
    client = SftpDeliveryClient(iac, sftp_factory=lambda: mock_sftp)
    client.open()
    # Make sftp.remove() raise so the except clause in _close_connection() is hit
    mock_sftp.remove.side_effect = OSError("remove error")
    # Second open calls _close_connection() while _tmp_path is set — remove raises, must be suppressed
    client.open()
    client.finalize()


def test_close_connection_paramiko_transport_close_raises_is_suppressed(
    monkeypatch: Any,
) -> None:
    """Verify _close_connection() suppresses _paramiko_transport.close() exception."""
    monkeypatch.setenv("SFTP_KEY", "pem")
    mock_sftp = _make_mock_sftp()
    client = SftpDeliveryClient(_make_iac(), sftp_factory=lambda: mock_sftp)
    client.open()
    # Inject a mock transport directly so _close_connection() tries to close it
    mock_paramiko_transport = MagicMock()
    mock_paramiko_transport.close.side_effect = RuntimeError("transport close failed")
    client._paramiko_transport = mock_paramiko_transport
    # finalize calls _close_connection() — must suppress the transport close error
    client.finalize()


def test_close_connection_suppresses_sftp_close_error(monkeypatch: Any) -> None:
    """Verify _close_connection() suppresses exceptions from sftp.close()."""
    monkeypatch.setenv("SFTP_KEY", "pem")
    mock_sftp = _make_mock_sftp()
    mock_sftp.close.side_effect = RuntimeError("transport already closed")
    client = SftpDeliveryClient(_make_iac(), sftp_factory=lambda: mock_sftp)
    client.open()
    # Should not raise even though sftp.close() raises
    client.finalize()


def test_close_connection_suppresses_file_close_error(monkeypatch: Any) -> None:
    """Verify _close_connection() suppresses exceptions from remote_file.close()."""
    monkeypatch.setenv("SFTP_KEY", "pem")
    mock_sftp = _make_mock_sftp()
    mock_sftp.open.return_value.close.side_effect = OSError("io error")
    client = SftpDeliveryClient(_make_iac(), sftp_factory=lambda: mock_sftp)
    client.open()
    # Should not raise
    client.finalize()


# ---------------------------------------------------------------------------
# Host key verification
# ---------------------------------------------------------------------------


def test_host_key_mismatch_raises_sftp_error(monkeypatch: Any) -> None:
    """Verify that a mismatched server host key raises SftpClientError."""
    expected_key = paramiko.RSAKey.generate(2048)
    actual_key = paramiko.RSAKey.generate(2048)  # different key
    raw = f"ssh-rsa {expected_key.get_base64()}"
    monkeypatch.setenv("SFTP_KEY", "pem")
    monkeypatch.setenv("HOST_KEY", raw)

    iac = SftpClientIaC.model_validate(
        {
            "host": "h",
            "username": "u",
            "remote_path": "/p",
            "private_key_ref": {"kind": "env", "value": "SFTP_KEY"},
            "host_key_ref": {"kind": "env", "value": "HOST_KEY"},
            "transport": {"timeout_seconds": 10.0, "verify_ssh_host_key": True},
        }
    )

    # Build mock paramiko Transport that returns the wrong key
    mock_transport = MagicMock()
    mock_transport.get_remote_server_key.return_value = actual_key

    with patch("pfp_runtime.publishing.clients.sftp_client.paramiko") as mock_paramiko:
        _patch_paramiko_key_types(mock_paramiko)
        mock_paramiko.Transport.return_value = mock_transport

        client = SftpDeliveryClient(iac)
        with pytest.raises(SftpClientError):
            client.open()


def test_host_key_verify_false_skips_key_check(monkeypatch: Any) -> None:
    """Verify verify_ssh_host_key=False skips get_remote_server_key() in _build_real_sftp."""
    monkeypatch.setenv("SFTP_KEY", "pem")
    iac = _make_iac()  # verify_ssh_host_key=False, no host_key_ref needed

    mock_transport = MagicMock()
    mock_sftp_client = MagicMock()

    with patch("pfp_runtime.publishing.clients.sftp_client.paramiko") as mock_paramiko:
        _patch_paramiko_key_types(mock_paramiko)
        mock_paramiko.Transport.return_value = mock_transport
        mock_paramiko.SFTPClient.from_transport.return_value = mock_sftp_client

        # _load_private_key will fail on "pem" string, bypass by patching it
        with patch(
            "pfp_runtime.publishing.clients.sftp_client._load_private_key",
            return_value=MagicMock(),
        ):
            client = SftpDeliveryClient(iac)
            client.open()

    mock_transport.get_remote_server_key.assert_not_called()


def test_build_real_sftp_applies_ssh_algorithm_overrides(monkeypatch: Any) -> None:
    """Verify _build_real_sftp applies ssh_ciphers/macs/kex/key_types when configured."""
    monkeypatch.setenv("SFTP_KEY", "pem")
    iac = SftpClientIaC.model_validate(
        {
            "host": "h",
            "username": "u",
            "remote_path": "/p",
            "private_key_ref": {"kind": "env", "value": "SFTP_KEY"},
            "transport": {
                "timeout_seconds": 10.0,
                "verify_ssh_host_key": False,
                "ssh_ciphers": ["aes128-ctr"],
                "ssh_macs": ["hmac-sha2-256"],
                "ssh_kex": ["diffie-hellman-group14-sha256"],
                "ssh_key_types": ["ssh-rsa"],
            },
        }
    )

    mock_transport = MagicMock()
    mock_opts = MagicMock()
    mock_transport.get_security_options.return_value = mock_opts
    mock_sftp_client = MagicMock()

    with patch("pfp_runtime.publishing.clients.sftp_client.paramiko") as mock_paramiko:
        _patch_paramiko_key_types(mock_paramiko)
        mock_paramiko.Transport.return_value = mock_transport
        mock_paramiko.SFTPClient.from_transport.return_value = mock_sftp_client

        with patch(
            "pfp_runtime.publishing.clients.sftp_client._load_private_key",
            return_value=MagicMock(),
        ):
            client = SftpDeliveryClient(iac)
            client.open()

    assert mock_opts.ciphers == ["aes128-ctr"]
    assert mock_opts.digests == ["hmac-sha2-256"]
    assert mock_opts.kex == ["diffie-hellman-group14-sha256"]
    assert mock_opts.key_types == ["ssh-rsa"]


def test_build_real_sftp_uses_password_auth(monkeypatch: Any) -> None:
    """Verify _build_real_sftp calls auth_password() when password_ref is configured."""
    monkeypatch.setenv("SFTP_PASS", "s3cr3t")
    iac = SftpClientIaC.model_validate(
        {
            "host": "h",
            "username": "u",
            "remote_path": "/p",
            "password_ref": {"kind": "env", "value": "SFTP_PASS"},
            "transport": {"timeout_seconds": 10.0, "verify_ssh_host_key": False},
        }
    )

    mock_transport = MagicMock()
    mock_opts = MagicMock()
    mock_transport.get_security_options.return_value = mock_opts
    mock_sftp_client = MagicMock()

    with patch("pfp_runtime.publishing.clients.sftp_client.paramiko") as mock_paramiko:
        _patch_paramiko_key_types(mock_paramiko)
        mock_paramiko.Transport.return_value = mock_transport
        mock_paramiko.SFTPClient.from_transport.return_value = mock_sftp_client

        client = SftpDeliveryClient(iac)
        client.open()

    mock_transport.auth_password.assert_called_once_with("u", "s3cr3t")


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


def test_sftp_client_satisfies_protocol(monkeypatch: Any) -> None:
    """Verify SftpDeliveryClient is recognised as DeliveryClient."""
    monkeypatch.setenv("SFTP_KEY", "pem")
    client = SftpDeliveryClient(_make_iac(), sftp_factory=lambda: _make_mock_sftp())
    assert isinstance(client, DeliveryClient)


# ---------------------------------------------------------------------------
# Full cycle
# ---------------------------------------------------------------------------


def test_full_cycle_all_chunks_written_in_order(monkeypatch: Any) -> None:
    """Verify open → 3× send_chunk → finalize calls write() for each chunk in order."""
    monkeypatch.setenv("SFTP_KEY", "pem")
    mock_sftp = _make_mock_sftp()
    iac = _make_iac()
    client = SftpDeliveryClient(iac, sftp_factory=lambda: mock_sftp)
    client.open()
    client.send_chunk(b"part1")
    client.send_chunk(b"part2")
    client.send_chunk(b"part3")
    result = client.finalize()
    remote_file = mock_sftp.open.return_value
    calls = [c.args[0] for c in remote_file.write.call_args_list]
    assert calls == [b"part1", b"part2", b"part3"]
    assert result.status_code == 0


# ---------------------------------------------------------------------------
# _load_private_key
# ---------------------------------------------------------------------------


def test_load_private_key_rsa() -> None:
    """Verify RSA private key is parsed correctly."""
    import io

    key = paramiko.RSAKey.generate(2048)
    buf = io.StringIO()
    key.write_private_key(buf)
    pem = buf.getvalue()
    loaded = _load_private_key(pem)
    assert loaded.get_name() == "ssh-rsa"


def test_load_private_key_ecdsa() -> None:
    """Verify ECDSA private key is parsed correctly."""
    import io

    key = paramiko.ECDSAKey.generate()
    buf = io.StringIO()
    key.write_private_key(buf)
    pem = buf.getvalue()
    loaded = _load_private_key(pem)
    assert loaded.get_name() == "ecdsa-sha2-nistp256"


def test_load_private_key_malformed_raises() -> None:
    """Verify malformed PEM raises SftpClientError."""
    with pytest.raises(SftpClientError, match="Unsupported or malformed"):
        _load_private_key("not a real key")


# ---------------------------------------------------------------------------
# _parse_host_key
# ---------------------------------------------------------------------------


def test_parse_host_key_rsa_matches_original() -> None:
    """Verify RSA public key parses and matches the original key."""
    key = paramiko.RSAKey.generate(2048)
    raw = f"ssh-rsa {key.get_base64()}"
    parsed = _parse_host_key(raw)
    assert parsed == key


def test_parse_host_key_rsa() -> None:
    """Verify RSA public key parses successfully."""
    key = paramiko.RSAKey.generate(2048)
    raw = f"ssh-rsa {key.get_base64()}"
    parsed = _parse_host_key(raw)
    assert parsed.get_name() == "ssh-rsa"


def test_parse_host_key_no_space_raises() -> None:
    """Verify missing space in host key format raises SftpClientError."""
    with pytest.raises(SftpClientError, match="Invalid host_key_ref format"):
        _parse_host_key("ssh-ed25519AAAAC3")


def test_parse_host_key_unsupported_type_raises() -> None:
    """Verify unsupported key type raises SftpClientError."""
    with pytest.raises(SftpClientError, match="Unsupported host key type"):
        _parse_host_key("ssh-unknown AAAA")


def test_parse_host_key_invalid_base64_raises() -> None:
    """Verify invalid base64 data raises SftpClientError."""
    with pytest.raises(SftpClientError, match="Failed to parse host key"):
        _parse_host_key("ssh-ed25519 !!!not-valid-base64!!!")
