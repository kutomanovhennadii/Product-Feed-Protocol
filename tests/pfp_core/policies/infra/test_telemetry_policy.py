"""Tests for telemetry policy."""

from unittest.mock import Mock, patch

import pytest

from pfp_core.policies.infra.telemetry_policy import TelemetryConfig, TelemetryPolicy


@patch("pfp_core.policies.infra.logging_policy.create_telemetry_handler")
def test_telemetry_policy_init(mock_create) -> None:
    """TelemetryPolicy resolves handler through logging_policy boundary."""
    mock_handler = Mock()
    mock_log_pipeline = Mock()
    mock_create.return_value = mock_handler

    config = TelemetryConfig(provider="none")
    policy = TelemetryPolicy(config, log_pipeline=mock_log_pipeline)

    mock_create.assert_called_once_with(config, log_pipeline=mock_log_pipeline)
    assert policy.handler == mock_handler


def test_telemetry_config_from_dict_preserves_provider_value() -> None:
    """Telemetry config forwards provider into both provider and handler fields."""

    assert TelemetryConfig.from_dict({}) == TelemetryConfig(
        provider="none",
        handler="none",
    )
    assert TelemetryConfig.from_dict({"provider": "Prometheus"}) == TelemetryConfig(
        provider="Prometheus",
        handler="Prometheus",
    )


def test_telemetry_config_from_dict_rejects_non_string_provider() -> None:
    """Telemetry config requires provider to be a string."""

    with pytest.raises(ValueError, match="provider must be a string"):
        TelemetryConfig.from_dict({"provider": 1})
