"""Tests for the log registry abstractions."""

from __future__ import annotations

import logging
from collections.abc import Generator

import pytest

from pfp_utils.logging.log_registry import (
    InMemoryLoggingRegistry,
    LoggingRegistry,
    PythonLoggingRegistry,
)


@pytest.fixture
def restore_root_logger() -> Generator[None, None, None]:
    """Restore root logger handlers and level after each test.

    Yields:
        None while the test executes.

    Returns:
        Generator that restores the root logger state in fixture teardown.
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


def test_python_logging_registry_satisfies_runtime_protocol() -> None:
    """Production registry must satisfy the runtime-checkable protocol."""
    assert isinstance(PythonLoggingRegistry(), LoggingRegistry) is True


def test_in_memory_logging_registry_satisfies_runtime_protocol() -> None:
    """Fake registry must satisfy the runtime-checkable protocol."""
    assert isinstance(InMemoryLoggingRegistry(), LoggingRegistry) is True


def test_python_logging_registry_clears_root_handlers(
    restore_root_logger: None,
) -> None:
    """Production registry must detach all handlers from the root logger."""
    root = logging.getLogger()
    root.handlers[:] = []
    root.addHandler(logging.StreamHandler())
    root.addHandler(logging.NullHandler())
    registry = PythonLoggingRegistry()

    registry.clear_root_handlers()

    assert root.handlers == []


def test_python_logging_registry_adds_root_handler(
    restore_root_logger: None,
) -> None:
    """Production registry must attach the supplied handler to the root logger."""
    root = logging.getLogger()
    root.handlers[:] = []
    handler = logging.NullHandler()
    registry = PythonLoggingRegistry()

    registry.add_root_handler(handler)

    assert handler in root.handlers


def test_python_logging_registry_sets_root_level(restore_root_logger: None) -> None:
    """Production registry must apply the requested level to the root logger."""
    root = logging.getLogger()
    registry = PythonLoggingRegistry()

    registry.set_root_level(logging.DEBUG)

    assert root.level == logging.DEBUG


def test_python_logging_registry_tracks_attachment_state() -> None:
    """Production registry must expose attachment state transitions."""
    registry = PythonLoggingRegistry()

    assert registry.is_attached() is False

    registry.mark_attached()

    assert registry.is_attached() is True


def test_in_memory_logging_registry_updates_fake_state_only(
    restore_root_logger: None,
) -> None:
    """Fake registry must update only its in-memory state and not root logger."""
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    original_level = root.level
    handler = logging.NullHandler()
    registry = InMemoryLoggingRegistry()

    registry.clear_root_handlers()
    registry.add_root_handler(handler)
    registry.set_root_level(logging.ERROR)
    registry.mark_attached()

    assert registry.added_handlers == [handler]
    assert registry.root_level == logging.ERROR
    assert registry.is_attached() is True
    assert root.handlers == original_handlers
    assert root.level == original_level


def test_in_memory_logging_registry_records_call_order() -> None:
    """Fake registry must preserve call order for pipeline interaction tests."""
    handler = logging.NullHandler()
    registry = InMemoryLoggingRegistry()

    registry.clear_root_handlers()
    registry.add_root_handler(handler)
    registry.set_root_level(logging.INFO)
    registry.mark_attached()

    assert registry.call_log == [
        "clear_root_handlers",
        "add_root_handler",
        "set_root_level",
        "mark_attached",
    ]
