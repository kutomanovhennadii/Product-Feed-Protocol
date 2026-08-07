"""Observability wrappers for timing and telemetry around pipeline steps."""

from __future__ import annotations

from time import perf_counter
from typing import Callable, Dict, List, Mapping, Optional, TypeVar

from pfp_utils.telemetry import TelemetryHandler

T = TypeVar("T")


def record_timing(
    timings: Dict[str, float],
    step_name: str,
    action: Callable[[], T],
) -> T:
    """Execute an action and persist its elapsed duration.

    Args:
        timings: Mutable mapping updated with the measured duration.
        step_name: Stable internal step name used as the timings key.
        action: Callable to execute.

    Returns:
        Result returned by the action.
    """
    started = perf_counter()
    try:
        return action()
    finally:
        timings[step_name] = perf_counter() - started


def emit_step_telemetry(
    telemetry: TelemetryHandler,
    metric_labels: Mapping[str, str],
    stage: str,
    action: Callable[[], T],
) -> T:
    """Execute an action and emit duration telemetry for public stages.

    Args:
        telemetry: Runtime telemetry handler used to publish durations.
        metric_labels: Stable low-cardinality labels attached to the metric.
        stage: Internal runner stage name.
        action: Callable to execute.

    Returns:
        Result returned by the action.
    """
    started = perf_counter()
    try:
        return action()
    finally:
        public_stage = _resolve_telemetry_stage(stage)
        if public_stage is not None:
            telemetry.observe_duration(
                public_stage,
                perf_counter() - started,
                dict(metric_labels),
            )


def _resolve_telemetry_stage(stage: str) -> Optional[str]:
    """Map internal runner stages to public telemetry stage names.

    Args:
        stage: Internal runner stage name.

    Returns:
        Public telemetry stage name, or None when no metric should be emitted.
    """
    if stage == "core":
        return "validation"
    if stage == "publish":
        return "publish"
    return None


__all__: List[str] = [
    "emit_step_telemetry",
    "record_timing",
]
