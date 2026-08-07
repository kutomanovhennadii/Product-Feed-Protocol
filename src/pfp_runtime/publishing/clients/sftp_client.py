"""SFTP delivery client for client_type: sftp.

Paramiko-based SFTP client with injectable sftp_factory for testing.
Streams artifact chunks directly to a remote file over an SSH connection.

Host key verification is performed when transport.verify_ssh_host_key=True
(the default). The expected host key is resolved from host_key_ref in __init__
and compared against the actual server key after start_client() in every
connection attempt.
"""

from __future__ import annotations

import base64
import io as _io
import uuid
from typing import Any, Callable, Dict, List, Optional

try:
    import paramiko
    import paramiko.message as paramiko_message
except ImportError as _err:  # pragma: no cover
    raise ImportError(
        "paramiko is required for SFTP delivery. "
        "Install it with: pip install pfp-core[sftp]"
    ) from _err

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pfp_runtime.publishing.clients.client_contract import DeliveryResult
from pfp_runtime.publishing.support.secret_resolver import (
    SecretResolutionError,
    resolve_secret_ref,
)
from pfp_runtime.publishing.support.transport_policy import (
    SftpTransportPolicy,
    classify_transport_error,
    execute_with_retry,
    format_transport_runtime_error,
    mark_transport_error,
)
from pfp_utils.security import SecretRef

SftpFactory = Callable[[], Any]  # () -> paramiko.SFTPClient


class SftpClientError(RuntimeError):
    """Raised when SftpDeliveryClient encounters a configuration or transport error."""


class SftpClientIaC(BaseModel):
    """IaC model for the SFTP delivery client.

    Attributes:
        host: SFTP server hostname or IP address.
        port: SSH/SFTP port. Default: 22.
        username: Username on the SFTP server.
        remote_path: Full path to the destination file on the server,
            including filename. Example: /feeds/product_feed.jsonl.gz.
        password_ref: Optional SecretRef for password-based authentication.
            Mutually exclusive with private_key_ref.
        private_key_ref: Optional SecretRef for key-based authentication.
            Mutually exclusive with password_ref.
        host_key_ref: Optional SecretRef containing the server's public key in
            OpenSSH format ('<key-type> <base64>'). Required when
            transport.verify_ssh_host_key=True (the default).
        transport: SFTP transport policy. All sub-fields have defaults —
            the entire block is optional in YAML.
    """

    model_config = ConfigDict(extra="forbid")

    host: str
    port: int = 22
    username: str
    remote_path: str
    password_ref: Optional[SecretRef] = None
    private_key_ref: Optional[SecretRef] = None
    host_key_ref: Optional[SecretRef] = None
    atomic_write: bool = True
    transport: SftpTransportPolicy = Field(default_factory=SftpTransportPolicy)

    @model_validator(mode="after")
    def _validate_auth(self) -> "SftpClientIaC":
        has_password = self.password_ref is not None
        has_key = self.private_key_ref is not None
        if not has_password and not has_key:
            raise ValueError(
                "Exactly one of password_ref or private_key_ref is required"
            )
        if has_password and has_key:
            raise ValueError(
                "Specify exactly one of password_ref or private_key_ref, not both"
            )
        if self.transport.verify_ssh_host_key and self.host_key_ref is None:
            raise ValueError(
                "host_key_ref is required when transport.verify_ssh_host_key=True"
            )
        return self


class SftpDeliveryClient:
    """Delivery client that streams artifact chunks over SFTP using paramiko.

    Satisfies the DeliveryClient protocol structurally. Instantiated by
    client_builder when client_type is 'sftp', using the standard 5-step
    build path.

    The entire TCP + SSH handshake + host key check + authentication sequence
    is wrapped in execute_with_retry in open(), making the whole connection
    attempt atomic and retryable on transient failures.

    Args:
        iac: Validated SftpClientIaC instance.
        sftp_factory: Optional callable returning a paramiko.SFTPClient for
            testing. When provided, open() calls sftp_factory() instead of
            building a real paramiko connection.
    """

    def __init__(
        self,
        iac: SftpClientIaC,
        *,
        sftp_factory: Optional[SftpFactory] = None,
    ) -> None:
        """Resolve credentials and parse host key in Fail-Fast mode.

        Args:
            iac: Validated SftpClientIaC instance.
            sftp_factory: Optional () -> SFTPClient for injecting test doubles.

        Raises:
            SftpClientError: If credential or host key secrets cannot be
                resolved, or if the host key string is malformed.
        """
        self._iac = iac
        self._sftp_factory = sftp_factory

        # Resolve credentials Fail-Fast
        try:
            if iac.password_ref is not None:
                self._password: Optional[str] = resolve_secret_ref(iac.password_ref)
                self._private_key_pem: Optional[str] = None
            else:
                self._password = None
                self._private_key_pem = resolve_secret_ref(
                    iac.private_key_ref  # type: ignore[arg-type]
                )
        except SecretResolutionError as exc:
            raise SftpClientError(f"Failed to resolve SFTP credential: {exc}") from exc

        # Parse host key Fail-Fast if verification is enabled
        self._expected_host_key: Optional[Any] = None
        if iac.transport.verify_ssh_host_key:
            try:
                raw = resolve_secret_ref(iac.host_key_ref)  # type: ignore[arg-type]
            except SecretResolutionError as exc:
                raise SftpClientError(f"Failed to resolve host_key_ref: {exc}") from exc
            self._expected_host_key = _parse_host_key(raw)

        # Runtime state
        self._sftp: Any = None
        self._paramiko_transport: Any = None
        self._remote_file: Any = None
        self._tmp_path: Optional[str] = None  # set in open() when atomic_write=True
        self._finalized: bool = False

    def open(self) -> None:
        """Establish SFTP connection and open the remote file for writing.

        If a previous cycle's connection is still open, closes it first
        (best-effort). On transient errors the whole TCP+auth sequence is
        retried up to transport.max_retries times.

        Raises:
            SftpClientError: On unrecoverable connection or configuration error.
        """
        if self._sftp is not None and not self._finalized:
            self._close_connection()

        self._finalized = False

        secret_values: List[str] = [
            s for s in [self._password, self._private_key_pem] if s is not None
        ]
        try:
            if self._sftp_factory is not None:
                self._sftp = self._sftp_factory()
            else:
                self._sftp = execute_with_retry(
                    self._build_real_sftp,
                    policy=self._iac.transport,
                    classify_error=lambda exc: classify_transport_error(
                        exc, transport="sftp"
                    ),
                )
            if self._iac.atomic_write:
                self._tmp_path = f"{self._iac.remote_path}.{uuid.uuid4().hex}.tmp"
                open_path = self._tmp_path
            else:
                self._tmp_path = None
                open_path = self._iac.remote_path
            self._remote_file = self._sftp.open(open_path, "wb")
            self._remote_file.set_pipelined(True)
        except SftpClientError:
            raise
        except Exception as exc:
            category = classify_transport_error(exc, transport="sftp")
            msg = format_transport_runtime_error(
                prefix="sftp_client",
                category=category,
                exc=exc,
                secret_values=secret_values,
            )
            raise SftpClientError(msg) from exc

    def send_chunk(self, chunk: bytes) -> None:
        """Write chunk to the remote file.

        Args:
            chunk: Payload bytes to write.

        Raises:
            SftpClientError: If called before open() or after finalize().
        """
        if self._finalized:
            raise SftpClientError("send_chunk() called after finalize()")
        if self._remote_file is None:
            raise SftpClientError("send_chunk() called before open()")
        self._remote_file.write(chunk)

    def finalize(self) -> DeliveryResult:
        """Close the remote file, optionally rename to final path, close connection.

        When atomic_write=True (default), the temp file is renamed to remote_path
        only after all data has been flushed — the destination never contains a
        partial file. On rename failure the temp file is removed best-effort and
        SftpClientError is raised.

        Returns:
            DeliveryResult with skipped=False and status_code=0 (SFTP_OK).

        Raises:
            SftpClientError: If called before open(), called twice without an
                intervening open(), or if the atomic rename fails.
        """
        if self._finalized:
            raise SftpClientError(
                "finalize() already called; call open() to start a new run"
            )
        if self._remote_file is None:
            raise SftpClientError("finalize() called before open()")

        # Step 1: flush and close the remote file
        try:
            self._remote_file.close()
        except Exception:  # nosec B110
            pass
        self._remote_file = None

        # Step 2: atomic rename — sftp session still open at this point
        if self._iac.atomic_write and self._tmp_path is not None:
            try:
                self._sftp.rename(self._tmp_path, self._iac.remote_path)
                self._tmp_path = None
            except Exception as exc:
                # Rename failed: remove temp file best-effort, then propagate
                try:
                    if self._sftp is not None:
                        self._sftp.remove(self._tmp_path)
                except Exception:  # nosec B110
                    pass
                self._tmp_path = None
                self._close_connection()
                raise SftpClientError(
                    f"sftp_client: atomic rename failed: {exc}"
                ) from exc

        # Step 3: close sftp + transport
        self._close_connection()
        self._finalized = True
        return DeliveryResult(skipped=False, status_code=0)

    def _build_real_sftp(self) -> Any:
        """Build real paramiko SFTP connection (TCP + handshake + host key + auth).

        Called (possibly with retry) from open(). The entire operation is
        atomic — any failure causes the Transport to be closed before raising,
        so no half-open connection is leaked.

        Returns:
            Connected paramiko.SFTPClient.

        Raises:
            BaseException: Marked with transport category for classify_error.
        """
        tp = self._iac.transport
        t = paramiko.Transport((self._iac.host, self._iac.port))
        t.set_keepalive(60)

        # Apply per-category SSH algorithm overrides (None = paramiko defaults)
        opts = t.get_security_options()
        if tp.ssh_ciphers is not None:
            opts.ciphers = tp.ssh_ciphers
        if tp.ssh_macs is not None:
            opts.digests = tp.ssh_macs
        if tp.ssh_kex is not None:
            opts.kex = tp.ssh_kex
        if tp.ssh_key_types is not None:
            opts.key_types = tp.ssh_key_types

        t.start_client(timeout=tp.timeout_seconds)

        # Host key verification
        if tp.verify_ssh_host_key:
            actual_key = t.get_remote_server_key()
            if actual_key != self._expected_host_key:
                t.close()
                raise mark_transport_error(
                    category="ssh_host_key_failure",
                    message=(
                        f"Host key mismatch for {self._iac.host}: "
                        f"got {actual_key.get_name()} "
                        f"but expected {self._expected_host_key.get_name()}"  # type: ignore[union-attr]
                    ),
                )

        # Authentication
        if self._password is not None:
            t.auth_password(self._iac.username, self._password)
        else:
            pkey = _load_private_key(self._private_key_pem)  # type: ignore[arg-type]
            t.auth_publickey(self._iac.username, pkey)

        self._paramiko_transport = t
        return paramiko.SFTPClient.from_transport(t)

    def _close_connection(self) -> None:
        """Close remote file, SFTP client, and paramiko transport. Best-effort.

        If _tmp_path is still set (rename never completed due to an error),
        removes the temp file before closing the SFTP session.
        """
        try:
            if self._remote_file is not None:
                self._remote_file.close()
        except Exception:  # nosec B110
            pass
        self._remote_file = None
        # Remove temp file if atomic rename did not complete (error path)
        if self._tmp_path is not None and self._sftp is not None:
            try:
                self._sftp.remove(self._tmp_path)
            except Exception:  # nosec B110
                pass
            self._tmp_path = None
        try:
            if self._sftp is not None:
                self._sftp.close()
        except Exception:  # nosec B110
            pass
        try:
            if self._paramiko_transport is not None:
                self._paramiko_transport.close()
        except Exception:  # nosec B110
            pass
        self._sftp = None
        self._paramiko_transport = None


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _parse_host_key(raw_str: str) -> Any:
    """Parse '<key-type> <base64>' string into a paramiko PKey.

    Called from SftpDeliveryClient.__init__ when verify_ssh_host_key=True.
    The result is stored as _expected_host_key and compared against the
    actual server key obtained from t.get_remote_server_key() after
    start_client().

    Args:
        raw_str: Public key in OpenSSH format, e.g. 'ssh-ed25519 AAAAC3...'.

    Returns:
        Parsed paramiko PKey ready for equality comparison.

    Raises:
        SftpClientError: If the format is invalid, the key type is unsupported,
            or the base64 data cannot be decoded/parsed.
    """
    parts = raw_str.strip().split(None, 1)
    if len(parts) != 2:
        raise SftpClientError(
            "Invalid host_key_ref format: expected '<key-type> <base64>'"
        )
    key_type, key_b64 = parts

    key_type_map: Dict[str, Any] = {
        "ssh-rsa": paramiko.RSAKey,
        "ssh-ed25519": paramiko.Ed25519Key,
        "ecdsa-sha2-nistp256": paramiko.ECDSAKey,
        "ecdsa-sha2-nistp384": paramiko.ECDSAKey,
        "ecdsa-sha2-nistp521": paramiko.ECDSAKey,
    }
    dss_key_class = getattr(paramiko, "DSSKey", None)
    if dss_key_class is not None:
        key_type_map["ssh-dss"] = dss_key_class
    key_class = key_type_map.get(key_type)
    if key_class is None:
        raise SftpClientError(f"Unsupported host key type: {key_type!r}")

    try:
        key_bytes = base64.b64decode(key_b64)
        msg = paramiko_message.Message(key_bytes)
        return key_class(msg=msg)
    except Exception as exc:
        raise SftpClientError(f"Failed to parse host key: {exc}") from exc


def _load_private_key(pem: str) -> Any:
    """Detect and load any paramiko-supported private key type from PEM string.

    Args:
        pem: PEM-encoded private key string.

    Returns:
        Loaded paramiko PKey.

    Raises:
        SftpClientError: If the key is malformed or of an unsupported type.
    """
    key_classes: List[Any] = [
        paramiko.RSAKey,
        paramiko.ECDSAKey,
        paramiko.Ed25519Key,
    ]
    dss_key_class = getattr(paramiko, "DSSKey", None)
    if dss_key_class is not None:
        key_classes.append(dss_key_class)

    for key_class in key_classes:
        try:
            return key_class.from_private_key(_io.StringIO(pem))  # type: ignore[arg-type]
        except paramiko.SSHException:
            continue
    raise SftpClientError("Unsupported or malformed private key")


__all__: List[str] = [
    "SftpClientIaC",
    "SftpDeliveryClient",
    "SftpClientError",
]
