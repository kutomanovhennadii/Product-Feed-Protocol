"""Strategy implementations for flood-control filter runtime."""

from __future__ import annotations

import logging
from collections import deque
from threading import RLock
from typing import Any, Callable, Deque, Dict, List, Mapping, Optional, Tuple

from pfp_utils.logging.filters.flood_control_filter.flood_control_filter_config_validation import (
    FloodControlFilterConfig,
)
from pfp_utils.logging.log_context import get_context

FloodControlKey = Tuple[Any, ...]
FilterStrategy = Callable[[logging.LogRecord], bool]
SummaryLoggerFactory = Callable[[str], logging.Logger]
TimeProvider = Callable[[], float]

_SUMMARY_MESSAGE_TEMPLATE = (
    "Flood control suppressed {count} records in mode={mode} for key={key}"
)


def build_filter_strategy(
    config: FloodControlFilterConfig,
    get_current_time: TimeProvider,
    get_summary_logger: SummaryLoggerFactory,
) -> FilterStrategy:
    """Build the runtime strategy selected by the normalized configuration."""
    if not config.enabled or config.mode == "off":
        return _AllowAllStrategy()

    summary_emitter: Optional[_SummaryEmitter] = None
    if config.emit_summary:
        summary_emitter = _SummaryEmitter(
            config=config,
            get_summary_logger=get_summary_logger,
        )

    if config.mode == "context_info_suppression":
        return _ContextSuppressionStrategy(
            config=config,
            summary_emitter=summary_emitter,
            get_current_time=get_current_time,
        )
    if config.mode == "rate_limit":
        return _RateLimitStrategy(
            config=config,
            summary_emitter=summary_emitter,
            get_current_time=get_current_time,
        )
    return _DeduplicateStrategy(
        config=config,
        summary_emitter=summary_emitter,
        get_current_time=get_current_time,
    )


class _AllowAllStrategy:
    """Strategy that always allows records to pass through."""

    def __call__(self, record: logging.LogRecord) -> bool:
        """Allow the supplied record without performing any checks.

        Args:
            record: Log record being filtered.

        Returns:
            Always True.
        """
        return True


class _ContextAwareStrategy:
    """Base strategy with shared context and summary-handling helpers."""

    def __init__(
        self,
        config: FloodControlFilterConfig,
        summary_emitter: Optional["_SummaryEmitter"],
        get_current_time: TimeProvider,
    ) -> None:
        """Store shared configuration used by context-aware strategies.

        Args:
            config: Normalized flood-control configuration.
            summary_emitter: Optional summary emitter for suppressed records.
            get_current_time: Monotonic clock provider.
        """
        self._context_keys = config.context_keys
        self._suppressed_levels = config.suppressed_levels
        self._key_fields = config.key_fields
        self._summary_emitter = summary_emitter
        self._get_current_time = get_current_time

    def _get_active_context(
        self,
        record: logging.LogRecord,
    ) -> Optional[Mapping[str, Any]]:
        """Return active logging context when the record is suppressible.

        Args:
            record: Log record being filtered.

        Returns:
            Active context mapping when suppression may apply, otherwise None.
        """
        if record.levelno not in self._suppressed_levels:
            return None
        context = get_context()
        if not _is_context_active(context, self._context_keys):
            return None
        return context

    def _record_suppression(
        self,
        record: logging.LogRecord,
        context: Mapping[str, Any],
        current_time: Optional[float] = None,
    ) -> None:
        """Forward suppression details to the summary emitter when enabled.

        Args:
            record: Suppressed log record.
            context: Active logging context for the record.
            current_time: Optional current clock value.
        """
        if self._summary_emitter is None:
            return
        record_key = _build_record_key(record, context, self._key_fields)
        emitted_at = current_time
        if emitted_at is None:
            emitted_at = self._get_current_time()
        self._summary_emitter.record_suppression(record, record_key, emitted_at)


class _ContextSuppressionStrategy(_ContextAwareStrategy):
    """Strategy that suppresses matching records whenever context is active."""

    def __call__(self, record: logging.LogRecord) -> bool:
        """Suppress matching records in active context.

        Args:
            record: Log record being filtered.

        Returns:
            False for suppressible records, otherwise True.
        """
        context = self._get_active_context(record)
        if context is None:
            return True
        self._record_suppression(record, context)
        return False


class _RateLimitStrategy(_ContextAwareStrategy):
    """Strategy that rate-limits matching records within a time window."""

    def __init__(
        self,
        config: FloodControlFilterConfig,
        summary_emitter: Optional["_SummaryEmitter"],
        get_current_time: TimeProvider,
    ) -> None:
        """Initialize rate-limit state for matching records.

        Args:
            config: Normalized flood-control configuration.
            summary_emitter: Optional summary emitter for suppressed records.
            get_current_time: Monotonic clock provider.
        """
        super().__init__(config, summary_emitter, get_current_time)
        self._window_seconds = config.window_seconds
        self._max_events_per_window = config.max_events_per_window
        self._max_cache_size = config.max_cache_size
        self._lock = RLock()
        self._event_windows: Dict[FloodControlKey, Deque[float]] = {}
        self._last_seen_at: Dict[FloodControlKey, float] = {}

    def __call__(self, record: logging.LogRecord) -> bool:
        """Apply rate limiting to a record.

        Args:
            record: Log record being filtered.

        Returns:
            True when the record is allowed, otherwise False.
        """
        context = self._get_active_context(record)
        if context is None:
            return True

        current_time = self._get_current_time()
        record_key = _build_record_key(record, context, self._key_fields)
        should_suppress = self._should_suppress(record_key, current_time)
        if should_suppress:
            self._record_suppression(record, context, current_time)
            return False
        return True

    def _should_suppress(
        self,
        record_key: FloodControlKey,
        current_time: float,
    ) -> bool:
        """Evaluate rate-limit state for the supplied record key.

        Args:
            record_key: Frozen key representing the record identity.
            current_time: Monotonic timestamp for this decision.

        Returns:
            True when the record must be suppressed, otherwise False.
        """
        with self._lock:
            event_window = self._event_windows.setdefault(record_key, deque())
            while (
                event_window and current_time - event_window[0] >= self._window_seconds
            ):
                event_window.popleft()

            should_suppress = len(event_window) >= self._max_events_per_window
            if not should_suppress:
                event_window.append(current_time)

            self._last_seen_at[record_key] = current_time
            self._enforce_cache_limit_locked()
            return should_suppress

    def _enforce_cache_limit_locked(self) -> None:
        """Evict the oldest rate-limit entries when cache size is exceeded."""
        if len(self._last_seen_at) <= self._max_cache_size:
            return

        overflow = len(self._last_seen_at) - self._max_cache_size
        oldest_keys = sorted(self._last_seen_at.items(), key=lambda item: item[1])[
            :overflow
        ]

        for record_key, _ in oldest_keys:
            self._last_seen_at.pop(record_key, None)
            self._event_windows.pop(record_key, None)


class _DeduplicateStrategy(_ContextAwareStrategy):
    """Strategy that suppresses repeated matching records within a window."""

    def __init__(
        self,
        config: FloodControlFilterConfig,
        summary_emitter: Optional["_SummaryEmitter"],
        get_current_time: TimeProvider,
    ) -> None:
        """Initialize duplicate-detection state.

        Args:
            config: Normalized flood-control configuration.
            summary_emitter: Optional summary emitter for suppressed records.
            get_current_time: Monotonic clock provider.
        """
        super().__init__(config, summary_emitter, get_current_time)
        self._window_seconds = config.window_seconds
        self._max_cache_size = config.max_cache_size
        self._lock = RLock()
        self._seen_at: Dict[FloodControlKey, float] = {}
        self._last_seen_at: Dict[FloodControlKey, float] = {}

    def __call__(self, record: logging.LogRecord) -> bool:
        """Apply duplicate suppression to a record.

        Args:
            record: Log record being filtered.

        Returns:
            True when the record is allowed, otherwise False.
        """
        context = self._get_active_context(record)
        if context is None:
            return True

        current_time = self._get_current_time()
        record_key = _build_record_key(record, context, self._key_fields)
        should_suppress = self._should_suppress(record_key, current_time)
        if should_suppress:
            self._record_suppression(record, context, current_time)
            return False
        return True

    def _should_suppress(
        self,
        record_key: FloodControlKey,
        current_time: float,
    ) -> bool:
        """Return whether a matching record is a duplicate in the active window.

        Args:
            record_key: Frozen key representing the record identity.
            current_time: Monotonic timestamp for this decision.

        Returns:
            True when the record must be suppressed, otherwise False.
        """
        with self._lock:
            last_seen_at = self._seen_at.get(record_key)
            self._seen_at[record_key] = current_time
            self._last_seen_at[record_key] = current_time
            self._enforce_cache_limit_locked()

            if last_seen_at is None:
                return False
            return current_time - last_seen_at < self._window_seconds

    def _enforce_cache_limit_locked(self) -> None:
        """Evict the oldest duplicate-tracking entries when cache is full."""
        if len(self._last_seen_at) <= self._max_cache_size:
            return

        overflow = len(self._last_seen_at) - self._max_cache_size
        oldest_keys = sorted(self._last_seen_at.items(), key=lambda item: item[1])[
            :overflow
        ]

        for record_key, _ in oldest_keys:
            self._last_seen_at.pop(record_key, None)
            self._seen_at.pop(record_key, None)


class _SummaryEmitter:
    """Emitter for periodic summaries about suppressed records."""

    def __init__(
        self,
        config: FloodControlFilterConfig,
        get_summary_logger: SummaryLoggerFactory,
    ) -> None:
        """Initialize summary-emission state.

        Args:
            config: Normalized flood-control configuration.
            get_summary_logger: Factory returning the logger for summary output.
        """
        self._mode = config.mode
        self._summary_level = config.summary_level
        self._summary_interval_seconds = config.summary_interval_seconds
        self._force_log_attr = config.force_log_attr
        self._max_cache_size = config.max_cache_size
        self._get_summary_logger = get_summary_logger
        self._lock = RLock()
        self._summary_counts: Dict[FloodControlKey, int] = {}
        self._summary_last_emitted_at: Dict[FloodControlKey, float] = {}
        self._last_seen_at: Dict[FloodControlKey, float] = {}

    def record_suppression(
        self,
        record: logging.LogRecord,
        record_key: FloodControlKey,
        current_time: float,
    ) -> None:
        """Record suppression state and emit summaries when due.

        Args:
            record: Suppressed log record.
            record_key: Frozen key representing the suppressed record identity.
            current_time: Monotonic timestamp for this suppression.
        """
        summary_count: Optional[int] = None

        with self._lock:
            self._summary_counts[record_key] = (
                self._summary_counts.get(record_key, 0) + 1
            )
            self._last_seen_at[record_key] = current_time

            last_summary_at = self._summary_last_emitted_at.get(record_key)
            if last_summary_at is None:
                self._summary_last_emitted_at[record_key] = current_time
            elif current_time - last_summary_at >= self._summary_interval_seconds:
                summary_count = self._summary_counts[record_key]
                self._summary_counts[record_key] = 0
                self._summary_last_emitted_at[record_key] = current_time

            self._enforce_cache_limit_locked()

        if summary_count is not None:
            self._emit_summary(record, record_key, summary_count)

    def _emit_summary(
        self,
        record: logging.LogRecord,
        record_key: FloodControlKey,
        count: int,
    ) -> None:
        """Emit a synthetic summary record for suppressed events.

        Args:
            record: Source log record.
            record_key: Frozen key representing the suppressed record identity.
            count: Number of suppressed records being summarized.
        """
        summary_logger = self._get_summary_logger(record.name)
        summary_logger.log(
            self._summary_level,
            _SUMMARY_MESSAGE_TEMPLATE.format(
                count=count,
                mode=self._mode,
                key=record_key,
            ),
            extra={self._force_log_attr: True},
        )

    def _enforce_cache_limit_locked(self) -> None:
        """Evict the oldest summary state entries when cache is full."""
        if len(self._last_seen_at) <= self._max_cache_size:
            return

        overflow = len(self._last_seen_at) - self._max_cache_size
        oldest_keys = sorted(self._last_seen_at.items(), key=lambda item: item[1])[
            :overflow
        ]

        for record_key, _ in oldest_keys:
            self._last_seen_at.pop(record_key, None)
            self._summary_counts.pop(record_key, None)
            self._summary_last_emitted_at.pop(record_key, None)


def _is_context_active(
    context: Mapping[str, Any],
    context_keys: Tuple[str, ...],
) -> bool:
    """Return whether flood control should activate for the supplied context.

    Args:
        context: Active logging context mapping.
        context_keys: Context keys that activate flood control.

    Returns:
        True when flood control should apply, otherwise False.
    """
    if not context_keys:
        return True
    return any(context_key in context for context_key in context_keys)


def _build_record_key(
    record: logging.LogRecord,
    context: Mapping[str, Any],
    key_fields: Tuple[str, ...],
) -> FloodControlKey:
    """Build a frozen key used by stateful suppression strategies.

    Args:
        record: Log record being filtered.
        context: Active logging context mapping.
        key_fields: Record and context fields used in the key.

    Returns:
        Tuple containing frozen key components.
    """
    key_parts: List[Any] = []
    for field_name in key_fields:
        if field_name in context:
            field_value = context[field_name]
        elif field_name == "message":
            field_value = record.getMessage()
        else:
            field_value = getattr(record, field_name, None)
        key_parts.append(_freeze_key_component(field_value))
    return tuple(key_parts)


def _freeze_key_component(value: Any) -> Any:
    """Return a hashable representation of a key component.

    Args:
        value: Raw key component value.

    Returns:
        Original value when hashable, otherwise its repr().
    """
    try:
        hash(value)
        return value
    except TypeError:
        return repr(value)


__all__: List[str] = ["FilterStrategy", "build_filter_strategy"]
