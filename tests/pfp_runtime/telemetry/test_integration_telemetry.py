"""Integration tests for the pfp_runtime.telemetry block."""

from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi", reason="fastapi extra not installed")
prometheus_client = pytest.importorskip(
    "prometheus_client", reason="prometheus extra not installed"
)


def test_metrics_router_serves_custom_registry_payload() -> None:
    """Telemetry router serves metrics from the supplied CollectorRegistry."""

    from fastapi.testclient import TestClient

    from pfp_runtime.telemetry import build_metrics_router

    registry = prometheus_client.CollectorRegistry()
    counter = prometheus_client.Counter(
        "pfp_runtime_test_metric_total",
        "Runtime integration metric.",
        registry=registry,
    )
    counter.inc()

    app = fastapi.FastAPI()
    app.include_router(
        build_metrics_router(path="/internal/metrics", registry=registry)
    )

    response = TestClient(app).get("/internal/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        prometheus_client.CONTENT_TYPE_LATEST
    )
    assert "pfp_runtime_test_metric_total" in response.text
    assert "pfp_runtime_test_metric_total 1.0" in response.text


def test_metrics_app_mounts_router_at_custom_path() -> None:
    """Telemetry app mounts the metrics router on the requested HTTP path."""

    from fastapi.testclient import TestClient

    from pfp_runtime.telemetry import build_metrics_app

    registry = prometheus_client.CollectorRegistry()
    gauge = prometheus_client.Gauge(
        "pfp_runtime_test_gauge",
        "Runtime integration gauge.",
        registry=registry,
    )
    gauge.set(2)

    app = build_metrics_app(path="/internal/metrics", registry=registry)
    response = TestClient(app).get("/internal/metrics")

    assert response.status_code == 200
    assert app.title == "PFP Metrics"
    assert "pfp_runtime_test_gauge 2.0" in response.text


def test_metrics_app_disables_docs_and_redoc_routes() -> None:
    """Telemetry app disables interactive documentation endpoints by default."""

    from fastapi.testclient import TestClient

    from pfp_runtime.telemetry import build_metrics_app

    app = build_metrics_app()
    client = TestClient(app)

    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
