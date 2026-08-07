"""Contract tests for runtime observability metrics, diagnostics events, and NoOp invariance."""

# ruff: noqa: E402

from datetime import datetime, timezone
from pathlib import Path
from types import MethodType
from typing import Any, cast

import pytest

prometheus_client = pytest.importorskip(
    "prometheus_client", reason="prometheus extra not installed"
)

from pfp_core.artifact_production import prepare_artifact_producer_from_files
from pfp_core.contracts import BuildResult
from pfp_core.contracts.artifact_metadata import ArtifactMetadata
from pfp_core.contracts.produced_artifact import ProducedArtifact
from pfp_runtime.manifest.pipeline_manifest import (
    ConnectorManifest,
    CoreManifest,
    ObservabilityManifest,
    PipelineManifest,
    PublishManifest,
    RunContext,
)
from pfp_runtime.orchestration.pipeline_runner import PipelineRunner
from pfp_runtime.pipeline.execution_report import ExecutionReport
from pfp_runtime.publishing.publisher_builder import build_publisher
from pfp_utils.diagnostics import FeedUsage
from pfp_utils.diagnostics.diagnostic_models import Diagnostic
from pfp_utils.diagnostics.validation_report import ValidationReport
from pfp_utils.telemetry import NoOpTelemetryHandler, PrometheusTelemetryHandler


class _LogPipelineStub:
    """Forwarding stub: routes log_process to stdlib so caplog can capture it."""

    def log_process(
        self, level: int, module_name: str, message: str, *args: Any, **kwargs: Any
    ) -> None:
        import logging as _stdlib

        extra = kwargs.get("extra")
        _stdlib.getLogger(module_name).log(level, message, *args, extra=extra)


_PYTHON_ROOT_ER = Path(__file__).resolve().parents[3]
_NOOP_OUTPUT_CONFIG_ER = {
    "archive_type": "noop",
    "archive_config": str(_PYTHON_ROOT_ER / "config" / "archive" / "noop.yaml"),
    "client_type": "noop",
    "client_config": str(_PYTHON_ROOT_ER / "config" / "clients" / "noop.yaml"),
}


class _ExtractResult:
    def __init__(self, items):
        self._items = items

    def __iter__(self):
        return iter(self._items)


class _FakeConnector:
    def __init__(self, items):
        self._items = items

    def extract(self, raw_input):
        del raw_input
        return _ExtractResult(self._items)


def _metadata() -> ArtifactMetadata:
    return ArtifactMetadata(
        target="stripe.product",
        schema_version="1.0.0",
        generated_at=datetime(2026, 2, 24, tzinfo=timezone.utc),
        content_type="text/csv",
        encoding="utf-8",
        artifact_profile="catalog_snapshot",
        filename_hint="stripe.product__FULL__v1.0.0.csv",
    )


def _artifact() -> ProducedArtifact:
    return ProducedArtifact(payload=iter([b"x"]), metadata=_metadata())


def _build_runner(*, telemetry_enabled: bool, telemetry_handler: Any = None) -> tuple:
    """Build runner and manifest pair."""
    manifest = _build_manifest(
        telemetry_enabled=telemetry_enabled,
        telemetry_handler=telemetry_handler,
    )
    runner = PipelineRunner(manifest)
    return runner, manifest


def _build_manifest(
    *,
    telemetry_enabled: bool,
    telemetry_handler: Any = None,
) -> PipelineManifest:
    python_root = _PYTHON_ROOT_ER
    producer = prepare_artifact_producer_from_files(
        schema_file=str(
            python_root
            / "schemas"
            / "stripe.product_feed"
            / "stripe.product_feed-1.0.0.yaml"
        ),
        policy_file=str(python_root / "config" / "policies.yaml"),
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    )
    publisher = build_publisher(_NOOP_OUTPUT_CONFIG_ER, log_pipeline=_LogPipelineStub())  # type: ignore[arg-type]
    return PipelineManifest(
        ingestion=ConnectorManifest(
            connector=cast(Any, _FakeConnector(items=[{"item_id": "SKU-1"}])),
            raw_input=b"fake-data",
        ),
        core=CoreManifest(producer=producer),
        publish=PublishManifest(publisher=publisher),
        run_context=RunContext(
            run_id="story-11.8-run",
            correlation_id="story-11.8-correlation",
        ),
        observability=ObservabilityManifest(
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
            telemetry_enabled=telemetry_enabled,
            telemetry_handler=(
                telemetry_handler
                if telemetry_handler is not None
                else NoOpTelemetryHandler()
            ),
            labels={
                "run_id": "story-11.8-run",
                "correlation_id": "story-11.8-correlation",
            },
        ),
    )


def _patch_producer(
    monkeypatch: pytest.MonkeyPatch,
    *,
    manifest: PipelineManifest,
    telemetry: PrometheusTelemetryHandler,
) -> None:
    def fake_produce(self, um, *, generated_at=None):
        del self, generated_at
        assert list(um) == [{"item_id": "SKU-1"}]
        telemetry.observe_duration(
            "validation",
            0.01,
            {
                "target": "stripe.product_feed",
            },
        )
        report = ValidationReport(target="stripe.product")
        report.add(
            Diagnostic(
                severity="WARN",
                code="OBS.CONTRACT",
                message="observability diagnostic contract",
                item_ref="SKU-1",
            )
        )
        return BuildResult(
            artifacts=(_artifact(),),
            validation_report=report,
        )

    monkeypatch.setattr(
        manifest.core.producer,
        "produce_artifacts",
        MethodType(fake_produce, manifest.core.producer),
    )


def test_observability_contract_metrics_and_runtime_diagnostics_logging(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Emit stage duration telemetry and log diagnostics while usage stays in the report."""
    registry = prometheus_client.CollectorRegistry()
    telemetry = PrometheusTelemetryHandler(registry=registry)

    runner, manifest = _build_runner(
        telemetry_enabled=True,
        telemetry_handler=telemetry,
    )
    _patch_producer(monkeypatch, manifest=manifest, telemetry=telemetry)

    caplog.set_level("INFO", logger="pfp_runtime.pipeline.log_filters")
    report = runner.run(b"fake-data")

    assert report.status == "SUCCESS"
    assert report.usage.input_items_count == 1
    assert report.usage.processed == 1
    assert report.usage.artifacts_count == 1

    payload = prometheus_client.generate_latest(registry).decode("utf-8")
    assert 'target="stripe.product_feed"' in payload
    assert "pfp_stage_duration_seconds" in payload
    assert 'stage="validation"' in payload

    assert any(
        "Runtime diagnostics event" in record.message for record in caplog.records
    )
    assert any("OBS.CONTRACT" in record.message for record in caplog.records)


def test_observability_contract_noop_telemetry_keeps_functional_behavior(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep pipeline functional result semantics unchanged when telemetry is disabled (NoOp)."""
    registry = prometheus_client.CollectorRegistry()
    telemetry = PrometheusTelemetryHandler(registry=registry)

    runner_on, manifest_on = _build_runner(
        telemetry_enabled=True,
        telemetry_handler=telemetry,
    )
    runner_off, manifest_off = _build_runner(
        telemetry_enabled=False,
        telemetry_handler=NoOpTelemetryHandler(),
    )
    _patch_producer(monkeypatch, manifest=manifest_on, telemetry=telemetry)
    _patch_producer(monkeypatch, manifest=manifest_off, telemetry=telemetry)

    report_on = runner_on.run(b"fake-data")
    report_off = runner_off.run(b"fake-data")

    assert report_on.status == report_off.status
    assert report_on.failed_step == report_off.failed_step
    assert report_on.reason_code == report_off.reason_code
    assert len(report_on.artifacts) == len(report_off.artifacts)
    assert (
        report_on.validation_report.to_dict() == report_off.validation_report.to_dict()
    )
    assert report_on.usage == report_off.usage


# ---------------------------------------------------------------------------
# ExecutionReport.artifacts field contract
# ---------------------------------------------------------------------------


def test_execution_report_artifacts_field_default_empty() -> None:
    """ExecutionReport.artifacts defaults to empty tuple."""
    report = ExecutionReport(
        status="SUCCESS",
        failed_step="",
        reason_code="",
        message="ok",
        validation_report=ValidationReport(target=None, artifact_profile=None),
    )
    assert report.artifacts == ()


def test_execution_report_usage_field_default_empty() -> None:
    """ExecutionReport.usage defaults to empty FeedUsage snapshot."""
    report = ExecutionReport(
        status="SUCCESS",
        failed_step="",
        reason_code="",
        message="ok",
        validation_report=ValidationReport(target=None, artifact_profile=None),
    )
    assert report.usage == FeedUsage()


def test_execution_report_counters_property_reflects_usage_snapshot() -> None:
    """Expose a legacy counters mapping derived from the typed usage snapshot."""
    usage = FeedUsage(
        input_items_count=4,
        artifacts_count=1,
        processed=4,
        dropped=0,
        errors=0,
        diagnostics_count_by_severity={"ERROR": 0, "WARN": 2, "INFO": 1},
    )
    report = ExecutionReport(
        status="SUCCESS",
        failed_step="",
        reason_code="",
        message="ok",
        validation_report=ValidationReport(target=None, artifact_profile=None),
        usage=usage,
    )

    assert report.counters == {
        "input_items_count": 4,
        "artifacts_count": 1,
        "diagnostics_count_by_severity": {"ERROR": 0, "WARN": 2, "INFO": 1},
        "processed": 4,
        "dropped": 0,
        "error": 0,
    }


def test_execution_report_artifacts_field_type() -> None:
    """ExecutionReport.artifacts accepts Tuple[ProducedArtifact, ...]."""
    artifact = ProducedArtifact(payload=tuple([b"x"]), metadata=_metadata())
    report = ExecutionReport(
        status="SUCCESS",
        failed_step="",
        reason_code="",
        message="ok",
        validation_report=ValidationReport(target=None, artifact_profile=None),
        artifacts=(artifact,),
    )
    assert len(report.artifacts) == 1
    assert report.artifacts[0] is artifact


def test_execution_report_has_no_published_artifacts_field() -> None:
    """ExecutionReport no longer has a published_artifacts field."""
    report = ExecutionReport(
        status="SUCCESS",
        failed_step="",
        reason_code="",
        message="ok",
        validation_report=ValidationReport(target=None, artifact_profile=None),
    )
    assert not hasattr(report, "published_artifacts")


def test_execution_report_has_no_partial_publish_field() -> None:
    """ExecutionReport no longer has a partial_publish field."""
    report = ExecutionReport(
        status="SUCCESS",
        failed_step="",
        reason_code="",
        message="ok",
        validation_report=ValidationReport(target=None, artifact_profile=None),
    )
    assert not hasattr(report, "partial_publish")
