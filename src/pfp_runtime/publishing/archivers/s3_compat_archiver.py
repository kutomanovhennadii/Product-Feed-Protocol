"""S3-compatible archiver for archive_type: s3_compat.

Implements the Archiver protocol for S3-compatible object stores: MinIO,
Cloudflare R2, Backblaze B2, and any other boto3-compatible endpoint.

Differs from S3Archiver in two ways:
  - endpoint_url is required (passed as boto3 client parameter).
  - Credentials are always explicit: access_key_ref and secret_key_ref
    are SecretRef values resolved in __init__ (Fail-Fast).

The multipart upload strategy and streaming cycle are identical to S3Archiver,
including abort-on-failure for both upload_part and complete_multipart_upload.
See s3_archiver.py for the shared design rationale.
"""

from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import boto3
from pydantic import BaseModel, ConfigDict, Field

from pfp_runtime.publishing.archivers.archiver_contract import ArchiveResult
from pfp_runtime.publishing.support.secret_resolver import (
    SecretResolutionError,
    resolve_secret_ref,
)
from pfp_runtime.publishing.support.transport_policy import (
    TlsTransportPolicy,
    classify_transport_error,
    execute_with_retry,
    format_transport_runtime_error,
)
from pfp_utils.security import SecretRef

_MIN_PART_SIZE: int = 5 * 1024 * 1024  # 5 MiB — AWS minimum part size (except last)


class S3CompatArchiverError(RuntimeError):
    """Raised when S3CompatArchiver encounters a configuration or upload error."""


class S3CompatArchiverIaC(BaseModel):
    """IaC model for the S3-compatible archiver.

    Attributes:
        endpoint: Storage endpoint URL (e.g. https://my-minio.internal:9000).
        bucket: Bucket name.
        filename_base: Base name for the output object. A UTC timestamp suffix
            is appended automatically: {filename_base}_{YYYYMMDD_HHMMSS}.
            Do not include a file extension.
        key_prefix: Optional object key prefix. Final key:
            {key_prefix}{filename_base}_{YYYYMMDD_HHMMSS}.
        access_key_ref: SecretRef for the storage access key.
        secret_key_ref: SecretRef for the storage secret key.
        transport: TLS transport policy. All sub-fields have defaults —
            the entire block is optional in YAML.
    """

    model_config = ConfigDict(extra="forbid")

    endpoint: str
    bucket: str
    filename_base: str
    key_prefix: str = ""
    access_key_ref: SecretRef
    secret_key_ref: SecretRef
    transport: TlsTransportPolicy = Field(default_factory=TlsTransportPolicy)


class S3CompatArchiver:
    """Archiver that streams artifact chunks to an S3-compatible object store.

    Satisfies the Archiver protocol structurally. Instantiated by archiver_builder
    when archive_type is 's3_compat', using the standard 5-step build path.

    Args:
        iac: Validated S3CompatArchiverIaC instance.

    Raises:
        S3CompatArchiverError: If credentials cannot be resolved.
    """

    def __init__(self, iac: S3CompatArchiverIaC) -> None:
        """Resolve credentials and create boto3 client.

        Credentials are resolved here (Fail-Fast). No S3 network calls are made.

        Args:
            iac: Validated S3CompatArchiverIaC instance.

        Raises:
            S3CompatArchiverError: If access_key_ref or secret_key_ref cannot
                be resolved.
        """
        self._iac = iac
        self._transport: TlsTransportPolicy = iac.transport

        try:
            self._access_key: str = resolve_secret_ref(iac.access_key_ref)
            self._secret_key: str = resolve_secret_ref(iac.secret_key_ref)
        except SecretResolutionError as exc:
            raise S3CompatArchiverError(
                "Failed to resolve S3Compat credentials: " + str(exc)
            ) from exc

        self._s3 = boto3.client(
            "s3",
            endpoint_url=iac.endpoint,
            aws_access_key_id=self._access_key,
            aws_secret_access_key=self._secret_key,
            verify=self._transport.verify_tls,
        )
        # runtime state — populated by open()
        self._object_key: Optional[str] = None
        self._upload_id: Optional[str] = None
        self._parts: List[Dict[str, Any]] = []
        self._buffer: Optional[io.BytesIO] = None
        self._part_number: int = 0
        self._finalized: bool = False

    def open(self) -> None:
        """Generate a timestamp-based object key and initiate a multipart upload.

        The object key is {key_prefix}{filename_base}_{YYYYMMDD_HHMMSS} (UTC).
        If a previous multipart upload was left open (open() called again before
        finalize()), it is aborted as best-effort before starting a new one.
        """
        if self._upload_id is not None and not self._finalized:
            self._abort_upload()

        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self._object_key = "{}{}_{}".format(
            self._iac.key_prefix, self._iac.filename_base, ts
        )
        self._finalized = False
        self._parts = []
        self._part_number = 0
        self._buffer = io.BytesIO()

        response = execute_with_retry(
            lambda: self._s3.create_multipart_upload(
                Bucket=self._iac.bucket, Key=self._object_key
            ),
            policy=self._transport,
            classify_error=lambda exc: classify_transport_error(
                exc, transport="s3_compat"
            ),
        )
        self._upload_id = response["UploadId"]

    def write_chunk(self, chunk: bytes) -> None:
        """Buffer one chunk and upload it as a part when the buffer is full.

        Args:
            chunk: Payload bytes to append to the archive.

        Raises:
            S3CompatArchiverError: If open() has not been called or finalize()
                has already been called.
        """
        if self._buffer is None:
            raise S3CompatArchiverError("write_chunk() called before open()")
        if self._finalized:
            raise S3CompatArchiverError("write_chunk() called after finalize()")
        self._buffer.write(chunk)
        if self._buffer.tell() >= _MIN_PART_SIZE:
            data = self._buffer.getvalue()
            self._buffer = io.BytesIO()
            try:
                self._upload_part(data)
            except Exception as exc:
                self._abort_upload()
                raise S3CompatArchiverError(
                    "S3Compat upload_part failed; upload aborted: "
                    + format_transport_runtime_error(
                        prefix="s3_compat_archiver",
                        category=classify_transport_error(exc, transport="s3_compat"),
                        exc=exc,
                        secret_values=[self._access_key, self._secret_key],
                    )
                ) from exc

    def finalize(self) -> ArchiveResult:
        """Upload the remaining buffer, complete the multipart upload, and return result.

        Returns:
            ArchiveResult with skipped=False and location set to
            s3://{bucket}/{object_key}.

        Raises:
            S3CompatArchiverError: If open() has not been called, finalize() has
                already been called, or the multipart upload fails.
        """
        if self._buffer is None:
            raise S3CompatArchiverError("finalize() called before open()")
        if self._finalized:
            raise S3CompatArchiverError(
                "finalize() already called; call open() to start a new run"
            )

        remaining = self._buffer.getvalue()
        self._buffer = io.BytesIO()
        if remaining:
            try:
                self._upload_part(remaining)  # last part — may be < _MIN_PART_SIZE
            except Exception as exc:
                self._abort_upload()
                raise S3CompatArchiverError(
                    "S3Compat upload_part failed; upload aborted: "
                    + format_transport_runtime_error(
                        prefix="s3_compat_archiver",
                        category=classify_transport_error(exc, transport="s3_compat"),
                        exc=exc,
                        secret_values=[self._access_key, self._secret_key],
                    )
                ) from exc

        if not self._parts:
            # No data was written at all. AWS requires at least one part in a
            # multipart upload — abort it and fall back to put_object with an
            # empty body so the caller gets a valid (zero-byte) object.
            self._abort_upload()
            try:
                execute_with_retry(
                    lambda: self._s3.put_object(
                        Bucket=self._iac.bucket,
                        Key=self._object_key,
                        Body=b"",
                    ),
                    policy=self._transport,
                    classify_error=lambda exc: classify_transport_error(
                        exc, transport="s3_compat"
                    ),
                )
            except Exception as exc:
                raise S3CompatArchiverError(
                    "S3Compat put_object failed for empty archive: "
                    + format_transport_runtime_error(
                        prefix="s3_compat_archiver",
                        category=classify_transport_error(exc, transport="s3_compat"),
                        exc=exc,
                        secret_values=[self._access_key, self._secret_key],
                    )
                ) from exc
        else:
            try:
                execute_with_retry(
                    lambda: self._s3.complete_multipart_upload(
                        Bucket=self._iac.bucket,
                        Key=self._object_key,
                        UploadId=self._upload_id,
                        MultipartUpload={"Parts": self._parts},
                    ),
                    policy=self._transport,
                    classify_error=lambda exc: classify_transport_error(
                        exc, transport="s3_compat"
                    ),
                )
            except Exception as exc:
                self._abort_upload()
                raise S3CompatArchiverError(
                    "S3Compat multipart upload failed; upload aborted: "
                    + format_transport_runtime_error(
                        prefix="s3_compat_archiver",
                        category=classify_transport_error(exc, transport="s3_compat"),
                        exc=exc,
                        secret_values=[self._access_key, self._secret_key],
                    )
                ) from exc

        self._finalized = True
        location = "s3://{}/{}".format(self._iac.bucket, self._object_key)
        return ArchiveResult(skipped=False, location=location)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _upload_part(self, data: bytes) -> None:
        """Upload one part to the S3-compatible store without any size check.

        Args:
            data: Raw bytes to upload as one multipart part.
        """
        self._part_number += 1
        part_num = self._part_number  # capture for lambda closure
        response = execute_with_retry(
            lambda: self._s3.upload_part(
                Bucket=self._iac.bucket,
                Key=self._object_key,
                UploadId=self._upload_id,
                PartNumber=part_num,
                Body=data,
            ),
            policy=self._transport,
            classify_error=lambda exc: classify_transport_error(
                exc, transport="s3_compat"
            ),
        )
        self._parts.append({"PartNumber": part_num, "ETag": response["ETag"]})

    def _abort_upload(self) -> None:
        """Best-effort multipart upload abort.

        Suppresses all errors so the original exception is not masked.
        """
        try:
            if self._upload_id is not None:
                self._s3.abort_multipart_upload(
                    Bucket=self._iac.bucket,
                    Key=self._object_key,
                    UploadId=self._upload_id,
                )
        except Exception:  # noqa: BLE001  # nosec B110
            pass


__all__: List[str] = [
    "S3CompatArchiverIaC",
    "S3CompatArchiver",
    "S3CompatArchiverError",
]
