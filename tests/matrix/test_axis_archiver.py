"""Archiver-axis matrix coverage for Phase 10.

Returns:
    None.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import boto3
import pytest

from pfp_runtime.publishing.contracts import PublishMetadata
from tests.matrix._axis_helpers import (
    MATRIX_ROOT,
    assert_success_baseline,
    clone_infra_with_overrides,
    count_fixture_records,
    read_yaml,
    write_yaml,
)
from tests.matrix.matrix_runner import run_matrix_cell

_ARCHIVER_CASES = (
    pytest.param("infra_noop.yaml", "noop", id="noop"),
    pytest.param("infra_local.yaml", "local", id="local"),
    pytest.param("infra_s3.yaml", "s3", id="s3"),
    pytest.param("infra_s3_compat.yaml", "s3_compat", id="s3-compat"),
)


def _extract_s3_key(location: str, bucket_name: str) -> str:
    """Extract the object key from an ``s3://`` location string.

    Args:
        location: Full archive location returned by the runtime.
        bucket_name: Expected bucket name prefix.

    Returns:
        Object key component stored in S3.
    """
    prefix = f"s3://{bucket_name}/"
    assert location.startswith(prefix)
    return location[len(prefix) :]


@pytest.mark.parametrize(("infra_name", "archive_type"), _ARCHIVER_CASES)
def test_archiver_axis_persists_payload_to_expected_destination(
    infra_name: str,
    archive_type: str,
    monkeypatch: pytest.MonkeyPatch,
    moto_s3_bucket: str,
    tmp_archive_dir: Path,
    tmp_path: Path,
) -> None:
    """Each archiver variant must either skip or persist the published bytes correctly.

    Args:
        infra_name: Archiver infra filename.
        archive_type: Expected runtime archiver type token.
        monkeypatch: Pytest monkeypatch fixture for environment and patches.
        moto_s3_bucket: Hermetic S3 bucket name.
        tmp_archive_dir: Temporary local archive directory.
        tmp_path: Temporary directory for rewritten infra/config files.

    Returns:
        None.
    """
    base_infra_path = MATRIX_ROOT / "infra" / "archiver" / infra_name
    fixture_path = MATRIX_ROOT / "fixtures" / "default.jsonl"
    input_format = str(read_yaml(base_infra_path)["input"]["format"])
    infra_path = base_infra_path
    s3_client = boto3.client("s3", region_name="us-east-1")

    if archive_type == "local":
        archive_config = write_yaml(
            tmp_path / "archive_local.yaml",
            {
                "output_dir": str(tmp_archive_dir),
                "filename_base": "matrix_feed",
            },
        )
        infra_path = clone_infra_with_overrides(
            tmp_path,
            base_infra_path,
            archive_config=archive_config,
        )
        result = run_matrix_cell(infra_path=infra_path, fixture_path=fixture_path)
    elif archive_type == "s3":
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
        monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
        result = run_matrix_cell(infra_path=infra_path, fixture_path=fixture_path)
    elif archive_type == "s3_compat":
        monkeypatch.setenv("MATRIX_S3_ACCESS_KEY", "minioaccess")
        monkeypatch.setenv("MATRIX_S3_SECRET_KEY", "miniosecret")
        monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
        with patch(
            "pfp_runtime.publishing.archivers.s3_compat_archiver.boto3"
        ) as mock_boto3:
            mock_boto3.client.return_value = s3_client
            result = run_matrix_cell(infra_path=infra_path, fixture_path=fixture_path)
    else:
        result = run_matrix_cell(infra_path=infra_path, fixture_path=fixture_path)

    assert_success_baseline(
        result,
        golden_path=MATRIX_ROOT / "golden" / "archiver" / "expected.csv",
        expected_target="stripe.product_feed",
        expected_content_type="text/csv",
        expected_input_count=count_fixture_records(fixture_path, input_format),
    )

    metadata = result.report.artifacts[0].metadata
    assert isinstance(metadata, PublishMetadata)
    assert metadata.delivery_skipped is True
    assert metadata.delivery_status_code is None

    if archive_type == "noop":
        assert metadata.archive_skipped is True
        assert metadata.location is None
        return

    assert metadata.archive_skipped is False
    assert metadata.location is not None

    if archive_type == "local":
        archived_path = Path(metadata.location)
        assert archived_path.exists()
        assert archived_path.parent == tmp_archive_dir.resolve()
        assert archived_path.read_bytes() == result.csv_payload
        return

    object_key = _extract_s3_key(metadata.location, moto_s3_bucket)
    archived_body = s3_client.get_object(Bucket=moto_s3_bucket, Key=object_key)[
        "Body"
    ].read()
    assert archived_body == result.csv_payload
