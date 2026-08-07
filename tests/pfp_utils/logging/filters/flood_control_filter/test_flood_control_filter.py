"""Tests for the public FloodControlFilter facade."""

import logging
from unittest.mock import Mock, patch

from pfp_utils.logging.filters.flood_control_filter.flood_control_filter import (
    FloodControlFilter,
    build_flood_control_filter,
)
from pfp_utils.logging.filters.flood_control_filter.flood_control_filter_config_validation import (
    FloodControlFilterConfig,
)


def _build_config() -> FloodControlFilterConfig:
    """Build a normalized-looking config object for facade tests."""
    return FloodControlFilterConfig(
        enabled=True,
        mode="context_info_suppression",
        context_keys=("item_ref",),
        suppressed_levels=(logging.INFO,),
        force_log_attr="force_log",
        key_fields=("name", "levelno", "msg", "item_ref"),
        window_seconds=30.0,
        max_events_per_window=1,
        emit_summary=False,
        summary_level=logging.INFO,
        summary_interval_seconds=30.0,
        max_cache_size=10000,
    )


def test_flood_control_filter_initializes_strategy_from_normalized_config() -> None:
    """Facade must normalize config once and build a strategy from it."""
    normalized_config = _build_config()
    strategy = Mock(return_value=True)

    with patch(
        "pfp_utils.logging.filters.flood_control_filter.flood_control_filter.normalize_flood_control_config",
        return_value=normalized_config,
    ) as normalize_mock, patch(
        "pfp_utils.logging.filters.flood_control_filter.flood_control_filter.build_filter_strategy",
        return_value=strategy,
    ) as build_strategy_mock:
        filter_instance = FloodControlFilter(config={"enabled": True})

    normalize_mock.assert_called_once_with({"enabled": True})
    build_strategy_mock.assert_called_once()
    assert build_strategy_mock.call_args.kwargs["config"] is normalized_config
    assert filter_instance.enabled is True
    assert filter_instance.mode == "context_info_suppression"
    assert filter_instance.context_keys == ("item_ref",)
    assert filter_instance.suppressed_levels == (logging.INFO,)
    assert filter_instance.force_log_attr == "force_log"
    assert filter_instance.key_fields == ("name", "levelno", "msg", "item_ref")
    assert filter_instance.window_seconds == 30.0
    assert filter_instance.max_events_per_window == 1
    assert filter_instance.emit_summary is False
    assert filter_instance.summary_level == logging.INFO
    assert filter_instance.summary_interval_seconds == 30.0
    assert filter_instance.max_cache_size == 10000


def test_flood_control_filter_module_helpers_return_runtime_dependencies() -> None:
    """Module helpers must expose the clock and logger factories used by the facade."""
    from pfp_utils.logging.filters.flood_control_filter.flood_control_filter import (
        _get_current_time,
        _get_summary_logger,
    )

    assert isinstance(_get_current_time(), float)
    assert _get_summary_logger("flood-control-filter-helper") is logging.getLogger(
        "flood-control-filter-helper"
    )


def test_flood_control_filter_bypasses_strategy_for_force_log_record() -> None:
    """Facade must honor force_log without invoking the selected strategy."""
    filter_instance = FloodControlFilter()
    filter_instance._filter_strategy = Mock(side_effect=AssertionError("unreachable"))
    record = logging.LogRecord(
        name="flood-control-filter",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="message",
        args=(),
        exc_info=None,
    )
    record.force_log = True

    assert filter_instance.filter(record) is True


def test_flood_control_filter_delegates_to_selected_strategy() -> None:
    """Facade must delegate runtime decisions to the prebuilt strategy."""
    filter_instance = FloodControlFilter()
    strategy = Mock(return_value=False)
    filter_instance._filter_strategy = strategy
    record = logging.LogRecord(
        name="flood-control-filter",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="message",
        args=(),
        exc_info=None,
    )

    assert filter_instance.filter(record) is False
    strategy.assert_called_once_with(record)


def test_build_flood_control_filter_returns_flood_control_filter() -> None:
    """Builder must construct the public filter facade."""
    filter_instance = build_flood_control_filter({})

    assert isinstance(filter_instance, FloodControlFilter)


def test_build_flood_control_filter_propagates_invalid_config() -> None:
    """Builder must fail fast when normalization rejects the configuration."""
    try:
        build_flood_control_filter({"mode": "unsupported"})
    except ValueError as error:
        assert "Invalid flood control mode" in str(error)
    else:
        raise AssertionError("Expected ValueError for invalid flood control mode")
