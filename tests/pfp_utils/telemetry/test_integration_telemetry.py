"""Integration tests for the pfp_utils.telemetry block."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

prometheus_client = pytest.importorskip(
    "prometheus_client", reason="prometheus extra not installed"
)


def test_telemetry_factory_builds_console_handler(capsys) -> None:
    """Telemetry block builds the real console handler and emits log output.

    Args:
        capsys: Pytest capture fixture used to inspect emitted log output.
    """

    from pfp_utils.logging import build_log_pipeline
    from pfp_utils.telemetry.telemetry_factory import create_telemetry_handler
    from pfp_utils.telemetry.telemetry_handlers import ConsoleTelemetryHandler

    handler = create_telemetry_handler(
        SimpleNamespace(enabled=True, handler="console"),
        log_pipeline=build_log_pipeline("DEBUG", "TEXT", {}),
    )
    handler.observe_duration(
        "publish",
        0.25,
        {"target": "stripe.product_feed", "mode": "catalog_delta"},
    )

    captured = capsys.readouterr()

    assert isinstance(handler, ConsoleTelemetryHandler)
    assert "TELEMETRY_DURATION" in captured.out
    assert "stage=publish" in captured.out


def test_telemetry_factory_returns_noop_when_disabled() -> None:
    """Telemetry block returns a no-op handler when telemetry is disabled."""

    from pfp_utils.logging import build_log_pipeline
    from pfp_utils.telemetry.telemetry_factory import create_telemetry_handler
    from pfp_utils.telemetry.telemetry_handlers import NoOpTelemetryHandler

    handler = create_telemetry_handler(
        SimpleNamespace(enabled=False, handler="console"),
        log_pipeline=build_log_pipeline("INFO", "TEXT", {}),
    )

    assert isinstance(handler, NoOpTelemetryHandler)


def test_prometheus_handler_records_metrics_in_custom_registry() -> None:
    """Telemetry block writes Prometheus histogram metrics into the supplied registry."""

    from pfp_utils.telemetry.telemetry_handlers import PrometheusTelemetryHandler

    registry = prometheus_client.CollectorRegistry()
    handler = PrometheusTelemetryHandler(registry=registry)
    handler.observe_duration(
        "publish",
        0.25,
        {"target": "stripe.product_feed", "mode": "catalog_delta"},
    )

    payload = prometheus_client.generate_latest(registry).decode("utf-8")

    assert (
        'pfp_stage_duration_seconds_sum{mode="catalog_delta",stage="publish",target="stripe.product_feed"} 0.25'
        in payload
    )
    assert (
        'pfp_stage_duration_seconds_count{mode="catalog_delta",stage="publish",target="stripe.product_feed"} 1.0'
        in payload
    )
