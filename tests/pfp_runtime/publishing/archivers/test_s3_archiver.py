"""Tests for publishing/archivers/s3_archiver.py."""

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
from pfp_runtime.publishing.archivers.s3_archiver import (
    S3Archiver,
    S3ArchiverError,
    S3ArchiverIaC,
)

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

_BUCKET = "test-bucket"
_REGION = "us-east-1"


def _make_iac(**kwargs) -> S3ArchiverIaC:  # type: ignore[return]
    defaults = {
        "bucket": _BUCKET,
        "filename_base": "product_feed",
        "region": _REGION,
    }
    defaults.update(kwargs)
    return S3ArchiverIaC.model_validate(defaults)


@pytest.fixture()
def aws_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set dummy AWS credentials so boto3 does not try the real credential chain."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", _REGION)


@pytest.fixture()
def s3_bucket(aws_credentials: None):  # type: ignore[return]
    """Provide a mocked S3 bucket for each test."""
    with mock_aws():
        client = boto3.client("s3", region_name=_REGION)
        client.create_bucket(Bucket=_BUCKET)
        yield client


# ---------------------------------------------------------------------------
# S3ArchiverIaC validation
# ---------------------------------------------------------------------------


def test_iac_bucket_required() -> None:
    """Missing bucket raises ValidationError."""
    with pytest.raises(ValidationError):
        S3ArchiverIaC.model_validate({"filename_base": "feed", "region": _REGION})


def test_iac_filename_base_required() -> None:
    """Missing filename_base raises ValidationError."""
    with pytest.raises(ValidationError):
        S3ArchiverIaC.model_validate({"bucket": _BUCKET, "region": _REGION})


def test_iac_transport_has_default() -> None:
    """transport block is optional — omitting it uses default values."""
    iac = S3ArchiverIaC.model_validate({"bucket": _BUCKET, "filename_base": "feed"})
    assert iac.transport.timeout_seconds == 60.0
    assert iac.transport.max_retries == 3
    assert iac.transport.verify_tls is True


def test_iac_key_prefix_defaults_to_empty() -> None:
    """key_prefix defaults to empty string when not provided."""
    iac = _make_iac()
    assert iac.key_prefix == ""


def test_iac_region_defaults_to_none() -> None:
    """region defaults to None when not provided."""
    iac = S3ArchiverIaC.model_validate({"bucket": _BUCKET, "filename_base": "feed"})
    assert iac.region is None


def test_iac_extra_fields_forbidden() -> None:
    """Extra fields raise ValidationError."""
    with pytest.raises(ValidationError):
        S3ArchiverIaC.model_validate(
            {"bucket": _BUCKET, "filename_base": "feed", "unknown": "x"}
        )


# ---------------------------------------------------------------------------
# open() — key generation
# ---------------------------------------------------------------------------


def test_open_generates_object_key(s3_bucket: None) -> None:
    """After open(), _object_key matches {filename_base}_{YYYYMMDD_HHMMSS}."""
    archiver = S3Archiver(_make_iac())
    archiver.open()
    key = archiver._object_key  # type: ignore[attr-defined]
    assert key is not None
    assert re.match(r"product_feed_\d{8}_\d{6}$", key), f"unexpected key: {key}"


def test_open_generates_key_with_prefix(s3_bucket: None) -> None:
    """With key_prefix set, the object key starts with the prefix."""
    archiver = S3Archiver(_make_iac(key_prefix="sent/"))
    archiver.open()
    key = archiver._object_key  # type: ignore[attr-defined]
    assert key is not None
    assert key.startswith("sent/product_feed_"), f"unexpected key: {key}"


def test_open_two_calls_produce_different_keys(s3_bucket: None) -> None:
    """Two archiver instances opened at different UTC times produce different keys."""
    iac = _make_iac()
    t1 = datetime(2026, 3, 18, 10, 30, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 3, 18, 10, 30, 1, tzinfo=timezone.utc)

    with patch("pfp_runtime.publishing.archivers.s3_archiver.datetime") as mock_dt:
        mock_dt.now.return_value = t1
        a1 = S3Archiver(iac)
        a1.open()
        key1 = a1._object_key  # type: ignore[attr-defined]

    with patch("pfp_runtime.publishing.archivers.s3_archiver.datetime") as mock_dt:
        mock_dt.now.return_value = t2
        a2 = S3Archiver(iac)
        a2.open()
        key2 = a2._object_key  # type: ignore[attr-defined]

    assert key1 != key2


# ---------------------------------------------------------------------------
# finalize() — content and result
# ---------------------------------------------------------------------------


def test_finalize_writes_content(s3_bucket: Any) -> None:
    """The S3 object contains all chunks written via write_chunk()."""
    archiver = S3Archiver(_make_iac())
    archiver.open()
    archiver.write_chunk(b"hello ")
    archiver.write_chunk(b"world")
    result = archiver.finalize()

    body = s3_bucket.get_object(
        Bucket=_BUCKET, Key=archiver._object_key  # type: ignore[attr-defined]
    )["Body"].read()
    assert body == b"hello world"
    assert result.location == "s3://{}/{}".format(
        _BUCKET, archiver._object_key  # type: ignore[attr-defined]
    )


def test_finalize_result(s3_bucket: None) -> None:
    """finalize() returns ArchiveResult(skipped=False, location='s3://...')."""
    archiver = S3Archiver(_make_iac())
    archiver.open()
    result = archiver.finalize()
    assert result.skipped is False
    assert result.location is not None
    assert result.location.startswith("s3://")


# ---------------------------------------------------------------------------
# Lifecycle errors
# ---------------------------------------------------------------------------


def test_write_chunk_before_open_raises() -> None:
    """write_chunk() before open() raises S3ArchiverError."""
    archiver = S3Archiver(_make_iac())
    with pytest.raises(S3ArchiverError, match="before open"):
        archiver.write_chunk(b"data")


def test_finalize_before_open_raises() -> None:
    """finalize() before open() raises S3ArchiverError."""
    archiver = S3Archiver(_make_iac())
    with pytest.raises(S3ArchiverError, match="before open"):
        archiver.finalize()


def test_double_finalize_raises(s3_bucket: None) -> None:
    """Calling finalize() a second time raises S3ArchiverError."""
    archiver = S3Archiver(_make_iac())
    archiver.open()
    archiver.finalize()
    with pytest.raises(S3ArchiverError, match="already called"):
        archiver.finalize()


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


def test_satisfies_archiver_protocol() -> None:
    """isinstance(S3Archiver(iac), Archiver) is True."""
    archiver = S3Archiver(_make_iac())
    assert isinstance(archiver, Archiver)


# ---------------------------------------------------------------------------
# Full cycle
# ---------------------------------------------------------------------------


def test_full_cycle_multiple_chunks(s3_bucket: Any) -> None:
    """open() -> write_chunk() x3 -> finalize() produces correct S3 object content."""
    archiver = S3Archiver(_make_iac(filename_base="report"))
    archiver.open()
    archiver.write_chunk(b"chunk1|")
    archiver.write_chunk(b"chunk2|")
    archiver.write_chunk(b"chunk3")
    result = archiver.finalize()

    assert result == ArchiveResult(skipped=False, location=result.location)
    assert result.location is not None
    body = s3_bucket.get_object(
        Bucket=_BUCKET, Key=archiver._object_key  # type: ignore[attr-defined]
    )["Body"].read()
    assert body == b"chunk1|chunk2|chunk3"
    key = archiver._object_key  # type: ignore[attr-defined]
    assert key is not None
    assert key.startswith("report_")


# ---------------------------------------------------------------------------
# Abort on complete failure
# ---------------------------------------------------------------------------


def test_finalize_aborts_on_complete_failure(s3_bucket: None) -> None:
    """On complete_multipart_upload failure, abort_multipart_upload is called."""
    archiver = S3Archiver(_make_iac())
    archiver.open()
    archiver.write_chunk(b"data")

    abort_mock = MagicMock()
    archiver._s3.abort_multipart_upload = abort_mock  # type: ignore[attr-defined]

    with patch.object(
        archiver._s3,
        "complete_multipart_upload",
        side_effect=Exception("S3 error"),
    ):
        with pytest.raises(S3ArchiverError):
            archiver.finalize()

    abort_mock.assert_called_once()


def test_write_chunk_after_finalize_raises(s3_bucket: None) -> None:
    """write_chunk() after finalize() raises S3ArchiverError."""
    archiver = S3Archiver(_make_iac())
    archiver.open()
    archiver.finalize()
    with pytest.raises(S3ArchiverError, match="after finalize"):
        archiver.write_chunk(b"late data")


def test_upload_part_failure_aborts_upload(s3_bucket: None) -> None:
    """On upload_part failure during write_chunk, abort_multipart_upload is called."""
    archiver = S3Archiver(_make_iac())
    archiver.open()

    abort_mock = MagicMock()
    archiver._s3.abort_multipart_upload = abort_mock  # type: ignore[attr-defined]

    # Force _upload_part to be called by injecting exactly _MIN_PART_SIZE bytes,
    # then patching upload_part to fail.
    from pfp_runtime.publishing.archivers.s3_archiver import _MIN_PART_SIZE

    with patch.object(
        archiver._s3,
        "upload_part",
        side_effect=Exception("network error"),
    ):
        with pytest.raises(S3ArchiverError, match="upload_part failed"):
            archiver.write_chunk(b"x" * _MIN_PART_SIZE)

    abort_mock.assert_called_once()


def test_double_open_aborts_previous_upload(s3_bucket: None) -> None:
    """Calling open() a second time before finalize() aborts the previous upload."""
    archiver = S3Archiver(_make_iac())
    archiver.open()

    abort_mock = MagicMock()
    archiver._s3.abort_multipart_upload = abort_mock  # type: ignore[attr-defined]

    archiver.open()  # second open — must abort first upload

    abort_mock.assert_called_once()


def test_finalize_upload_part_failure_with_remaining_data(s3_bucket: None) -> None:
    """Finalize raises S3ArchiverError when upload_part fails for remaining buffer."""
    archiver = S3Archiver(_make_iac())
    archiver.open()
    archiver.write_chunk(b"small")  # less than _MIN_PART_SIZE — stays in buffer

    abort_mock = MagicMock()
    archiver._s3.abort_multipart_upload = abort_mock  # type: ignore[attr-defined]

    with patch.object(
        archiver._s3,
        "upload_part",
        side_effect=Exception("network error"),
    ):
        with pytest.raises(S3ArchiverError, match="upload_part failed"):
            archiver.finalize()

    abort_mock.assert_called_once()


def test_finalize_put_object_failure_empty_archive(s3_bucket: None) -> None:
    """Finalize raises S3ArchiverError when put_object fails for an empty archive."""
    archiver = S3Archiver(_make_iac())
    archiver.open()  # no write_chunk — _parts will be empty

    with patch.object(
        archiver._s3,
        "put_object",
        side_effect=Exception("storage error"),
    ):
        with pytest.raises(S3ArchiverError, match="put_object failed"):
            archiver.finalize()


def test_abort_upload_suppresses_errors(s3_bucket: None) -> None:
    """_abort_upload() silently suppresses errors so the original exception is not masked."""
    archiver = S3Archiver(_make_iac())
    archiver.open()

    archiver._s3.abort_multipart_upload = MagicMock(  # type: ignore[attr-defined]
        side_effect=Exception("abort failed")
    )

    # open() again triggers _abort_upload; the abort error must not propagate
    archiver.open()  # should not raise
