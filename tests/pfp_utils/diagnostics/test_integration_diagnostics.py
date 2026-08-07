"""Integration tests for the pfp_utils.diagnostics block."""

from __future__ import annotations

from typing import Any, Dict, List, cast

from pfp_utils.diagnostics import FeedUsageCollector, ValidationReport
from pfp_utils.diagnostics.diagnostic_models import Diagnostic, DiagnosticSeverity
from pfp_utils.diagnostics.diagnostic_sanitizer import sanitize_validation_report


def test_validation_report_sanitizer_and_usage_collector_work_together() -> None:
    """Diagnostics block sanitizes reports and aggregates usage counters."""

    report = ValidationReport(
        target="stripe.product_feed", artifact_profile="catalog_delta"
    )
    report.add(
        Diagnostic(
            DiagnosticSeverity.ERROR,
            code="AUTH.FAIL",
            message="Bearer secret-token token=top-secret",
            metadata={"api_key": "super-secret"},
        )
    )

    sanitized = sanitize_validation_report(report)
    collector = FeedUsageCollector()
    counted = list(collector.attach_input_counter([{"id": "SKU-1"}, {"id": "SKU-2"}]))
    collector.inc_processed(len(counted))
    collector.inc_artifacts(1)
    for diagnostic in sanitized.diagnostics:
        collector.inc_diagnostic(str(diagnostic.severity))

    usage = collector.build()

    assert sanitized is not report
    assert "secret-token" not in sanitized.diagnostics[0].message
    assert sanitized.diagnostics[0].metadata["api_key"] == "***"
    assert usage.input_items_count == 2
    assert usage.processed == 2
    assert usage.artifacts_count == 1
    assert usage.diagnostics_count_by_severity["ERROR"] == 1


def test_validation_report_normalizes_warning_severity_in_usage_counts() -> None:
    """Diagnostics block normalizes warning aliases before usage accounting."""

    report = ValidationReport(target="stripe.product_feed", artifact_profile=None)
    report.add(Diagnostic("WARNING", code="WARN.CODE", message="warned"))
    report.add(Diagnostic("ERROR", code="ERROR.CODE", message="broken"))

    sanitized = sanitize_validation_report(report)
    collector = FeedUsageCollector()
    for diagnostic in sanitized.sorted_diagnostics():
        collector.inc_diagnostic(str(diagnostic.severity))

    usage = collector.build()
    sanitized_payload = cast(Dict[str, List[Dict[str, Any]]], sanitized.to_dict())

    assert [item["severity"] for item in sanitized_payload["diagnostics"]] == [
        "ERROR",
        "WARN",
    ]
    assert usage.diagnostics_count_by_severity["WARN"] == 1
    assert usage.diagnostics_count_by_severity["ERROR"] == 1


def test_sanitize_validation_report_masks_nested_secret_metadata() -> None:
    """Diagnostics block redacts nested secret values in report metadata and text."""

    report = ValidationReport(target="stripe.product_feed", artifact_profile=None)
    report.add(
        Diagnostic(
            DiagnosticSeverity.ERROR,
            code="SECRET.FAIL",
            message="request failed at https://example.test?token=raw-secret",
            metadata={
                "nested": {"password": "raw-secret"},
                "events": [{"api_key": "nested-secret"}],
            },
        )
    )

    sanitized = sanitize_validation_report(report)
    diagnostic = sanitized.diagnostics[0]

    assert "raw-secret" not in diagnostic.message
    assert "token=***" in diagnostic.message
    assert diagnostic.metadata["nested"]["password"] == "***"
    assert diagnostic.metadata["events"][0]["api_key"] == "***"
