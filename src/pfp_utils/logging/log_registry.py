"""LoggingRegistry: wrapper around logging.getLogger() root manipulation.

Two implementations:
- PythonLoggingRegistry: production, thin wrapper over logging.getLogger().
- InMemoryLoggingRegistry: fake for unit tests, no global side effects.

See phase3_step6_secret_redaction_filter_plan.md §11.1 for rationale.
"""

from __future__ import annotations

import logging
from typing import List, Protocol, runtime_checkable


@runtime_checkable
class LoggingRegistry(Protocol):
    """Encapsulate Python logging root logger mutation.

    This protocol isolates the global logging registry behind an explicit
    contract so init-phase builders can be unit-tested without mutating the
    real Python root logger.
    """

    def clear_root_handlers(self) -> None:
        """Detach all handlers currently attached to Python's root logger.

        Returns:
            None.
        """
        ...

    def add_root_handler(self, handler: logging.Handler) -> None:
        """Attach a handler to Python's root logger.

        Args:
            handler: Handler instance attached to Python's root logger.

        Returns:
            None.
        """
        ...

    def set_root_level(self, level: int) -> None:
        """Set Python's root logger level.

        Args:
            level: Standard logging numeric level applied to the root logger.

        Returns:
            None.
        """
        ...

    def is_attached(self) -> bool:
        """Return whether mark_attached() has been called.

        Returns:
            True when the registry has been marked as attached.
        """
        ...

    def mark_attached(self) -> None:
        """Record that LogPipeline has installed itself via this registry.

        Returns:
            None.
        """
        ...


class PythonLoggingRegistry:
    """Production implementation backed by logging.getLogger()."""

    def __init__(self) -> None:
        """Initialize the registry in a detached state.

        Returns:
            None.
        """
        self._attached = False

    def clear_root_handlers(self) -> None:
        """Detach all handlers currently attached to the root logger.

        Returns:
            None.
        """
        root = logging.getLogger()
        for handler in root.handlers[:]:
            root.removeHandler(handler)

    def add_root_handler(self, handler: logging.Handler) -> None:
        """Attach a handler to the root logger.

        Args:
            handler: Handler instance attached to the root logger.

        Returns:
            None.
        """
        logging.getLogger().addHandler(handler)

    def set_root_level(self, level: int) -> None:
        """Set the root logger level.

        Args:
            level: Standard logging numeric level applied to the root logger.

        Returns:
            None.
        """
        logging.getLogger().setLevel(level)

    def is_attached(self) -> bool:
        """Return whether this registry has been marked as attached.

        Returns:
            True when mark_attached() has already been called.
        """
        return self._attached

    def mark_attached(self) -> None:
        """Record that a pipeline has installed itself via this registry.

        Returns:
            None.
        """
        self._attached = True


class InMemoryLoggingRegistry:
    """Fake implementation for unit tests with no global side effects."""

    def __init__(self) -> None:
        """Initialize fake storage for handlers, level, and call ordering.

        Returns:
            None.
        """
        self.added_handlers: List[logging.Handler] = []
        self.root_level: int = logging.WARNING
        self._attached = False
        self.call_log: List[str] = []

    def clear_root_handlers(self) -> None:
        """Clear fake attached handlers and record the call order.

        Returns:
            None.
        """
        self.added_handlers.clear()
        self.call_log.append("clear_root_handlers")

    def add_root_handler(self, handler: logging.Handler) -> None:
        """Attach a handler to fake storage.

        Args:
            handler: Handler instance tracked by the fake registry.

        Returns:
            None.
        """
        self.added_handlers.append(handler)
        self.call_log.append("add_root_handler")

    def set_root_level(self, level: int) -> None:
        """Set the fake root level and record the call order.

        Args:
            level: Standard logging numeric level tracked by the fake registry.

        Returns:
            None.
        """
        self.root_level = level
        self.call_log.append("set_root_level")

    def is_attached(self) -> bool:
        """Return whether this fake registry has been marked as attached.

        Returns:
            True when mark_attached() has already been called.
        """
        return self._attached

    def mark_attached(self) -> None:
        """Record fake pipeline attachment and the call order.

        Returns:
            None.
        """
        self._attached = True
        self.call_log.append("mark_attached")


__all__: List[str] = [
    "LoggingRegistry",
    "PythonLoggingRegistry",
    "InMemoryLoggingRegistry",
]
