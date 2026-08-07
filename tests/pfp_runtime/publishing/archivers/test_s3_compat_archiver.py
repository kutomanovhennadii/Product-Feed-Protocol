"""Tests for publishing/archivers/s3_compat_archiver.py."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import boto3
import pytest
from moto import mock_aws
from pydantic import ValidationError

from pfp_runtime.publishing.archivers.archiver_contract import Archiver, ArchiveResult
from pfp_runtime.publishing.archivers.s3_compat_archiver import (
    S3CompatArchiver,
    S3CompatArchiverError,
    S3CompatArchiverIaC,
)

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

_BUCKET = "test-bucket"
_ENDPOINT = "https://minio.example.com"
_ACCESS_KEY_ENV = "MINIO_ACCESS_KEY"
_SECRET_KEY_ENV = "MINIO_SECRET_KEY"
_ACCESS_KEY_VAL = "minioaccess"
_SECRET_KEY_VAL = "miniosecret"


def _make_iac(**kwargs) -> S3CompatArchiverIaC:  # type: ignore[return]
    defaults = {
        "endpoint": _ENDPOINT,
        "bucket": _BUCKET,
        "filename_base": "product_feed",
        "access_key_ref": {"kind": "env", "value": _ACCESS_KEY_ENV},
        "secret_key_ref": {"kind": "env", "value": _SECRET_KEY_ENV},
    }
    defaults.update(kwargs)
    return S3CompatArchiverIaC.model_validate(defaults)


@pytest.fixture()
def compat_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set credentials in environment for SecretRef resolution."""
    monkeypatch.setenv(_ACCESS_KEY_ENV, _ACCESS_KEY_VAL)
    monkeypatch.setenv(_SECRET_KEY_ENV, _SECRET_KEY_VAL)
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")


@pytest.fixture()
def s3_compat_bucket(compat_credentials: None):  # type: ignore[return]
    """Provide a mocked S3-compatible bucket for each test.

    moto does not intercept custom endpoint_url (DNS resolves before botocore's
    HTTP layer where moto patches). We instead patch boto3.client inside the
    archiver module so the archiver uses a standard moto-interceptable client.
    """
    with mock_aws():
        std_client = boto3.client("s3", region_name="us-east-1")
        std_client.create_bucket(Bucket=_BUCKET)
        with patch(
            "pfp_runtime.publishing.archivers.s3_compat_archiver.boto3"
        ) as mock_boto3:
            mock_boto3.client.return_value = std_client
            yield std_client


# ---------------------------------------------------------------------------
# S3CompatArchiverIaC validation
# ---------------------------------------------------------------------------


def test_iac_endpoint_required() -> None:
    """Missing endpoint raises ValidationError."""
    with pytest.raises(ValidationError):
        S3CompatArchiverIaC.model_validate(
            {
                "bucket": _BUCKET,
                "filename_base": "feed",
                "access_key_ref": {"kind": "env", "value": "K"},
                "secret_key_ref": {"kind": "env", "value": "S"},
            }
        )


def test_iac_bucket_required() -> None:
    """Missing bucket raises ValidationError."""
    with pytest.raises(ValidationError):
        S3CompatArchiverIaC.model_validate(
            {
                "endpoint": _ENDPOINT,
                "filename_base": "feed",
                "access_key_ref": {"kind": "env", "value": "K"},
                "secret_key_ref": {"kind": "env", "value": "S"},
            }
        )


def test_iac_filename_base_required() -> None:
    """Missing filename_base raises ValidationError."""
    with pytest.raises(ValidationError):
        S3CompatArchiverIaC.model_validate(
            {
                "endpoint": _ENDPOINT,
                "bucket": _BUCKET,
                "access_key_ref": {"kind": "env", "value": "K"},
                "secret_key_ref": {"kind": "env", "value": "S"},
            }
        )


def test_iac_access_key_ref_required() -> None:
    """Missing access_key_ref raises ValidationError."""
    with pytest.raises(ValidationError):
        S3CompatArchiverIaC.model_validate(
            {
                "endpoint": _ENDPOINT,
                "bucket": _BUCKET,
                "filename_base": "feed",
                "secret_key_ref": {"kind": "env", "value": "S"},
            }
        )


def test_iac_secret_key_ref_required() -> None:
    """Missing secret_key_ref raises ValidationError."""
    with pytest.raises(ValidationError):
        S3CompatArchiverIaC.model_validate(
            {
                "endpoint": _ENDPOINT,
                "bucket": _BUCKET,
                "filename_base": "feed",
                "access_key_ref": {"kind": "env", "value": "K"},
            }
        )


def test_iac_access_key_ref_invalid_kind() -> None:
    """SecretRef with unsupported kind raises ValidationError."""
    with pytest.raises(ValidationError):
        S3CompatArchiverIaC.model_validate(
            {
                "endpoint": _ENDPOINT,
                "bucket": _BUCKET,
                "filename_base": "feed",
                "access_key_ref": {"kind": "ftp", "value": "K"},
                "secret_key_ref": {"kind": "env", "value": "S"},
            }
        )


def test_iac_transport_has_default(compat_credentials: None) -> None:
    """transport block is optional — omitting it uses default values."""
    iac = _make_iac()
    assert iac.transport.timeout_seconds == 60.0
    assert iac.transport.max_retries == 3
    assert iac.transport.verify_tls is True


def test_iac_extra_fields_forbidden() -> None:
    """Extra fields raise ValidationError."""
    with pytest.raises(ValidationError):
        S3CompatArchiverIaC.model_validate(
            {
                "endpoint": _ENDPOINT,
                "bucket": _BUCKET,
                "filename_base": "feed",
                "access_key_ref": {"kind": "env", "value": "K"},
                "secret_key_ref": {"kind": "env", "value": "S"},
                "unknown": "x",
            }
        )


# ---------------------------------------------------------------------------
# __init__ — secret resolution
# ---------------------------------------------------------------------------


def test_init_resolves_secrets_from_env(compat_credentials: None) -> None:
    """Secrets are resolved in __init__ from environment variables."""
    archiver = S3CompatArchiver(_make_iac())
    assert archiver._access_key == _ACCESS_KEY_VAL  # type: ignore[attr-defined]
    assert archiver._secret_key == _SECRET_KEY_VAL  # type: ignore[attr-defined]


def test_init_raises_on_secret_resolution_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """S3CompatArchiverError is raised in __init__ when a secret cannot be resolved."""
    monkeypatch.delenv(_ACCESS_KEY_ENV, raising=False)
    monkeypatch.delenv(_SECRET_KEY_ENV, raising=False)
    with pytest.raises(S3CompatArchiverError, match="credentials"):
        S3CompatArchiver(_make_iac())


# ---------------------------------------------------------------------------
# open() — key generation
# ---------------------------------------------------------------------------


def test_open_generates_object_key(s3_compat_bucket: None) -> None:
    """After open(), _object_key matches {filename_base}_{YYYYMMDD_HHMMSS}."""
    archiver = S3CompatArchiver(_make_iac())
    archiver.open()
    key = archiver._object_key  # type: ignore[attr-defined]
    assert key is not None
    assert re.match(r"product_feed_\d{8}_\d{6}$", key), f"unexpected key: {key}"


def test_open_two_calls_produce_different_keys(s3_compat_bucket: None) -> None:
    """Two archiver instances opened at different UTC times produce different keys."""
    iac = _make_iac()
    t1 = datetime(2026, 3, 18, 10, 30, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 3, 18, 10, 30, 1, tzinfo=timezone.utc)

    with patch(
        "pfp_runtime.publishing.archivers.s3_compat_archiver.datetime"
    ) as mock_dt:
        mock_dt.now.return_value = t1
        a1 = S3CompatArchiver(iac)
        a1.open()
        key1 = a1._object_key  # type: ignore[attr-defined]

    with patch(
        "pfp_runtime.publishing.archivers.s3_compat_archiver.datetime"
    ) as mock_dt:
        mock_dt.now.return_value = t2
        a2 = S3CompatArchiver(iac)
        a2.open()
        key2 = a2._object_key  # type: ignore[attr-defined]

    assert key1 != key2


# ---------------------------------------------------------------------------
# finalize() — content and result
# ---------------------------------------------------------------------------


def test_finalize_writes_content(s3_compat_bucket: Any) -> None:
    """The S3-compat object contains all chunks written via write_chunk()."""
    archiver = S3CompatArchiver(_make_iac())
    archiver.open()
    archiver.write_chunk(b"hello ")
    archiver.write_chunk(b"world")
    result = archiver.finalize()

    body = s3_compat_bucket.get_object(
        Bucket=_BUCKET, Key=archiver._object_key  # type: ignore[attr-defined]
    )["Body"].read()
    assert body == b"hello world"
    assert result.location == "s3://{}/{}".format(
        _BUCKET, archiver._object_key  # type: ignore[attr-defined]
    )


def test_finalize_result(s3_compat_bucket: None) -> None:
    """finalize() returns ArchiveResult(skipped=False, location='s3://...')."""
    archiver = S3CompatArchiver(_make_iac())
    archiver.open()
    result = archiver.finalize()
    assert result.skipped is False
    assert result.location is not None
    assert result.location.startswith("s3://")


# ---------------------------------------------------------------------------
# Lifecycle errors
# ---------------------------------------------------------------------------


def test_write_chunk_before_open_raises(compat_credentials: None) -> None:
    """write_chunk() before open() raises S3CompatArchiverError."""
    archiver = S3CompatArchiver(_make_iac())
    with pytest.raises(S3CompatArchiverError, match="before open"):
        archiver.write_chunk(b"data")


def test_finalize_before_open_raises(compat_credentials: None) -> None:
    """finalize() before open() raises S3CompatArchiverError."""
    archiver = S3CompatArchiver(_make_iac())
    with pytest.raises(S3CompatArchiverError, match="before open"):
        archiver.finalize()


def test_double_finalize_raises(s3_compat_bucket: None) -> None:
    """Calling finalize() a second time raises S3CompatArchiverError."""
    archiver = S3CompatArchiver(_make_iac())
    archiver.open()
    archiver.finalize()
    with pytest.raises(S3CompatArchiverError, match="already called"):
        archiver.finalize()


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


def test_satisfies_archiver_protocol(compat_credentials: None) -> None:
    """isinstance(S3CompatArchiver(iac), Archiver) is True."""
    archiver = S3CompatArchiver(_make_iac())
    assert isinstance(archiver, Archiver)


# ---------------------------------------------------------------------------
# Full cycle
# ---------------------------------------------------------------------------


def test_full_cycle_multiple_chunks(s3_compat_bucket: Any) -> None:
    """open() -> write_chunk() x3 -> finalize() produces correct object content."""
    archiver = S3CompatArchiver(_make_iac(filename_base="report"))
    archiver.open()
    archiver.write_chunk(b"chunk1|")
    archiver.write_chunk(b"chunk2|")
    archiver.write_chunk(b"chunk3")
    result = archiver.finalize()

    assert result == ArchiveResult(skipped=False, location=result.location)
    assert result.location is not None
    body = s3_compat_bucket.get_object(
        Bucket=_BUCKET, Key=archiver._object_key  # type: ignore[attr-defined]
    )["Body"].read()
    assert body == b"chunk1|chunk2|chunk3"
    key = archiver._object_key  # type: ignore[attr-defined]
    assert key is not None
    assert key.startswith("report_")


# ---------------------------------------------------------------------------
# Abort cleanup
# ---------------------------------------------------------------------------


def test_finalize_aborts_on_complete_failure(s3_compat_bucket: None) -> None:
    """On complete_multipart_upload failure, abort_multipart_upload is called."""
    archiver = S3CompatArchiver(_make_iac())
    archiver.open()
    archiver.write_chunk(b"data")

    abort_mock = MagicMock()
    archiver._s3.abort_multipart_upload = abort_mock  # type: ignore[attr-defined]

    with patch.object(
        archiver._s3,
        "complete_multipart_upload",
        side_effect=Exception("storage error"),
    ):
        with pytest.raises(S3CompatArchiverError):
            archiver.finalize()

    abort_mock.assert_called_once()


def test_upload_part_failure_aborts_upload(s3_compat_bucket: None) -> None:
    """On upload_part failure during write_chunk, abort_multipart_upload is called."""
    from pfp_runtime.publishing.archivers.s3_compat_archiver import _MIN_PART_SIZE

    archiver = S3CompatArchiver(_make_iac())
    archiver.open()

    abort_mock = MagicMock()
    archiver._s3.abort_multipart_upload = abort_mock  # type: ignore[attr-defined]

    with patch.object(
        archiver._s3,
        "upload_part",
        side_effect=Exception("network error"),
    ):
        with pytest.raises(S3CompatArchiverError, match="upload_part failed"):
            archiver.write_chunk(b"x" * _MIN_PART_SIZE)

    abort_mock.assert_called_once()


def test_write_chunk_after_finalize_raises(s3_compat_bucket: None) -> None:
    """write_chunk() after finalize() raises S3CompatArchiverError."""
    archiver = S3CompatArchiver(_make_iac())
    archiver.open()
    archiver.finalize()
    with pytest.raises(S3CompatArchiverError, match="after finalize"):
        archiver.write_chunk(b"late data")


def test_double_open_aborts_previous_upload(s3_compat_bucket: None) -> None:
    """Calling open() a second time before finalize() aborts the previous upload."""
    archiver = S3CompatArchiver(_make_iac())
    archiver.open()

    abort_mock = MagicMock()
    archiver._s3.abort_multipart_upload = abort_mock  # type: ignore[attr-defined]

    archiver.open()  # second open — must abort first upload

    abort_mock.assert_called_once()


def test_finalize_upload_part_failure_with_remaining_data(
    s3_compat_bucket: None,
) -> None:
    """Finalize raises S3CompatArchiverError when upload_part fails for remaining buffer."""
    archiver = S3CompatArchiver(_make_iac())
    archiver.open()
    archiver.write_chunk(b"small")  # less than _MIN_PART_SIZE — stays in buffer

    abort_mock = MagicMock()
    archiver._s3.abort_multipart_upload = abort_mock  # type: ignore[attr-defined]

    with patch.object(
        archiver._s3,
        "upload_part",
        side_effect=Exception("network error"),
    ):
        with pytest.raises(S3CompatArchiverError, match="upload_part failed"):
            archiver.finalize()

    abort_mock.assert_called_once()


def test_finalize_put_object_failure_empty_archive(s3_compat_bucket: None) -> None:
    """Finalize raises S3CompatArchiverError when put_object fails for an empty archive."""
    archiver = S3CompatArchiver(_make_iac())
    archiver.open()  # no write_chunk — _parts will be empty

    with patch.object(
        archiver._s3,
        "put_object",
        side_effect=Exception("storage error"),
    ):
        with pytest.raises(S3CompatArchiverError, match="put_object failed"):
            archiver.finalize()


def test_abort_upload_suppresses_errors(s3_compat_bucket: None) -> None:
    """_abort_upload() silently suppresses errors so the original exception is not masked."""
    archiver = S3CompatArchiver(_make_iac())
    archiver.open()

    archiver._s3.abort_multipart_upload = MagicMock(  # type: ignore[attr-defined]
        side_effect=Exception("abort failed")
    )

    # open() again triggers _abort_upload; the abort error must not propagate
    archiver.open()  # should not raise
