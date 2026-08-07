"""Mirror unit tests for pfp_runtime.pipeline.report_step."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

import pfp_runtime.pipeline.report_step as report_step_module
from pfp_core.contracts.artifact_metadata import ArtifactMetadata
from pfp_core.contracts.produced_artifact import ProducedArtifact
from pfp_runtime.pipeline.report_step import report_step
from pfp_runtime.pipeline.run_report import RunReport
from pfp_utils.diagnostics import Diagnostic, FeedUsageCollector, ValidationReport


class _WrappedError(RuntimeError):
    """Local wrapper exposing ``original_exc`` for failure-path tests."""

    def __init__(self, original_exc: Exception) -> None:
        """Store the wrapped exception on the test double.

        Args:
            original_exc: Exception exposed through the wrapper contract.

        Returns:
            None.
        """
        super().__init__("wrapped")
        self.original_exc = original_exc


def _make_artifact() -> ProducedArtifact:
    """Build a minimal produced artifact for report-step tests.

    Returns:
        ProducedArtifact with deterministic metadata.
    """
    return ProducedArtifact(
        payload=(b"chunk",),
        metadata=ArtifactMetadata(
            target="target",
            schema_version="1.0",
            generated_at=datetime(2026, 4, 29, tzinfo=timezone.utc),
            content_type="application/octet-stream",
            encoding="utf-8",
        ),
    )


def test_report_step_builds_success_execution_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Finalize success state with one sanitize pass and usage counters.

    Returns:
        None.
    """
    original_report = ValidationReport(target="catalog", artifact_profile="profile")
    original_report.add(Diagnostic("ERROR", code="VAL", message="unsafe validation"))
    sanitized_report = ValidationReport(target="catalog", artifact_profile="profile")
    sanitized_validation = Diagnostic(
        "ERROR",
        code="VAL",
        message="safe validation",
    )
    sanitized_ingestion = Diagnostic(
        "WARN",
        code="ING",
        message="safe ingestion",
    )
    sanitized_report.add(sanitized_validation)
    sanitize_calls = []

    def _fake_sanitize_validation_report(report: ValidationReport) -> ValidationReport:
        sanitize_calls.append(report)
        return sanitized_report

    def _fake_sanitize_diagnostic(diagnostic: Diagnostic) -> Diagnostic:
        assert diagnostic.code == "ING"
        return sanitized_ingestion

    monkeypatch.setattr(
        report_step_module,
        "sanitize_validation_report",
        _fake_sanitize_validation_report,
    )
    monkeypatch.setattr(
        report_step_module,
        "sanitize_diagnostic",
        _fake_sanitize_diagnostic,
    )
    monkeypatch.setattr(report_step_module, "perf_counter", lambda: 13.0)

    collector = FeedUsageCollector()
    collector.inc_input(2)
    ctx = RunReport(
        started_at=10.0,
        collector=collector,
        timings={"core": 1.25},
        run_id="run-1",
        correlation_id="corr-1",
        ingestion_diagnostics=(
            Diagnostic("WARN", code="ING", message="unsafe ingestion"),
        ),
        validation_report=original_report,
        artifact=_make_artifact(),
    )

    actual = report_step(ctx)

    assert sanitize_calls == [original_report]
    assert actual.status == "SUCCESS"
    assert actual.failed_step == ""
    assert actual.reason_code == ""
    assert actual.message == "Pipeline completed successfully"
    assert actual.validation_report is sanitized_report
    assert actual.validation_report.diagnostics == [
        sanitized_validation,
        sanitized_ingestion,
    ]
    assert actual.artifacts == (ctx.artifact,)
    assert actual.timings == {"core": 1.25, "total": 3.0}
    assert actual.usage.input_items_count == 2
    assert actual.usage.artifacts_count == 1
    assert actual.usage.processed == 2
    assert actual.usage.errors == 0
    assert actual.usage.diagnostics_count_by_severity == {
        "ERROR": 1,
        "WARN": 1,
        "INFO": 0,
    }
    assert actual.run_id == "run-1"
    assert actual.correlation_id == "corr-1"
    assert actual.error_type is None


def test_report_step_builds_failed_execution_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Finalize failure state with sanitized message and error counters.

    Returns:
        None.
    """
    original_report = ValidationReport(target="catalog", artifact_profile="profile")
    original_report.add(Diagnostic("INFO", code="VAL", message="unsafe validation"))
    sanitized_report = ValidationReport(target="catalog", artifact_profile="profile")
    sanitized_validation = Diagnostic(
        "INFO",
        code="VAL",
        message="safe validation",
    )
    sanitized_ingestion = Diagnostic(
        "ERROR",
        code="ING",
        message="safe ingestion",
    )
    sanitized_report.add(sanitized_validation)

    monkeypatch.setattr(
        report_step_module,
        "sanitize_validation_report",
        lambda report: sanitized_report,
    )
    monkeypatch.setattr(
        report_step_module,
        "sanitize_diagnostic",
        lambda diagnostic: sanitized_ingestion,
    )
    monkeypatch.setattr(
        report_step_module, "sanitize_text", lambda text: "safe:" + text
    )
    monkeypatch.setattr(report_step_module, "perf_counter", lambda: 17.0)

    collector = FeedUsageCollector()
    collector.inc_input(4)
    ctx = RunReport(
        started_at=10.0,
        collector=collector,
        timings={"publish": 0.75},
        run_id="run-2",
        correlation_id="corr-2",
        ingestion_diagnostics=(
            Diagnostic("ERROR", code="ING", message="unsafe ingestion"),
        ),
        validation_report=original_report,
    ).fail(
        failed_step="PUBLISH",
        reason_code="PUBLISH.TIMEOUT",
        exc=_WrappedError(TimeoutError("secret token")),
    )

    actual = report_step(ctx)

    assert actual.status == "FAILED"
    assert actual.failed_step == "PUBLISH"
    assert actual.reason_code == "PUBLISH.TIMEOUT"
    assert actual.message == "safe:secret token"
    assert actual.validation_report is sanitized_report
    assert actual.validation_report.diagnostics == [
        sanitized_validation,
        sanitized_ingestion,
    ]
    assert actual.artifacts == ()
    assert actual.timings == {"publish": 0.75, "total": 7.0}
    assert actual.usage.input_items_count == 4
    assert actual.usage.artifacts_count == 0
    assert actual.usage.processed == 0
    assert actual.usage.errors == 1
    assert actual.usage.diagnostics_count_by_severity == {
        "ERROR": 1,
        "WARN": 0,
        "INFO": 1,
    }
    assert actual.run_id == "run-2"
    assert actual.correlation_id == "corr-2"
    assert actual.error_type == "TimeoutError"


def test_report_step_creates_empty_report_when_validation_report_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Create an empty validation report when the context has no core report.

    Returns:
        None.
    """

    def _unexpected_sanitize(report: ValidationReport) -> ValidationReport:
        raise AssertionError("sanitize_validation_report must not be called")

    monkeypatch.setattr(
        report_step_module,
        "sanitize_validation_report",
        _unexpected_sanitize,
    )
    monkeypatch.setattr(report_step_module, "perf_counter", lambda: 11.5)

    collector = FeedUsageCollector()
    collector.inc_input(3)
    ctx = RunReport(
        started_at=10.0,
        collector=collector,
        timings={"ingestion_extract": 0.5},
    )

    actual = report_step(ctx)

    assert actual.status == "SUCCESS"
    assert actual.validation_report.target is None
    assert actual.validation_report.artifact_profile is None
    assert actual.validation_report.diagnostics == []
    assert actual.artifacts == ()
    assert actual.timings == {"ingestion_extract": 0.5, "total": 1.5}
    assert actual.usage.input_items_count == 3
    assert actual.usage.processed == 3
    assert actual.usage.artifacts_count == 0
    assert actual.usage.errors == 0
