"""Tests for telemetry metrics router helpers."""

import importlib.util
import sys
import types
from typing import Any, List, cast

import pytest

from pfp_utils.telemetry.metrics import build_metrics_router
from pfp_utils.telemetry.telemetry_handlers import PrometheusTelemetryHandler

_PROMETHEUS_AVAILABLE = importlib.util.find_spec("prometheus_client") is not None


def _get_prometheus_client() -> Any:
    """Import prometheus_client for tests that require the optional dependency."""
    import prometheus_client  # type: ignore[import-not-found]

    return prometheus_client


def _install_fake_fastapi(monkeypatch: pytest.MonkeyPatch) -> None:
    """Install a lightweight fake fastapi module for router tests."""

    class _FakeResponse:
        def __init__(self, content: Any, media_type: str) -> None:
            self.content = content
            self.media_type = media_type

    class _FakeRoute:
        def __init__(self, path: str, endpoint: Any) -> None:
            self.path = path
            self.endpoint = endpoint

    class _FakeRouter:
        def __init__(self) -> None:
            self.routes: List[Any] = []

        def get(self, path: str) -> Any:
            def _decorator(func: Any) -> Any:
                self.routes.append(_FakeRoute(path, func))
                return func

            return _decorator

    fake_fastapi = cast(Any, types.ModuleType("fastapi"))
    fake_fastapi.APIRouter = _FakeRouter
    fake_fastapi.Response = _FakeResponse
    monkeypatch.setitem(sys.modules, "fastapi", fake_fastapi)


@pytest.mark.skipif(
    not _PROMETHEUS_AVAILABLE,
    reason="prometheus_client not installed",
)
def test_build_metrics_router_returns_metrics_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return Prometheus metrics payload from the configured router endpoint."""
    prometheus_client = _get_prometheus_client()
    _install_fake_fastapi(monkeypatch)

    registry = prometheus_client.CollectorRegistry()
    handler = PrometheusTelemetryHandler(registry=registry)
    handler.observe_duration(
        "validation",
        0.25,
        {"target": "stripe.product_feed", "mode": "FULL"},
    )

    router = build_metrics_router(path="/metrics", registry=registry)

    assert len(router.routes) == 1
    response = router.routes[0].endpoint()
    assert response.media_type == prometheus_client.CONTENT_TYPE_LATEST
    assert b"pfp_stage_duration_seconds" in response.content


@pytest.mark.skipif(
    not _PROMETHEUS_AVAILABLE,
    reason="prometheus_client not installed",
)
def test_build_metrics_router_uses_custom_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Register the metrics endpoint on a custom HTTP path."""
    prometheus_client = _get_prometheus_client()
    _install_fake_fastapi(monkeypatch)

    router = build_metrics_router(
        path="/custom-metrics",
        registry=prometheus_client.CollectorRegistry(),
    )

    assert len(router.routes) == 1
    assert router.routes[0].path == "/custom-metrics"


def test_build_metrics_router_raises_import_error_without_fastapi(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Raise ImportError when FastAPI dependency is missing at call site."""
    original_import = __import__

    def _patched_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "fastapi":
            raise ImportError("fastapi missing")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr("builtins.__import__", _patched_import)

    with pytest.raises(ImportError):
        build_metrics_router()
