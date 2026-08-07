"""Tests for the init-phase LogPipeline builder."""

from __future__ import annotations

import logging
from collections.abc import Generator

import pytest

from pfp_utils.logging.filters.context_filter import ContextFilter
from pfp_utils.logging.filters.flood_control_filter import FloodControlFilter
from pfp_utils.logging.filters.secret_redaction_filter import SecretRedactionFilter
from pfp_utils.logging.log_pipeline import LogPipeline
from pfp_utils.logging.log_pipeline_builder import build_log_pipeline
from pfp_utils.logging.log_registry import PythonLoggingRegistry


@pytest.fixture
def restore_root_logger() -> Generator[None, None, None]:
    """Restore root logger handlers and level after each builder test.

    Yields:
        None while the test executes.
    """
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    original_level = root.level

    try:
        yield
    finally:
        root.handlers[:] = []
        for handler in original_handlers:
            root.addHandler(handler)
        root.setLevel(original_level)


def test_build_log_pipeline_returns_active_text_pipeline_with_expected_shape(
    restore_root_logger: None,
) -> None:
    """TEXT builder output must include the expected active pipeline components."""
    root = logging.getLogger()
    pipeline = build_log_pipeline("INFO", "TEXT", {"enabled": False})

    assert isinstance(pipeline, LogPipeline)
    assert pipeline.level == "INFO"
    assert pipeline.format_type == "TEXT"
    assert len(pipeline.filters) == 3
    assert isinstance(pipeline.filters[0], ContextFilter)
    assert isinstance(pipeline.filters[1], SecretRedactionFilter)
    assert isinstance(pipeline.filters[2], FloodControlFilter)
    assert pipeline.handler.filters == list(pipeline.filters)
    assert pipeline.handler.formatter is pipeline.formatter
    assert isinstance(pipeline.registry, PythonLoggingRegistry)
    assert pipeline.registry.is_attached() is True
    assert root.handlers == [pipeline.handler]
    assert root.level == logging.INFO
    assert pipeline.filters[2].enabled is False


def test_build_log_pipeline_normalizes_lowercase_json_format(
    restore_root_logger: None,
) -> None:
    """Lowercase format selectors must normalize to the canonical key."""
    pipeline = build_log_pipeline("INFO", "json", {})

    assert pipeline.format_type == "JSON"
    assert pipeline.registry.is_attached() is True


def test_build_log_pipeline_rejects_unsupported_format_type() -> None:
    """Unsupported format selectors must raise ValueError."""
    with pytest.raises(ValueError, match="Invalid log format: YAML"):
        build_log_pipeline("INFO", "YAML", {})
