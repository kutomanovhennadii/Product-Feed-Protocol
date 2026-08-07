"""Tests for runtime telemetry package exports."""

import pfp_runtime.telemetry as telemetry_pkg
from pfp_runtime.telemetry.metrics_app import build_metrics_app
from pfp_utils.telemetry import PrometheusTelemetryHandler
from pfp_utils.telemetry.metrics import build_metrics_router


def test_telemetry_package_reexports_public_symbols() -> None:
    """Package root exposes the approved telemetry API without wrappers."""

    assert set(telemetry_pkg.__all__) == {
        "PrometheusTelemetryHandler",
        "build_metrics_app",
        "build_metrics_router",
    }
    assert telemetry_pkg.PrometheusTelemetryHandler is PrometheusTelemetryHandler
    assert telemetry_pkg.build_metrics_app is build_metrics_app
    assert telemetry_pkg.build_metrics_router is build_metrics_router
