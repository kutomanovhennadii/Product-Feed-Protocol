"""Integration tests for the pfp_runtime.orchestration block."""

from __future__ import annotations

from pathlib import Path

import pytest

from pfp_runtime.manifest.pipeline_manifest_provider import build_pipeline_manifest
from pfp_runtime.orchestration.pipeline_runner import PipelineRunner
from tests.pfp_runtime._integration_helpers import (
    runtime_csv_input,
    write_runtime_infra,
)


def test_pipeline_runner_reports_validation_stop_as_header_only_success(
    tmp_path: Path,
) -> None:
    """Pipeline runner exposes validation-stop diagnostics even when the report is SUCCESS.

    Args:
        tmp_path: Temporary directory that stores the generated runtime infra file.
    """

    manifest = build_pipeline_manifest(str(write_runtime_infra(tmp_path)))
    report = PipelineRunner(manifest).run(runtime_csv_input())

    assert report.status == "SUCCESS"
    assert report.failed_step == ""
    assert len(report.artifacts) == 1
    assert report.artifacts[0].payload == (b"id,title,description,link,availability\n",)
    assert {diagnostic.code for diagnostic in report.validation_report.diagnostics} >= {
        "BUILD.FAIL_STOP",
        "STRIPE_TITLE_REQUIRED",
    }
    assert report.validation_report.target == "stripe.product_feed"
    assert report.counters["artifacts_count"] == 1


def test_pipeline_runner_reports_ingestion_extract_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pipeline runner maps synchronous connector failures to ingestion failure reports.

    Args:
        tmp_path: Temporary directory that stores the generated runtime infra file.
        monkeypatch: Pytest helper used to replace the connector boundary.
    """

    manifest = build_pipeline_manifest(str(write_runtime_infra(tmp_path)))

    def _failing_extract(_raw_input: bytes) -> None:
        raise ValueError("extract failed")

    monkeypatch.setattr(manifest.ingestion.connector, "extract", _failing_extract)

    report = PipelineRunner(manifest).run(runtime_csv_input())

    assert report.status == "FAILED"
    assert report.failed_step == "INGESTION_EXTRACT"
    assert report.reason_code == "INGESTION.EXTRACT_ERROR"
    assert report.error_type == "ValueError"
    assert report.artifacts == ()


def test_pipeline_runner_reports_core_contract_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pipeline runner maps producer contract failures to core build reports.

    Args:
        tmp_path: Temporary directory that stores the generated runtime infra file.
        monkeypatch: Pytest helper used to replace the producer boundary.
    """

    manifest = build_pipeline_manifest(str(write_runtime_infra(tmp_path)))

    def _failing_produce(*_args: object, **_kwargs: object) -> None:
        raise ValueError("producer contract failed")

    monkeypatch.setattr(manifest.core.producer, "produce_artifacts", _failing_produce)

    report = PipelineRunner(manifest).run(runtime_csv_input())

    assert report.status == "FAILED"
    assert report.failed_step == "CORE_BUILD"
    assert report.reason_code == "CORE.CONTRACT_ERROR"
    assert report.error_type == "ValueError"
    assert report.artifacts == ()


def test_pipeline_runner_reports_publish_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pipeline runner maps publisher failures to publish failure reports.

    Args:
        tmp_path: Temporary directory that stores the generated runtime infra file.
        monkeypatch: Pytest helper used to replace the publisher boundary.
    """

    manifest = build_pipeline_manifest(str(write_runtime_infra(tmp_path)))

    def _failing_publish(_artifact: object) -> None:
        raise TimeoutError("publish timed out")

    monkeypatch.setattr(manifest.publish.publisher, "publish", _failing_publish)

    report = PipelineRunner(manifest).run(runtime_csv_input())

    assert report.status == "FAILED"
    assert report.failed_step == "PUBLISH"
    assert report.reason_code == "PUBLISH.TIMEOUT"
    assert report.error_type == "TimeoutError"
    assert report.artifacts == ()
