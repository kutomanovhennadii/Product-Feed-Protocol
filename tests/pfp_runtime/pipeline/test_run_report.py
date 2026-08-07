"""Mirror unit tests for pfp_runtime.pipeline.run_report."""

from __future__ import annotations

from pfp_runtime.pipeline.run_report import RunReport
from pfp_utils.diagnostics import FeedUsageCollector


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


def test_run_report_constructor_defaults() -> None:
    """Populate optional fields with the documented default values.

    Returns:
        None.
    """
    collector = FeedUsageCollector()

    report = RunReport(started_at=1.5, collector=collector)

    assert report.started_at == 1.5
    assert report.collector is collector
    assert report.timings == {}
    assert report.run_id is None
    assert report.correlation_id is None
    assert report.ingestion_diagnostics == ()
    assert report.validation_report is None
    assert report.artifact is None
    assert report.failed_step == ""
    assert report.reason_code == ""
    assert report.message == ""
    assert report.error_type is None


def test_fail_uses_original_exception_when_present() -> None:
    """Read failure message and error type from ``original_exc``.

    Returns:
        None.
    """
    report = RunReport(started_at=1.0, collector=FeedUsageCollector())
    wrapped = _WrappedError(TimeoutError("slow source"))

    returned = report.fail(
        failed_step="INGESTION_EXTRACT",
        reason_code="INGESTION.TIMEOUT",
        exc=wrapped,
    )

    assert returned is report
    assert report.failed_step == "INGESTION_EXTRACT"
    assert report.reason_code == "INGESTION.TIMEOUT"
    assert report.message == "slow source"
    assert report.error_type == "TimeoutError"


def test_fail_falls_back_to_exception_without_original_exc() -> None:
    """Read failure details from ``exc`` when no wrapper contract exists.

    Returns:
        None.
    """
    report = RunReport(started_at=1.0, collector=FeedUsageCollector())
    error = RuntimeError("boom")

    report.fail(
        failed_step="INTERNAL",
        reason_code="INTERNAL.ERROR",
        exc=error,
    )

    assert report.failed_step == "INTERNAL"
    assert report.reason_code == "INTERNAL.ERROR"
    assert report.message == "boom"
    assert report.error_type == "RuntimeError"
