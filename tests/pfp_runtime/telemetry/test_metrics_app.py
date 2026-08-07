"""Tests for runtime metrics app builder."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import Mock

from pfp_runtime.telemetry.metrics_app import build_metrics_app


class _FakeFastAPI:
    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs
        self.routers: list[object] = []

    def include_router(self, router: object) -> None:
        self.routers.append(router)


def test_build_metrics_app_creates_fastapi_app_and_mounts_router(
    monkeypatch,
) -> None:
    """App builder wires FastAPI instance and metrics router with forwarded args."""

    fake_fastapi = SimpleNamespace(FastAPI=_FakeFastAPI)
    mock_build_router = Mock(return_value=object())

    monkeypatch.setitem(sys.modules, "fastapi", fake_fastapi)
    monkeypatch.setattr(
        "pfp_runtime.telemetry.metrics_app.build_metrics_router",
        mock_build_router,
    )

    app = build_metrics_app(path="/internal/metrics", registry="registry")

    assert isinstance(app, _FakeFastAPI)
    assert app.kwargs == {
        "title": "PFP Metrics",
        "docs_url": None,
        "redoc_url": None,
    }
    assert app.routers == [mock_build_router.return_value]
    mock_build_router.assert_called_once_with(
        path="/internal/metrics",
        registry="registry",
    )
