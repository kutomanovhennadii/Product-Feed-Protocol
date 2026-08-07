"""Public flood-control filter implementation."""

from __future__ import annotations

import logging
import time
from typing import Any, List, Mapping, Optional, Tuple

from pfp_utils.logging.filters.flood_control_filter.flood_control_filter_config_validation import (
    FloodControlFilterConfig,
    normalize_flood_control_config,
)
from pfp_utils.logging.filters.flood_control_filter.flood_control_filter_strategies import (
    FilterStrategy,
    build_filter_strategy,
)


def _get_current_time() -> float:
    """Return the current monotonic clock value for strategy timing."""
    return time.monotonic()


def _get_summary_logger(name: str) -> logging.Logger:
    """Return the logger instance used for synthetic summary records."""
    return logging.getLogger(name)


class FloodControlFilter(logging.Filter):
    """Suppress INFO logs when item_ref is in context, unless force_log=True."""

    def __init__(self, config: Optional[Mapping[str, Any]] = None) -> None:
        """Initialize the flood-control filter with validated settings.

        Args:
            config: Optional mapping with flood-control settings. Missing keys are
                filled with defaults that preserve the legacy behavior.

        Raises:
            ValueError: If the supplied configuration contains invalid values.
        """
        super().__init__()
        self._config: FloodControlFilterConfig = normalize_flood_control_config(config)
        self._filter_strategy: FilterStrategy = build_filter_strategy(
            config=self._config,
            get_current_time=_get_current_time,
            get_summary_logger=_get_summary_logger,
        )

    @property
    def enabled(self) -> bool:
        """Return whether flood control is enabled."""
        return self._config.enabled

    @property
    def mode(self) -> str:
        """Return the selected flood-control strategy mode."""
        return self._config.mode

    @property
    def context_keys(self) -> Tuple[str, ...]:
        """Return context keys that activate flood control."""
        return self._config.context_keys

    @property
    def suppressed_levels(self) -> Tuple[int, ...]:
        """Return log levels that may be suppressed by the strategy."""
        return self._config.suppressed_levels

    @property
    def force_log_attr(self) -> str:
        """Return the record attribute name that bypasses flood control."""
        return self._config.force_log_attr

    @property
    def key_fields(self) -> Tuple[str, ...]:
        """Return record fields used to build suppression keys."""
        return self._config.key_fields

    @property
    def window_seconds(self) -> float:
        """Return the active suppression window size in seconds."""
        return self._config.window_seconds

    @property
    def max_events_per_window(self) -> int:
        """Return the maximum events allowed per rate-limit window."""
        return self._config.max_events_per_window

    @property
    def emit_summary(self) -> bool:
        """Return whether suppressed-record summaries are enabled."""
        return self._config.emit_summary

    @property
    def summary_level(self) -> int:
        """Return the log level used for synthetic summary records."""
        return self._config.summary_level

    @property
    def summary_interval_seconds(self) -> float:
        """Return the minimum interval between emitted summaries."""
        return self._config.summary_interval_seconds

    @property
    def max_cache_size(self) -> int:
        """Return the maximum cache size for stateful suppression modes."""
        return self._config.max_cache_size

    def filter(self, record: logging.LogRecord) -> bool:
        """Decide whether the log record should pass through the filter.

        Args:
            record: Log record that may be suppressed during item-level loops.

        Returns:
            True when the record should be emitted, otherwise False.
        """
        if getattr(record, self.force_log_attr, False):
            return True
        return self._filter_strategy(record)


def build_flood_control_filter(config: Mapping[str, Any]) -> FloodControlFilter:
    """Build a FloodControlFilter instance from configuration.

    Args:
        config: Flood-control settings dictionary.

    Returns:
        A new FloodControlFilter configured with the supplied settings.
    """
    return FloodControlFilter(config=config)


__all__: List[str] = ["FloodControlFilter", "build_flood_control_filter"]
