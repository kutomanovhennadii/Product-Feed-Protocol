"""Built-in telemetry handler implementations."""

import logging
import weakref
from typing import Any, Dict, Optional, Set, Tuple

from pfp_utils.logging import LogPipeline


class NoOpTelemetryHandler:
    """Telemetry handler that does nothing."""

    def observe_duration(
        self, stage: str, duration: float, labels: Dict[str, str]
    ) -> None:
        del stage, duration, labels

    def inc(
        self,
        name: str,
        value: float = 1.0,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        del name, value, labels


class ConsoleTelemetryHandler:
    """Telemetry handler that logs metrics to the logger."""

    def __init__(self, *, log_pipeline: LogPipeline) -> None:
        self._log_pipeline = log_pipeline

    def _debug(self, message: str, *args: Any) -> None:
        self._log_pipeline.log_process(logging.DEBUG, __name__, message, *args)

    def observe_duration(
        self, stage: str, duration: float, labels: Dict[str, str]
    ) -> None:
        self._debug(
            "TELEMETRY_DURATION: stage=%s duration=%.4fs labels=%s",
            stage,
            duration,
            labels,
        )

    def inc(
        self,
        name: str,
        value: float = 1.0,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        self._debug(
            "TELEMETRY_COUNT: metric=%s value=%s labels=%s",
            name,
            value,
            labels,
        )


_ALLOWED_STAGES: Set[str] = {
    "normalization",
    "validation",
    "mapping",
    "serialization",
    "publish",
}

_STAGE_DURATION_BY_REGISTRY = weakref.WeakKeyDictionary()


def _import_prometheus() -> Any:
    """Import prometheus_client lazily."""
    import prometheus_client  # type: ignore[import-not-found]

    return prometheus_client


def _extract_metric_labels(labels: Optional[Dict[str, str]]) -> Tuple[str, str, str]:
    """Extract stable target/mode/stage labels for metrics."""
    raw_labels = labels or {}
    target = str(raw_labels.get("target", "unknown"))
    mode = str(raw_labels.get("mode", "unknown"))
    stage = str(raw_labels.get("stage", "total"))
    return target, mode, stage


def _get_stage_duration_metric(registry: Any) -> Any:
    """Return the shared stage-duration histogram for the supplied registry."""
    metric = _STAGE_DURATION_BY_REGISTRY.get(registry)
    if metric is not None:
        return metric

    prometheus_client = _import_prometheus()
    metric = prometheus_client.Histogram(
        "pfp_stage_duration_seconds",
        "Duration of pipeline stages in seconds.",
        labelnames=("stage", "target", "mode"),
        registry=registry,
    )
    _STAGE_DURATION_BY_REGISTRY[registry] = metric
    return metric


class PrometheusTelemetryHandler:
    """Prometheus-backed implementation of TelemetryHandler."""

    def __init__(self, registry: Optional[Any] = None) -> None:
        prometheus_client = _import_prometheus()
        active_registry = prometheus_client.REGISTRY if registry is None else registry
        self._stage_duration = _get_stage_duration_metric(active_registry)

    def observe_duration(
        self, stage: str, duration: float, labels: Dict[str, str]
    ) -> None:
        """Record stage duration metric."""
        if stage not in _ALLOWED_STAGES:
            return
        target, mode, _ = _extract_metric_labels(labels)
        self._stage_duration.labels(stage=stage, target=target, mode=mode).observe(
            duration
        )

    def inc(
        self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Ignore generic counter increments.

        Business usage accounting is owned by FeedUsageCollector and does not
        belong in PrometheusTelemetryHandler. The method remains as a no-op to
        preserve the TelemetryHandler protocol for existing callers.
        """
        del name, value, labels


__all__ = [
    "ConsoleTelemetryHandler",
    "NoOpTelemetryHandler",
    "PrometheusTelemetryHandler",
]
