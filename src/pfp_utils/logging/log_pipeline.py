"""LogPipeline init-phase wrapper and runtime orchestrator for observability."""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Tuple

from pfp_utils.logging.log_registry import LoggingRegistry


def _to_numeric(level: str) -> int:
    """Convert a textual logging level name to its numeric value.

    Args:
        level: Textual logging level such as "INFO" or "ERROR".

    Returns:
        Numeric logging level understood by the stdlib logging package.

    Raises:
        ValueError: If the provided level name is unknown.
    """
    numeric = getattr(logging, level.upper(), None)
    if not isinstance(numeric, int):
        raise ValueError(f"Invalid log level: {level}")
    return numeric


def _normalize_exc_info(exc_info: Any) -> Any:
    """Normalize exception metadata into the shape expected by LogRecord.

    Args:
        exc_info: None, an exception instance, or an exc_info tuple.

    Returns:
        None when exception data is absent, a normalized exc_info tuple when an
        exception instance is provided, or the original value for tuple input.
    """
    if exc_info is None:
        return None
    if isinstance(exc_info, BaseException):
        return (type(exc_info), exc_info, exc_info.__traceback__)
    return exc_info


@dataclass(frozen=True)
class LogPipeline:
    """Wrap Python logging primitives and orchestrate runtime log processing.

    Init-phase instances are assembled by a dedicated builder and keep the
    already-wired handler, formatter, filters, and registry together.
    Runtime calls use log_process() to create LogRecord objects explicitly and
    forward them through the configured handler.
    """

    level: str
    format_type: str
    filters: Tuple[logging.Filter, ...]
    formatter: logging.Formatter
    handler: logging.Handler
    registry: LoggingRegistry

    def log_process(
        self,
        level: int,
        name: str,
        msg: str,
        *args: Any,
        exc_info: Optional[Any] = None,
        extra: Optional[Mapping[str, Any]] = None,
    ) -> None:
        """Create a LogRecord and push it through the configured handler.

        Args:
            level: Numeric stdlib logging level such as logging.INFO.
            name: Logger name describing the call site.
            msg: Log message template or already-formatted message.
            *args: Positional arguments used by stdlib % formatting.
            exc_info: None, an exception instance, or an exc_info tuple.
            extra: Optional mapping of extra record attributes applied via setattr.

        Returns:
            None.
        """
        if level < _to_numeric(self.level):
            return

        frame = sys._getframe(1)
        record = logging.LogRecord(
            name=name,
            level=level,
            pathname=frame.f_code.co_filename,
            lineno=frame.f_lineno,
            msg=msg,
            args=args,
            exc_info=_normalize_exc_info(exc_info),
            func=frame.f_code.co_name,
        )

        if extra:
            for key, value in extra.items():
                setattr(record, key, value)

        self.handler.handle(record)

    def install(self) -> None:
        """Attach the wrapped handler to the root logger via the registry.

        Returns:
            None.

        Raises:
            RuntimeError: If the pipeline has already been installed.
        """
        if self.registry.is_attached():
            raise RuntimeError(
                "LogPipeline already installed - second install() is a build bug"
            )

        self.registry.clear_root_handlers()
        self.registry.add_root_handler(self.handler)
        self.registry.set_root_level(_to_numeric(self.level))
        self.registry.mark_attached()


__all__ = ["LogPipeline"]
