"""Integration tests for runtime secret resolver and redaction helpers."""

from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from types import MethodType
from typing import Any

import pytest

from pfp_core.artifact_production import prepare_artifact_producer_from_files
from pfp_core.contracts import Artifact, BuildResult
from pfp_core.contracts.artifact_metadata import ArtifactMetadata
from pfp_runtime.manifest.pipeline_manifest import (
    ConnectorManifest,
    CoreManifest,
    ObservabilityManifest,
    PipelineManifest,
    PublishManifest,
)
from pfp_runtime.orchestration.pipeline_runner import PipelineRunner
from pfp_runtime.pipeline.report_step import report_step
from pfp_runtime.pipeline.run_report import RunReport
from pfp_utils.diagnostics import FeedUsageCollector
from pfp_utils.diagnostics.diagnostic_models import Diagnostic
from pfp_utils.diagnostics.validation_report import ValidationReport


class _LogPipelineStub:
    """Forwarding stub: routes log_process to stdlib so caplog can capture it."""

    def log_process(
        self, level: int, module_name: str, message: str, *_args: Any, **kwargs: Any
    ) -> None:
        import logging as _stdlib

        extra = kwargs.get("extra")
        _stdlib.getLogger(module_name).log(level, message, extra=extra)


class _ExtractResult:
    def __init__(self, items, diagnostics=()):
        self._items = items
        self._diagnostics = tuple(diagnostics)

    def __iter__(self):
        return iter(self._items)

    @property
    def diagnostics(self):
        return self._diagnostics


class _Connector:
    def extract(self, raw_input: Any) -> _ExtractResult:
        del raw_input
        return _ExtractResult(
            [{"item_id": "SKU-1"}],
            diagnostics=(
                Diagnostic(
                    severity="WARN",
                    code="INGESTION.SECRET",
                    message="token=ingestion-secret-token",
                    metadata={"password": "ingestion-secret-token"},
                ),
            ),
        )


def _artifact(target: str = "stripe.product") -> Artifact:
    return Artifact(
        payload=iter([b"x"]),
        metadata=ArtifactMetadata(
            target=target,
            artifact_profile="catalog_snapshot",
            schema_version="1.0.0",
            generated_at=datetime(2026, 2, 24, tzinfo=timezone.utc),
            content_type="text/csv",
            encoding="utf-8",
            filename_hint=target + "__FULL__v1.0.0.csv",
        ),
    )


def _manifest() -> PipelineManifest:
    python_root = Path(__file__).resolve().parents[3]
    config_root = python_root / "config"
    producer = prepare_artifact_producer_from_files(
        schema_file=str(
            python_root
            / "schemas"
            / "stripe.product_feed"
            / "stripe.product_feed-1.0.0.yaml"
        ),
        policy_file=str(config_root / "policies.yaml"),
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    )
    from pfp_runtime.publishing.publisher_builder import build_publisher

    publisher = build_publisher(
        {
            "archive_type": "noop",
            "archive_config": str(config_root / "archive" / "noop.yaml"),
            "client_type": "noop",
            "client_config": str(config_root / "clients" / "noop.yaml"),
        },
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    )
    return PipelineManifest(
        ingestion=ConnectorManifest(
            connector=_Connector(),  # type: ignore[arg-type]
            raw_input=b"fake-data",
        ),
        core=CoreManifest(producer=producer),
        publish=PublishManifest(publisher=publisher),
        observability=ObservabilityManifest(
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
        ),
    )


def test_execution_report_success_validation_report_is_sanitized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensures success report diagnostics hide secret content in message and metadata."""
    manifest = _manifest()
    runner = PipelineRunner(manifest)

    def _fake_produce(self, um, *, generated_at=None):
        del self, um, generated_at
        report = ValidationReport(target="stripe.product")
        report.add(
            Diagnostic(
                severity="WARN",
                code="CORE.SECRET",
                message="api_key=core-secret-value",
                metadata={"token": "core-secret-value"},
            )
        )
        return BuildResult(
            artifacts=(_artifact(),),
            validation_report=report,
        )

    monkeypatch.setattr(
        manifest.core.producer,
        "produce_artifacts",
        MethodType(_fake_produce, manifest.core.producer),
    )

    execution_report = runner.run(b"fake-data")
    rendered = execution_report.validation_report.to_dict()

    assert execution_report.status == "SUCCESS"
    assert "core-secret-value" not in str(rendered)
    assert "ingestion-secret-token" not in str(rendered)
    assert "***" in str(rendered)


def test_execution_report_failure_validation_report_is_sanitized() -> None:
    """Ensures failure report validation_report surface does not leak raw secrets."""
    report = ValidationReport(target="stripe.product")
    report.add(
        Diagnostic(
            severity="ERROR",
            code="CORE.FAIL",
            message="password=core-failure-secret",
            metadata={"api_key": "core-failure-secret"},
        )
    )

    execution_report = report_step(
        RunReport(
            started_at=perf_counter(),
            collector=FeedUsageCollector(),
            validation_report=report,
        ).fail(
            failed_step="CORE",
            reason_code="CORE.ERROR",
            exc=RuntimeError("failed with token=core-failure-secret"),
        )
    )
    rendered = execution_report.validation_report.to_dict()

    assert execution_report.status == "FAILED"
    assert "core-failure-secret" not in str(rendered)
    assert "***" in str(rendered)
