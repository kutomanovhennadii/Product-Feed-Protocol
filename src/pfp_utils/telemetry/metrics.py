"""FastAPI router exposing Prometheus metrics endpoint."""

from __future__ import annotations

from typing import Any, Optional

from pfp_utils.telemetry.telemetry_handlers import _import_prometheus


def build_metrics_router(
    *, path: str = "/metrics", registry: Optional[Any] = None
) -> Any:
    """Build FastAPI router exposing Prometheus metrics endpoint.

    Args:
        path: HTTP path for metrics endpoint.
        registry: Optional Prometheus collector registry.

    Returns:
        Configured FastAPI APIRouter.

    Raises:
        ImportError: If FastAPI or prometheus_client are not installed.
    """
    from fastapi import APIRouter, Response  # type: ignore[import-not-found]

    prometheus_client = _import_prometheus()
    metrics_registry = prometheus_client.REGISTRY if registry is None else registry

    router = APIRouter()

    @router.get(path)
    def metrics() -> Response:
        payload = prometheus_client.generate_latest(metrics_registry)
        return Response(
            content=payload,
            media_type=prometheus_client.CONTENT_TYPE_LATEST,
        )

    return router


__all__ = ["build_metrics_router"]
