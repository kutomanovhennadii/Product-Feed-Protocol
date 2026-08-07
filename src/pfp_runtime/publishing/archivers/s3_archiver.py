"""S3 archiver for archive_type: s3.

Implements the Archiver protocol by streaming artifact chunks to AWS S3
using multipart upload. Each call to open() generates a unique S3 object key:
{key_prefix}{filename_base}_{YYYYMMDD_HHMMSS} (UTC).

Multipart upload strategy
--------------------------
AWS requires each part (except the last) to be at least 5 MiB. Chunks from
write_chunk() are accumulated in an in-memory buffer. When the buffer reaches
_MIN_PART_SIZE the buffered data is uploaded as one S3 part. finalize() uploads
whatever remains in the buffer as the final part (which may be smaller than
_MIN_PART_SIZE), then calls complete_multipart_upload().

On any failure during upload_part() or complete_multipart_upload(),
abort_multipart_upload() is called as a best-effort cleanup so orphaned parts
do not accumulate in S3.

Credentials
-----------
Credentials are not part of the IaC schema. The AWS SDK resolves them via the
standard credential chain: environment variables → ~/.aws/credentials → IAM role.
"""

from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import boto3
from pydantic import BaseModel, ConfigDict, Field

from pfp_runtime.publishing.archivers.archiver_contract import ArchiveResult
from pfp_runtime.publishing.support.transport_policy import (
    TlsTransportPolicy,
    classify_transport_error,
    execute_with_retry,
    format_transport_runtime_error,
)

_MIN_PART_SIZE: int = 5 * 1024 * 1024  # 5 MiB — AWS minimum part size (except last)


class S3ArchiverError(RuntimeError):
    """Raised when S3Archiver encounters a configuration or upload error."""


class S3ArchiverIaC(BaseModel):
    """IaC model for the AWS S3 archiver.

    Attributes:
        bucket: S3 bucket name.
        filename_base: Base name for the output object. A UTC timestamp suffix
            is appended automatically: {filename_base}_{YYYYMMDD_HHMMSS}.
            Do not include a file extension.
        key_prefix: Optional object key prefix. Final key:
            {key_prefix}{filename_base}_{YYYYMMDD_HHMMSS}.
        region: Optional AWS region. If omitted, boto3 uses the environment
            or ~/.aws/config.
        transport: TLS transport policy. All sub-fields have defaults —
            the entire block is optional in YAML.
    """

    model_config = ConfigDict(extra="forbid")

    bucket: str
    filename_base: str
    key_prefix: str = ""
    region: Optional[str] = None
    transport: TlsTransportPolicy = Field(default_factory=TlsTransportPolicy)


class S3Archiver:
    """Archiver that streams artifact chunks to AWS S3 via multipart upload.

    Satisfies the Archiver protocol structurally. Instantiated by archiver_builder
    when archive_type is 's3', using the standard 5-step build path.

    Args:
        iac: Validated S3ArchiverIaC instance.
    """

    def __init__(self, iac: S3ArchiverIaC) -> None:
        """Resolve configuration and create boto3 client.

        No network calls are made here. The boto3 client is created once and
        reused across open/write_chunk/finalize cycles.

        Args:
            iac: Validated S3ArchiverIaC instance.
        """
        self._iac = iac
        self._transport: TlsTransportPolicy = iac.transport
        kwargs: Dict[str, Any] = {"verify": self._transport.verify_tls}
        if iac.region:
            kwargs["region_name"] = iac.region
        self._s3 = boto3.client("s3", **kwargs)
        # runtime state — populated by open()
        self._object_key: Optional[str] = None
        self._upload_id: Optional[str] = None
        self._parts: List[Dict[str, Any]] = []
        self._buffer: Optional[io.BytesIO] = None
        self._part_number: int = 0
        self._finalized: bool = False

    def open(self) -> None:
        """Generate a timestamp-based S3 key and initiate a multipart upload.

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
            classify_error=lambda exc: classify_transport_error(exc, transport="s3"),
        )
        self._upload_id = response["UploadId"]

    def write_chunk(self, chunk: bytes) -> None:
        """Buffer one chunk and upload it as an S3 part when the buffer is full.

        Args:
            chunk: Payload bytes to append to the archive.

        Raises:
            S3ArchiverError: If open() has not been called or finalize() has
                already been called.
        """
        if self._buffer is None:
            raise S3ArchiverError("write_chunk() called before open()")
        if self._finalized:
            raise S3ArchiverError("write_chunk() called after finalize()")
        self._buffer.write(chunk)
        if self._buffer.tell() >= _MIN_PART_SIZE:
            data = self._buffer.getvalue()
            self._buffer = io.BytesIO()
            try:
                self._upload_part(data)
            except Exception as exc:
                self._abort_upload()
                raise S3ArchiverError(
                    "S3 upload_part failed; upload aborted: "
                    + format_transport_runtime_error(
                        prefix="s3_archiver",
                        category=classify_transport_error(exc, transport="s3"),
                        exc=exc,
                    )
                ) from exc

    def finalize(self) -> ArchiveResult:
        """Upload the remaining buffer, complete the multipart upload, and return result.

        Returns:
            ArchiveResult with skipped=False and location set to
            s3://{bucket}/{object_key}.

        Raises:
            S3ArchiverError: If open() has not been called, finalize() has
                already been called, or the multipart upload fails. On upload
                failure, abort_multipart_upload() is called as best-effort cleanup.
        """
        if self._buffer is None:
            raise S3ArchiverError("finalize() called before open()")
        if self._finalized:
            raise S3ArchiverError(
                "finalize() already called; call open() to start a new run"
            )

        remaining = self._buffer.getvalue()
        self._buffer = io.BytesIO()
        if remaining:
            try:
                self._upload_part(remaining)  # last part — may be < _MIN_PART_SIZE
            except Exception as exc:
                self._abort_upload()
                raise S3ArchiverError(
                    "S3 upload_part failed; upload aborted: "
                    + format_transport_runtime_error(
                        prefix="s3_archiver",
                        category=classify_transport_error(exc, transport="s3"),
                        exc=exc,
                    )
                ) from exc

        if not self._parts:
            # No data was written at all. AWS requires at least one part in a
            # multipart upload — abort it and fall back to put_object with an
            # empty body so the caller gets a valid (zero-byte) S3 object.
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
                        exc, transport="s3"
                    ),
                )
            except Exception as exc:
                raise S3ArchiverError(
                    "S3 put_object failed for empty archive: "
                    + format_transport_runtime_error(
                        prefix="s3_archiver",
                        category=classify_transport_error(exc, transport="s3"),
                        exc=exc,
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
                        exc, transport="s3"
                    ),
                )
            except Exception as exc:
                self._abort_upload()
                raise S3ArchiverError(
                    "S3 multipart upload failed; upload aborted: "
                    + format_transport_runtime_error(
                        prefix="s3_archiver",
                        category=classify_transport_error(exc, transport="s3"),
                        exc=exc,
                    )
                ) from exc

        self._finalized = True
        location = "s3://{}/{}".format(self._iac.bucket, self._object_key)
        return ArchiveResult(skipped=False, location=location)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _upload_part(self, data: bytes) -> None:
        """Upload one part to S3 without any size check.

        Args:
            data: Raw bytes to upload as one S3 multipart part.
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
            classify_error=lambda exc: classify_transport_error(exc, transport="s3"),
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


__all__: List[str] = ["S3ArchiverIaC", "S3Archiver", "S3ArchiverError"]
