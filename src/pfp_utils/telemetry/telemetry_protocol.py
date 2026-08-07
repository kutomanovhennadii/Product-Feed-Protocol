"""Telemetry protocol contract for observability."""

from typing import Dict, Optional, Protocol


class TelemetryHandler(Protocol):
    """Interface for telemetry handlers (e.g., Prometheus integration)."""

    def observe_duration(
        self, stage: str, duration: float, labels: Dict[str, str]
    ) -> None:
        """Record duration of a processing stage."""

    def inc(
        self,
        name: str,
        value: float = 1.0,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Increment a counter metric."""


__all__ = [
    "TelemetryHandler",
]
