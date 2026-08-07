"""Tests for built-in telemetry handler implementations."""

import importlib.util
import logging
from typing import Any

import pytest

from pfp_utils.telemetry.telemetry_handlers import (
    ConsoleTelemetryHandler,
    NoOpTelemetryHandler,
    PrometheusTelemetryHandler,
)

_PROMETHEUS_AVAILABLE = importlib.util.find_spec("prometheus_client") is not None


class _LogPipelineStub:
    def log_process(self, level, module_name, message, *args, **kwargs) -> None:
        extra = kwargs.get("extra")
        exc_info = kwargs.get("exc_info")
        logging.getLogger(module_name).log(
            level,
            message,
            *args,
            extra=extra,
            exc_info=exc_info,
        )


def _get_prometheus_client() -> Any:
    """Import prometheus_client for tests that require the optional dependency."""
    import prometheus_client  # type: ignore[import-not-found]

    return prometheus_client


def test_noop_handler() -> None:
    """Test that NoOp handler doesn't raise errors."""
    handler = NoOpTelemetryHandler()
    handler.observe_duration("stage", 1.0, {})


def test_noop_handler_inc() -> None:
    """NoOp handler inc should be callable and not raise exceptions."""
    handler = NoOpTelemetryHandler()
    handler.inc("items_processed", 1.0, {"key": "value"})


def test_console_handler_logs(caplog) -> None:
    """Console handler should emit DEBUG logs for observability."""
    handler = ConsoleTelemetryHandler(log_pipeline=_LogPipelineStub())  # type: ignore[arg-type]
    with caplog.at_level(logging.DEBUG):
        handler.observe_duration("stage", 0.5, {"key": "value"})
    assert "TELEMETRY_DURATION: stage=stage" in caplog.text


def test_console_handler_inc_logs(caplog) -> None:
    """Console handler inc should log counter updates at DEBUG level."""
    handler = ConsoleTelemetryHandler(log_pipeline=_LogPipelineStub())  # type: ignore[arg-type]
    with caplog.at_level(logging.DEBUG):
        handler.inc("items_processed", 2.0, {"key": "value"})
    assert "TELEMETRY_COUNT: metric=items_processed" in caplog.text


@pytest.mark.skipif(
    not _PROMETHEUS_AVAILABLE,
    reason="prometheus_client not installed",
)
def test_prometheus_handler_writes_stage_duration_metric() -> None:
    """Prometheus handler should record duration for allowed stages."""
    prometheus_client = _get_prometheus_client()
    registry = prometheus_client.CollectorRegistry()
    handler = PrometheusTelemetryHandler(registry=registry)

    handler.observe_duration(
        "validation",
        0.25,
        {"target": "stripe.product_feed", "mode": "FULL"},
    )

    payload = prometheus_client.generate_latest(registry).decode("utf-8")
    assert "pfp_stage_duration_seconds" in payload
    assert 'stage="validation"' in payload
    assert 'target="stripe.product_feed"' in payload
    assert 'mode="FULL"' in payload


@pytest.mark.skipif(
    not _PROMETHEUS_AVAILABLE,
    reason="prometheus_client not installed",
)
def test_prometheus_handler_ignores_unknown_stage() -> None:
    """Prometheus handler should ignore unsupported stages."""
    prometheus_client = _get_prometheus_client()
    registry = prometheus_client.CollectorRegistry()
    handler = PrometheusTelemetryHandler(registry=registry)

    handler.observe_duration(
        "unsupported_stage",
        0.1,
        {"target": "stripe.product_feed", "mode": "FULL"},
    )

    payload = prometheus_client.generate_latest(registry).decode("utf-8")
    assert 'stage="unsupported_stage"' not in payload


@pytest.mark.skipif(
    not _PROMETHEUS_AVAILABLE,
    reason="prometheus_client not installed",
)
def test_prometheus_handler_ignores_counter_increments() -> None:
    """Prometheus handler should ignore generic counter increments."""
    prometheus_client = _get_prometheus_client()
    registry = prometheus_client.CollectorRegistry()
    handler = PrometheusTelemetryHandler(registry=registry)

    handler.inc(
        "pfp_items_processed_total",
        value=2.0,
        labels={"target": "stripe.product_feed", "mode": "FULL", "stage": "total"},
    )

    payload = prometheus_client.generate_latest(registry).decode("utf-8")
    assert "pfp_items_processed_total" not in payload


@pytest.mark.skipif(
    not _PROMETHEUS_AVAILABLE,
    reason="prometheus_client not installed",
)
def test_prometheus_handler_reuses_existing_metric_for_same_default_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Repeated default-registry handlers should share one histogram collector."""
    prometheus_client = _get_prometheus_client()
    registry = prometheus_client.CollectorRegistry()
    monkeypatch.setattr(prometheus_client, "REGISTRY", registry)

    first = PrometheusTelemetryHandler()
    second = PrometheusTelemetryHandler()

    first.observe_duration(
        "validation",
        0.25,
        {"target": "stripe.product_feed", "mode": "FULL"},
    )
    second.observe_duration(
        "publish",
        0.5,
        {"target": "stripe.product_feed", "mode": "FULL"},
    )

    payload_lines = prometheus_client.generate_latest(registry).decode("utf-8").splitlines()
    assert (
        payload_lines.count(
            "# HELP pfp_stage_duration_seconds Duration of pipeline stages in seconds."
        )
        == 1
    )
    payload = "\n".join(payload_lines)
    assert 'stage="validation"' in payload
    assert 'stage="publish"' in payload


def test_prometheus_handler_requires_prometheus_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prometheus handler should raise ImportError when dependency is unavailable."""
    original_import = __import__

    def _patched_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "prometheus_client":
            raise ImportError("missing prometheus_client")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr("builtins.__import__", _patched_import)

    with pytest.raises(ImportError, match="missing prometheus_client"):
        PrometheusTelemetryHandler()
