"""Validation helpers for flood-control filter configuration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

_SUPPORTED_MODES: Tuple[str, ...] = (
    "off",
    "context_info_suppression",
    "rate_limit",
    "deduplicate",
)

_DEFAULT_FLOOD_CONTROL_CONFIG: Dict[str, Any] = {
    "enabled": True,
    "mode": "context_info_suppression",
    "context_keys": ["item_ref"],
    "suppressed_levels": ["INFO"],
    "force_log_attr": "force_log",
    "key_fields": ["name", "levelno", "msg", "item_ref"],
    "window_seconds": 30.0,
    "max_events_per_window": 1,
    "emit_summary": False,
    "summary_level": "INFO",
    "summary_interval_seconds": 30.0,
    "max_cache_size": 10000,
}


@dataclass(frozen=True)
class FloodControlFilterConfig:
    """Normalized flood-control configuration."""

    enabled: bool
    mode: str
    context_keys: Tuple[str, ...]
    suppressed_levels: Tuple[int, ...]
    force_log_attr: str
    key_fields: Tuple[str, ...]
    window_seconds: float
    max_events_per_window: int
    emit_summary: bool
    summary_level: int
    summary_interval_seconds: float
    max_cache_size: int


def normalize_flood_control_config(
    config: Optional[Mapping[str, Any]],
) -> FloodControlFilterConfig:
    """Merge defaults and validate flood-control configuration."""
    merged_config = dict(_DEFAULT_FLOOD_CONTROL_CONFIG)
    if config is not None:
        merged_config.update(dict(config))

    mode = merged_config["mode"]
    if mode not in _SUPPORTED_MODES:
        raise ValueError("Invalid flood control mode: {0}".format(mode))

    key_fields_value = merged_config.get("key_fields")
    if key_fields_value is None:
        key_fields = tuple(_DEFAULT_FLOOD_CONTROL_CONFIG["key_fields"])
    else:
        key_fields = tuple(_normalize_string_sequence(key_fields_value, "key_fields"))

    normalized_config = FloodControlFilterConfig(
        enabled=_normalize_bool(merged_config["enabled"], "enabled"),
        mode=mode,
        context_keys=tuple(
            _normalize_string_sequence(merged_config["context_keys"], "context_keys")
        ),
        suppressed_levels=tuple(
            _normalize_levels(merged_config["suppressed_levels"], "suppressed_levels")
        ),
        force_log_attr=_normalize_non_empty_string(
            merged_config["force_log_attr"],
            "force_log_attr",
        ),
        key_fields=key_fields,
        window_seconds=_normalize_positive_float(
            merged_config["window_seconds"],
            "window_seconds",
        ),
        max_events_per_window=_normalize_positive_int(
            merged_config["max_events_per_window"],
            "max_events_per_window",
        ),
        emit_summary=_normalize_bool(
            merged_config["emit_summary"],
            "emit_summary",
        ),
        summary_level=_normalize_level(
            merged_config["summary_level"],
            "summary_level",
        ),
        summary_interval_seconds=_normalize_positive_float(
            merged_config["summary_interval_seconds"],
            "summary_interval_seconds",
        ),
        max_cache_size=_normalize_positive_int(
            merged_config["max_cache_size"],
            "max_cache_size",
        ),
    )

    if mode == "deduplicate" and not normalized_config.key_fields:
        raise ValueError("key_fields must not be empty for deduplicate mode")

    return normalized_config


def _normalize_levels(levels: Any, field_name: str) -> List[int]:
    """Normalize a sequence of log levels into numeric logging constants.

    Args:
        levels: Sequence of string or integer log levels.
        field_name: Configuration field name used in validation errors.

    Returns:
        List of normalized logging level integers.

    Raises:
        ValueError: If the supplied value is not a valid sequence of log levels.
    """
    if not isinstance(levels, Sequence) or isinstance(levels, (str, bytes)):
        raise ValueError("{0} must be a sequence of log levels".format(field_name))
    normalized_levels: List[int] = []
    for level in levels:
        normalized_levels.append(_normalize_level(level, field_name))
    return normalized_levels


def _normalize_level(level: Any, field_name: str) -> int:
    """Normalize a single log level value.

    Args:
        level: String or integer logging level.
        field_name: Configuration field name used in validation errors.

    Returns:
        Numeric logging level.

    Raises:
        ValueError: If the level cannot be interpreted by the logging module.
    """
    if isinstance(level, int):
        return level
    if not isinstance(level, str):
        raise ValueError("{0} must contain strings or integers".format(field_name))
    normalized_level = getattr(logging, level.upper(), None)
    if not isinstance(normalized_level, int):
        raise ValueError("Invalid log level in {0}: {1}".format(field_name, level))
    return normalized_level


def _normalize_string_sequence(values: Any, field_name: str) -> List[str]:
    """Normalize a sequence of non-empty strings.

    Args:
        values: Sequence candidate supplied in configuration.
        field_name: Configuration field name used in validation errors.

    Returns:
        List of validated strings.

    Raises:
        ValueError: If the value is not a sequence of non-empty strings.
    """
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise ValueError("{0} must be a sequence of strings".format(field_name))

    normalized_values: List[str] = []
    for value in values:
        normalized_values.append(_normalize_non_empty_string(value, field_name))
    return normalized_values


def _normalize_non_empty_string(value: Any, field_name: str) -> str:
    """Validate that the supplied value is a non-empty string.

    Args:
        value: Candidate value from configuration.
        field_name: Configuration field name used in validation errors.

    Returns:
        The validated string value.

    Raises:
        ValueError: If the value is not a non-empty string.
    """
    if not isinstance(value, str) or not value:
        raise ValueError("{0} must be a non-empty string".format(field_name))
    return value


def _normalize_bool(value: Any, field_name: str) -> bool:
    """Validate that the supplied value is boolean.

    Args:
        value: Candidate value from configuration.
        field_name: Configuration field name used in validation errors.

    Returns:
        The validated boolean value.

    Raises:
        ValueError: If the value is not a boolean.
    """
    if not isinstance(value, bool):
        raise ValueError("{0} must be a boolean".format(field_name))
    return value


def _normalize_positive_float(value: Any, field_name: str) -> float:
    """Validate and normalize a positive numeric value to float.

    Args:
        value: Candidate numeric value from configuration.
        field_name: Configuration field name used in validation errors.

    Returns:
        Positive float value.

    Raises:
        ValueError: If the value is not a positive number.
    """
    if not isinstance(value, (int, float)) or value <= 0:
        raise ValueError("{0} must be a positive number".format(field_name))
    return float(value)


def _normalize_positive_int(value: Any, field_name: str) -> int:
    """Validate that the supplied value is a positive integer.

    Args:
        value: Candidate integer value from configuration.
        field_name: Configuration field name used in validation errors.

    Returns:
        Positive integer value.

    Raises:
        ValueError: If the value is not a positive integer.
    """
    if not isinstance(value, int) or value <= 0:
        raise ValueError("{0} must be a positive integer".format(field_name))
    return value


__all__: List[str] = ["FloodControlFilterConfig", "normalize_flood_control_config"]
