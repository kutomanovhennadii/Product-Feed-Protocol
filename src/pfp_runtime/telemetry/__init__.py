"""Public telemetry API for PFP microservices.

Provides ready-to-use Prometheus integration:

- ``build_metrics_router`` — FastAPI router for ``/metrics`` endpoint (mount into existing app)
- ``build_metrics_app``    — standalone FastAPI app for dedicated metrics HTTP server
- ``PrometheusTelemetryHandler`` — handler selected when runtime observability
  resolves ``observability.telemetry.provider: prometheus``
"""

from pfp_runtime.telemetry.metrics_app import build_metrics_app
from pfp_utils.telemetry import PrometheusTelemetryHandler
from pfp_utils.telemetry.metrics import build_metrics_router

__all__ = [
    "PrometheusTelemetryHandler",
    "build_metrics_app",
    "build_metrics_router",
]
