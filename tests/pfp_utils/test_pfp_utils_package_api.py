"""Contract tests for package-level pfp_utils public API."""

from __future__ import annotations

import pfp_utils as utils_pkg
from pfp_utils.diagnostics import Diagnostic, FeedUsage, FeedUsageCollector
from pfp_utils.diagnostics.diagnostic_sanitizer import sanitize_diagnostic
from pfp_utils.logging import LogPipeline, build_log_pipeline
from pfp_utils.sanitization import sanitize_text
from pfp_utils.security import SecretRef


def test_package_api_exposes_expected_symbols() -> None:
    """Package root exposes exactly the approved stable public surface."""

    expected_symbols = {
        "ConsoleTelemetryHandler",
        "Diagnostic",
        "DiagnosticSeverity",
        "FeedUsage",
        "FeedUsageCollector",
        "LogContext",
        "LogPipeline",
        "NoOpTelemetryHandler",
        "PrometheusTelemetryHandler",
        "ResolvedSecret",
        "SecretRef",
        "SecretResolutionError",
        "TelemetryHandler",
        "ValidationReport",
        "build_log_pipeline",
        "build_metrics_router",
        "create_telemetry_handler",
        "get_context",
        "profile_stage",
        "resolve_secret",
        "sanitize_diagnostic",
        "sanitize_mapping",
        "sanitize_text",
        "sanitize_validation_report",
    }

    assert set(utils_pkg.__all__) == expected_symbols

    for symbol in expected_symbols:
        assert hasattr(utils_pkg, symbol)


def test_package_api_reexports_canonical_symbols() -> None:
    """Package root re-exports canonical leaf symbols without wrapping them."""

    assert utils_pkg.Diagnostic is Diagnostic
    assert utils_pkg.FeedUsage is FeedUsage
    assert utils_pkg.FeedUsageCollector is FeedUsageCollector
    assert utils_pkg.LogPipeline is LogPipeline
    assert utils_pkg.build_log_pipeline is build_log_pipeline
    assert utils_pkg.SecretRef is SecretRef
    assert utils_pkg.sanitize_text is sanitize_text
    assert utils_pkg.sanitize_diagnostic is sanitize_diagnostic


def test_package_api_exposes_step_7b_prime_symbols() -> None:
    """Package root exposes Prometheus handler and metrics router after step 7.B′.2."""

    assert hasattr(utils_pkg, "PrometheusTelemetryHandler")
    assert hasattr(utils_pkg, "build_metrics_router")
