"""Tests for flood-control filter configuration normalization."""

import logging

from pfp_utils.logging.filters.flood_control_filter.flood_control_filter_config_validation import (
    FloodControlFilterConfig,
    normalize_flood_control_config,
)


def test_normalize_flood_control_config_returns_typed_defaults() -> None:
    """Default normalization must return legacy-compatible typed settings."""
    config = normalize_flood_control_config({})

    assert isinstance(config, FloodControlFilterConfig)
    assert config.enabled is True
    assert config.mode == "context_info_suppression"
    assert config.context_keys == ("item_ref",)
    assert config.suppressed_levels == (logging.INFO,)
    assert config.force_log_attr == "force_log"
    assert config.key_fields == ("name", "levelno", "msg", "item_ref")


def test_normalize_flood_control_config_maps_string_levels_to_logging_constants() -> (
    None
):
    """String levels must normalize to logging module numeric constants."""
    config = normalize_flood_control_config(
        {"suppressed_levels": ["WARNING"], "summary_level": "ERROR"}
    )

    assert config.suppressed_levels == (logging.WARNING,)
    assert config.summary_level == logging.ERROR


def test_normalize_flood_control_config_rejects_invalid_log_level() -> None:
    """Normalization must fail fast on invalid log levels."""
    try:
        normalize_flood_control_config({"suppressed_levels": ["INVALID"]})
    except ValueError as error:
        assert "Invalid log level" in str(error)
    else:
        raise AssertionError("Expected ValueError for invalid log level")


def test_normalize_flood_control_config_rejects_empty_key_fields_for_deduplicate() -> (
    None
):
    """Deduplicate mode requires an explicit non-empty record key."""
    try:
        normalize_flood_control_config({"mode": "deduplicate", "key_fields": []})
    except ValueError as error:
        assert "key_fields must not be empty" in str(error)
    else:
        raise AssertionError("Expected ValueError for empty deduplicate key_fields")


def test_normalize_flood_control_config_uses_default_key_fields_when_none() -> None:
    """Missing explicit key fields must fall back to the default suppression key."""
    config = normalize_flood_control_config({"key_fields": None})

    assert config.key_fields == ("name", "levelno", "msg", "item_ref")


def test_normalize_flood_control_config_rejects_non_sequence_levels() -> None:
    """Suppressed levels must be provided as a sequence."""
    try:
        normalize_flood_control_config({"suppressed_levels": "INFO"})
    except ValueError as error:
        assert "suppressed_levels must be a sequence of log levels" in str(error)
    else:
        raise AssertionError("Expected ValueError for invalid suppressed_levels")


def test_normalize_flood_control_config_accepts_numeric_log_levels() -> None:
    """Numeric log levels must be preserved during normalization."""
    config = normalize_flood_control_config(
        {"suppressed_levels": [logging.DEBUG], "summary_level": logging.WARNING}
    )

    assert config.suppressed_levels == (logging.DEBUG,)
    assert config.summary_level == logging.WARNING


def test_normalize_flood_control_config_rejects_non_string_level_value() -> None:
    """Non-string and non-integer log levels must be rejected."""
    try:
        normalize_flood_control_config({"summary_level": object()})
    except ValueError as error:
        assert "summary_level must contain strings or integers" in str(error)
    else:
        raise AssertionError("Expected ValueError for invalid summary_level")


def test_normalize_flood_control_config_rejects_invalid_context_keys_type() -> None:
    """Context keys must be provided as a sequence of strings."""
    try:
        normalize_flood_control_config({"context_keys": "item_ref"})
    except ValueError as error:
        assert "context_keys must be a sequence of strings" in str(error)
    else:
        raise AssertionError("Expected ValueError for invalid context_keys")


def test_normalize_flood_control_config_rejects_empty_force_log_attr() -> None:
    """Force-log attribute name must be a non-empty string."""
    try:
        normalize_flood_control_config({"force_log_attr": ""})
    except ValueError as error:
        assert "force_log_attr must be a non-empty string" in str(error)
    else:
        raise AssertionError("Expected ValueError for empty force_log_attr")


def test_normalize_flood_control_config_rejects_non_boolean_enabled() -> None:
    """Enabled flag must be a boolean value."""
    try:
        normalize_flood_control_config({"enabled": 1})
    except ValueError as error:
        assert "enabled must be a boolean" in str(error)
    else:
        raise AssertionError("Expected ValueError for invalid enabled flag")


def test_normalize_flood_control_config_rejects_non_positive_window_seconds() -> None:
    """Window size must be a positive numeric value."""
    try:
        normalize_flood_control_config({"window_seconds": 0})
    except ValueError as error:
        assert "window_seconds must be a positive number" in str(error)
    else:
        raise AssertionError("Expected ValueError for invalid window_seconds")


def test_normalize_flood_control_config_rejects_non_positive_max_events() -> None:
    """Max events per window must be a positive integer."""
    try:
        normalize_flood_control_config({"max_events_per_window": 0})
    except ValueError as error:
        assert "max_events_per_window must be a positive integer" in str(error)
    else:
        raise AssertionError("Expected ValueError for invalid max_events_per_window")
