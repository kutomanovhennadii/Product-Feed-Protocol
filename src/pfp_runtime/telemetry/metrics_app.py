"""Standalone FastAPI application exposing Prometheus metrics for PFP microservices."""

from __future__ import annotations

from typing import Any, Optional

from pfp_utils.telemetry.metrics import build_metrics_router


def build_metrics_app(*, path: str = "/metrics", registry: Optional[Any] = None) -> Any:
    """Build a standalone FastAPI application exposing /metrics for Prometheus scraping.

    Intended for use by PFP microservices that need a dedicated HTTP server.
    Mount alongside your broker consumer loop at startup::

        app = build_metrics_app()
        # run with: uvicorn pfp_runtime.telemetry.metrics_app:app --port 9090

    Args:
        path: HTTP path for the metrics endpoint. Default: "/metrics".
        registry: Optional Prometheus CollectorRegistry (useful for tests).

    Returns:
        FastAPI application instance.
    """
    from fastapi import FastAPI  # type: ignore[import-not-found]

    app = FastAPI(title="PFP Metrics", docs_url=None, redoc_url=None)
    router = build_metrics_router(path=path, registry=registry)
    app.include_router(router)
    return app
