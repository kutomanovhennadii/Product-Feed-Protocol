"""Tests for flood-control filter runtime strategies."""

import logging
from unittest.mock import Mock, patch

from pfp_utils.logging import LogContext
from pfp_utils.logging.filters.flood_control_filter.flood_control_filter_config_validation import (
    normalize_flood_control_config,
)
from pfp_utils.logging.filters.flood_control_filter.flood_control_filter_strategies import (
    build_filter_strategy,
)


def _build_record(
    level: int = logging.INFO, message: str = "message"
) -> logging.LogRecord:
    """Build a LogRecord for strategy-level tests."""
    return logging.LogRecord(
        name="flood-control-filter",
        level=level,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=None,
    )


def test_build_filter_strategy_returns_allow_all_for_disabled_config() -> None:
    """Disabled config must compile to an allow-all strategy."""
    strategy = build_filter_strategy(
        config=normalize_flood_control_config({"enabled": False}),
        get_current_time=Mock(return_value=0.0),
        get_summary_logger=Mock(),
    )

    with patch(
        "pfp_utils.logging.filters.flood_control_filter.flood_control_filter_strategies.get_context",
        side_effect=AssertionError("get_context should not be called"),
    ):
        assert strategy(_build_record()) is True


def test_context_suppression_strategy_blocks_info_in_item_context() -> None:
    """Context suppression strategy must block configured levels in active context."""
    strategy = build_filter_strategy(
        config=normalize_flood_control_config({}),
        get_current_time=Mock(side_effect=AssertionError("clock is unused")),
        get_summary_logger=Mock(),
    )

    with LogContext(item_ref="a"):
        assert strategy(_build_record()) is False


def test_context_suppression_strategy_allows_record_without_active_context() -> None:
    """Context suppression strategy must allow records when no trigger context exists."""
    strategy = build_filter_strategy(
        config=normalize_flood_control_config({}),
        get_current_time=Mock(side_effect=AssertionError("clock is unused")),
        get_summary_logger=Mock(),
    )

    assert strategy(_build_record()) is True


def test_context_suppression_strategy_allows_non_matching_level() -> None:
    """Context suppression strategy must allow records outside suppressed levels."""
    strategy = build_filter_strategy(
        config=normalize_flood_control_config({}),
        get_current_time=Mock(side_effect=AssertionError("clock is unused")),
        get_summary_logger=Mock(),
    )

    with LogContext(item_ref="a"):
        assert strategy(_build_record(level=logging.WARNING, message="warning")) is True


def test_rate_limit_strategy_suppresses_after_threshold_within_window() -> None:
    """Rate-limit strategy must suppress records after the configured threshold."""
    strategy = build_filter_strategy(
        config=normalize_flood_control_config(
            {
                "mode": "rate_limit",
                "context_keys": [],
                "key_fields": ["name", "msg"],
                "window_seconds": 1.0,
                "max_events_per_window": 2,
            }
        ),
        get_current_time=Mock(side_effect=[0.0, 0.1, 0.2, 1.2]),
        get_summary_logger=Mock(),
    )
    record = _build_record()

    assert strategy(record) is True
    assert strategy(record) is True
    assert strategy(record) is False
    assert strategy(record) is True


def test_rate_limit_strategy_allows_record_without_active_context() -> None:
    """Rate-limit strategy must allow records when the trigger context is absent."""
    strategy = build_filter_strategy(
        config=normalize_flood_control_config(
            {
                "mode": "rate_limit",
                "context_keys": ["item_ref"],
                "key_fields": ["msg"],
                "window_seconds": 1.0,
                "max_events_per_window": 1,
            }
        ),
        get_current_time=Mock(side_effect=AssertionError("clock is unused")),
        get_summary_logger=Mock(),
    )

    assert strategy(_build_record()) is True


def test_deduplicate_strategy_suppresses_repeated_records_within_window() -> None:
    """Deduplicate strategy must suppress repeated matching records in the window."""
    strategy = build_filter_strategy(
        config=normalize_flood_control_config(
            {
                "mode": "deduplicate",
                "context_keys": [],
                "key_fields": ["name", "msg"],
                "window_seconds": 1.0,
            }
        ),
        get_current_time=Mock(side_effect=[0.0, 0.5, 1.5]),
        get_summary_logger=Mock(),
    )
    record = _build_record()

    assert strategy(record) is True
    assert strategy(record) is False
    assert strategy(record) is True


def test_deduplicate_strategy_allows_record_without_active_context() -> None:
    """Deduplicate strategy must allow records when the trigger context is absent."""
    strategy = build_filter_strategy(
        config=normalize_flood_control_config(
            {
                "mode": "deduplicate",
                "context_keys": ["item_ref"],
                "key_fields": ["msg"],
                "window_seconds": 1.0,
            }
        ),
        get_current_time=Mock(side_effect=AssertionError("clock is unused")),
        get_summary_logger=Mock(),
    )

    assert strategy(_build_record()) is True


def test_strategy_emits_summary_after_suppression_interval() -> None:
    """Summary-capable strategy must emit a forced summary record on interval."""
    logger_mock = Mock()
    strategy = build_filter_strategy(
        config=normalize_flood_control_config(
            {"emit_summary": True, "summary_interval_seconds": 30.0}
        ),
        get_current_time=Mock(side_effect=[0.0, 31.0]),
        get_summary_logger=Mock(return_value=logger_mock),
    )
    record = _build_record()

    with LogContext(item_ref="a"):
        assert strategy(record) is False
        assert strategy(record) is False

    logger_mock.log.assert_called_once()
    log_call = logger_mock.log.call_args
    assert log_call.args[0] == logging.INFO
    assert "Flood control suppressed 2 records" in log_call.args[1]
    assert log_call.kwargs["extra"]["force_log"] is True


def test_context_suppression_strategy_without_summary_skips_clock_usage() -> None:
    """Context suppression without summaries must not touch the clock provider."""
    strategy = build_filter_strategy(
        config=normalize_flood_control_config({}),
        get_current_time=Mock(side_effect=AssertionError("clock is unused")),
        get_summary_logger=Mock(),
    )

    with LogContext(item_ref="a"):
        assert strategy(_build_record()) is False


def test_rate_limit_strategy_evicts_oldest_state_when_cache_is_full() -> None:
    """Rate-limit strategy must evict the oldest cached key when over capacity."""
    strategy = build_filter_strategy(
        config=normalize_flood_control_config(
            {
                "mode": "rate_limit",
                "context_keys": [],
                "key_fields": ["msg"],
                "window_seconds": 10.0,
                "max_events_per_window": 1,
                "max_cache_size": 1,
            }
        ),
        get_current_time=Mock(side_effect=[0.0, 1.0]),
        get_summary_logger=Mock(),
    )

    assert strategy(_build_record(message="first")) is True
    assert strategy(_build_record(message="second")) is True


def test_deduplicate_strategy_evicts_oldest_state_when_cache_is_full() -> None:
    """Deduplicate strategy must evict the oldest cached key when over capacity."""
    strategy = build_filter_strategy(
        config=normalize_flood_control_config(
            {
                "mode": "deduplicate",
                "context_keys": [],
                "key_fields": ["msg"],
                "window_seconds": 10.0,
                "max_cache_size": 1,
            }
        ),
        get_current_time=Mock(side_effect=[0.0, 1.0]),
        get_summary_logger=Mock(),
    )

    assert strategy(_build_record(message="first")) is True
    assert strategy(_build_record(message="second")) is True


def test_summary_strategy_evicts_oldest_summary_state_when_cache_is_full() -> None:
    """Summary emitter must evict the oldest summary cache entry when full."""
    logger_mock = Mock()
    strategy = build_filter_strategy(
        config=normalize_flood_control_config(
            {
                "emit_summary": True,
                "context_keys": [],
                "key_fields": ["msg"],
                "summary_interval_seconds": 10.0,
                "max_cache_size": 1,
            }
        ),
        get_current_time=Mock(side_effect=[0.0, 1.0]),
        get_summary_logger=Mock(return_value=logger_mock),
    )

    assert strategy(_build_record(message="first")) is False
    assert strategy(_build_record(message="second")) is False
    logger_mock.log.assert_not_called()


def test_strategy_helpers_cover_internal_branches() -> None:
    """Internal helper functions must handle empty context and unhashable values."""
    from pfp_utils.logging.filters.flood_control_filter.flood_control_filter_strategies import (
        _build_record_key,
        _freeze_key_component,
        _is_context_active,
    )

    record = _build_record(message="payload")
    context = {"payload": {"nested": True}}

    assert _is_context_active({}, tuple()) is True
    assert _is_context_active({"item_ref": "a"}, ("item_ref",)) is True
    assert _freeze_key_component({"nested": True}) == "{'nested': True}"
    assert _build_record_key(record, context, ("payload", "message")) == (
        "{'nested': True}",
        "payload",
    )
