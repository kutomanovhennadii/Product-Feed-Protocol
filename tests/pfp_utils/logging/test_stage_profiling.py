"""Tests for stage profiling helpers."""

from unittest.mock import Mock

import pytest

from pfp_utils.logging import LogContext
from pfp_utils.logging.stage_profiling import profile_stage
from pfp_utils.telemetry import TelemetryHandler


def test_profile_stage_decorator(monkeypatch) -> None:
    """Test profiling decorator functionality."""
    mock_telemetry = Mock(spec=TelemetryHandler)
    mock_log_pipeline = Mock()
    perf_values = iter([10.0, 10.02])
    monkeypatch.setattr(
        "pfp_utils.logging.stage_profiling.time.perf_counter",
        lambda: next(perf_values),
    )

    @profile_stage("test_stage")
    def profiled_func(telemetry=None, log_pipeline=None):
        return "result"

    result = profiled_func(telemetry=mock_telemetry, log_pipeline=mock_log_pipeline)

    assert result == "result"
    mock_telemetry.observe_duration.assert_called_once()

    args = mock_telemetry.observe_duration.call_args[0]
    assert args[0] == "test_stage"
    assert args[1] == pytest.approx(0.02)


def test_profile_stage_without_telemetry() -> None:
    """Test profiling without telemetry handler (should log only)."""
    mock_log_pipeline = Mock()

    @profile_stage("test_stage")
    def profiled_func(telemetry=None, log_pipeline=None):
        return "ok"

    assert profiled_func(log_pipeline=mock_log_pipeline) == "ok"


def test_profile_stage_extracts_labels_from_context() -> None:
    """Test that profile_stage extracts labels from LogContext."""
    mock_telemetry = Mock(spec=TelemetryHandler)
    mock_log_pipeline = Mock()

    @profile_stage("labeled_stage")
    def profiled_func(telemetry=None, log_pipeline=None):
        return "done"

    with LogContext(
        target="STRIPE",
        artifact_profile="catalog_snapshot",
        policy_name="shipping",
    ):
        profiled_func(telemetry=mock_telemetry, log_pipeline=mock_log_pipeline)

    mock_telemetry.observe_duration.assert_called_once()
    args = mock_telemetry.observe_duration.call_args[0]

    stage, duration, labels = args
    assert stage == "labeled_stage"
    assert labels.get("target") == "STRIPE"
    assert labels.get("artifact_profile") == "catalog_snapshot"
    assert labels.get("policy_name") == "shipping"


def test_profile_stage_with_empty_context() -> None:
    """Test profiling with no context set (labels should be empty dict)."""
    mock_telemetry = Mock(spec=TelemetryHandler)
    mock_log_pipeline = Mock()

    @profile_stage("no_context_stage")
    def profiled_func(telemetry=None, log_pipeline=None):
        return "result"

    profiled_func(telemetry=mock_telemetry, log_pipeline=mock_log_pipeline)

    mock_telemetry.observe_duration.assert_called_once()
    args = mock_telemetry.observe_duration.call_args[0]

    stage, duration, labels = args
    assert stage == "no_context_stage"
    assert labels == {}


def test_profile_stage_requires_log_pipeline_keyword_argument() -> None:
    """Decorator raises when wrapped call omits mandatory log_pipeline keyword."""

    @profile_stage("missing_log_pipeline")
    def profiled_func(**kwargs):
        return kwargs

    with pytest.raises(TypeError, match="log_pipeline"):
        profiled_func()
