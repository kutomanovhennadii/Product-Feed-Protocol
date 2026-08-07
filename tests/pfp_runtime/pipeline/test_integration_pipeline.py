"""Integration tests for the pfp_runtime.pipeline block."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter

import pytest

from pfp_runtime.manifest.pipeline_manifest_provider import build_pipeline_manifest
from pfp_runtime.pipeline.core_guard import core_step
from pfp_runtime.pipeline.ingestion_guard import (
    IngestionExtractIterationError,
    ingestion_step,
)
from pfp_runtime.pipeline.publish_guard import PublishError, publish_step
from pfp_runtime.pipeline.report_step import report_step
from pfp_runtime.pipeline.run_report import RunReport
from pfp_utils.diagnostics import FeedUsageCollector
from tests.pfp_runtime._integration_helpers import (
    runtime_csv_input,
    write_runtime_infra,
)


def test_pipeline_steps_compose_into_successful_execution_report(
    tmp_path: Path,
) -> None:
    """Pipeline block chains ingestion, core, publish, and report into success.

    Args:
        tmp_path: Temporary directory that stores the generated runtime infra file.
    """

    manifest = build_pipeline_manifest(str(write_runtime_infra(tmp_path)))

    um_items, ingestion_diagnostics = ingestion_step(
        manifest.ingestion.connector,
        runtime_csv_input(),
    )
    core_result = core_step(
        manifest.core.producer, um_items, manifest.core.generated_at
    )
    published = publish_step(core_result.artifacts[0], manifest.publish)

    ctx = RunReport(started_at=perf_counter(), collector=FeedUsageCollector())
    ctx.ingestion_diagnostics = ingestion_diagnostics
    ctx.validation_report = core_result.validation_report
    ctx.artifact = published
    report = report_step(ctx)

    assert report.status == "SUCCESS"
    assert len(report.artifacts) == 1
    assert report.artifacts[0].payload == (b"id,title,description,link,availability\n",)
    assert {diagnostic.code for diagnostic in report.validation_report.diagnostics} >= {
        "BUILD.FAIL_STOP",
        "STRIPE_TITLE_REQUIRED",
    }
    assert report.validation_report.target == "stripe.product_feed"
    assert report.counters["artifacts_count"] == 1


def test_ingestion_step_wraps_adapter_decode_failures(tmp_path: Path) -> None:
    """Pipeline block maps adapter decode errors into ingestion iteration failures.

    Args:
        tmp_path: Temporary directory that stores the generated runtime infra file.
    """

    manifest = build_pipeline_manifest(str(write_runtime_infra(tmp_path)))
    items, _ = ingestion_step(manifest.ingestion.connector, b"\x81invalid")

    with pytest.raises(
        IngestionExtractIterationError,
        match="Failed to decode raw_input as utf-8",
    ):
        list(items)


def test_publish_step_wraps_runtime_publisher_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pipeline block re-raises publisher failures as ``PublishError``.

    Args:
        tmp_path: Temporary directory that stores the generated runtime infra file.
        monkeypatch: Pytest helper used to replace the publisher boundary.
    """

    manifest = build_pipeline_manifest(str(write_runtime_infra(tmp_path)))
    um_items, _ = ingestion_step(manifest.ingestion.connector, runtime_csv_input())
    core_result = core_step(
        manifest.core.producer,
        um_items,
        manifest.core.generated_at,
    )

    def _failing_publish(_artifact: object) -> None:
        raise RuntimeError("publish failed")

    monkeypatch.setattr(manifest.publish.publisher, "publish", _failing_publish)

    with pytest.raises(PublishError, match="publish failed"):
        publish_step(core_result.artifacts[0], manifest.publish)
