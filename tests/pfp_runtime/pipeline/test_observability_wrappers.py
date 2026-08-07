"""Mirror tests for pfp_runtime.pipeline.observability_wrappers."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import pytest

from pfp_runtime.pipeline.observability_wrappers import (
    emit_step_telemetry,
    record_timing,
)


class _TelemetryStub:
    """Collect duration telemetry emitted by wrapper helpers.

    Returns:
        None.
    """

    def __init__(self) -> None:
        """Initialize the in-memory telemetry sink.

        Returns:
            None.
        """
        self.calls: List[Tuple[str, float, Dict[str, str]]] = []

    def observe_duration(
        self,
        stage: str,
        duration: float,
        labels: Dict[str, str],
    ) -> None:
        """Record a duration observation from the wrapper.

        Args:
            stage: Public telemetry stage name.
            duration: Measured elapsed duration.
            labels: Metric labels emitted with the metric.

        Returns:
            None.
        """
        self.calls.append((stage, duration, labels))

    def inc(
        self,
        name: str,
        value: float = 1.0,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Accept counter telemetry calls required by the protocol.

        Args:
            name: Counter metric name.
            value: Counter increment value.
            labels: Optional metric labels.

        Returns:
            None.
        """
        del name, value, labels


def test_record_timing_returns_result_and_updates_timings() -> None:
    """Return the action result and store elapsed time under the given key.

    Returns:
        None.
    """
    timings: Dict[str, float] = {}

    result = record_timing(timings, "core", lambda: "ok")

    assert result == "ok"
    assert "core" in timings
    assert timings["core"] >= 0.0


def test_record_timing_updates_timings_when_action_raises() -> None:
    """Store elapsed time even when the wrapped action raises an exception.

    Returns:
        None.
    """
    timings: Dict[str, float] = {}

    with pytest.raises(RuntimeError, match="boom"):
        record_timing(
            timings,
            "publish",
            lambda: (_ for _ in ()).throw(RuntimeError("boom")),
        )

    assert "publish" in timings
    assert timings["publish"] >= 0.0


def test_emit_step_telemetry_maps_core_stage_to_validation() -> None:
    """Map internal core stage names to the public validation metric stage.

    Returns:
        None.
    """
    telemetry = _TelemetryStub()
    labels = {"target": "stripe.product_feed", "stage": "total"}

    result = emit_step_telemetry(
        telemetry,
        labels,
        "core",
        lambda: 42,
    )

    assert result == 42
    assert len(telemetry.calls) == 1
    stage, duration, call_labels = telemetry.calls[0]
    assert stage == "validation"
    assert duration >= 0.0
    assert call_labels == labels
    assert call_labels is not labels


def test_emit_step_telemetry_records_publish_stage_on_exception() -> None:
    """Emit publish telemetry even when the wrapped action raises an error.

    Returns:
        None.
    """
    telemetry = _TelemetryStub()

    with pytest.raises(RuntimeError, match="boom"):
        emit_step_telemetry(
            telemetry,
            {"target": "stripe.product_feed", "stage": "total"},
            "publish",
            lambda: (_ for _ in ()).throw(RuntimeError("boom")),
        )

    assert len(telemetry.calls) == 1
    stage, duration, labels = telemetry.calls[0]
    assert stage == "publish"
    assert duration >= 0.0
    assert labels["target"] == "stripe.product_feed"


def test_emit_step_telemetry_skips_internal_only_stages() -> None:
    """Skip telemetry emission for stages without a public mapping.

    Returns:
        None.
    """
    telemetry = _TelemetryStub()

    result = emit_step_telemetry(
        telemetry,
        {"target": "stripe.product_feed", "stage": "total"},
        "ingestion_extract",
        lambda: "ok",
    )

    assert result == "ok"
    assert telemetry.calls == []
