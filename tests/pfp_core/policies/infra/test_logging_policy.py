"""Tests for logging policy."""

from unittest.mock import patch

import pytest

from pfp_core.policies.infra.logging_policy import LoggingConfig, LoggingPolicy


@patch("pfp_core.policies.infra.logging_policy.build_log_pipeline")
def test_logging_policy_apply(mock_build_pipeline) -> None:
    """LoggingPolicy builds and installs a LogPipeline from level and format."""
    mock_pipeline = mock_build_pipeline.return_value
    config = LoggingConfig(level="DEBUG", format="JSON")
    policy = LoggingPolicy(config)
    policy.apply()
    mock_build_pipeline.assert_called_once_with("DEBUG", "JSON", {})
    mock_pipeline.install.assert_called_once_with()


def test_logging_config_from_dict_validates_supported_values() -> None:
    """Config loader accepts valid values and preserves explicit casing."""

    config = LoggingConfig.from_dict({"level": "ERROR", "format": "Text"})

    assert config == LoggingConfig(level="ERROR", format="Text")


def test_logging_config_from_dict_rejects_invalid_values() -> None:
    """Config loader rejects invalid level and format payloads."""

    with pytest.raises(ValueError, match="level must be a string"):
        LoggingConfig.from_dict({"level": 1})

    with pytest.raises(ValueError, match="Invalid log level"):
        LoggingConfig.from_dict({"level": "TRACE"})

    with pytest.raises(ValueError, match="format must be a string"):
        LoggingConfig.from_dict({"format": 1})

    with pytest.raises(ValueError, match="Invalid log format"):
        LoggingConfig.from_dict({"format": "yaml"})
