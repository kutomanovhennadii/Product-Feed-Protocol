"""Tests for the LogPipeline runtime orchestrator module."""

from __future__ import annotations

import io
import logging
import sys
from pathlib import Path
from types import TracebackType
from typing import List, cast

import pytest

from pfp_utils.logging.formatters.text_formatter import TextFormatterWithContext
from pfp_utils.logging.log_pipeline import LogPipeline, _normalize_exc_info, _to_numeric
from pfp_utils.logging.log_registry import InMemoryLoggingRegistry


class CapturingStreamHandler(logging.StreamHandler):
    """StreamHandler test double that stores emitted records for assertions."""

    def __init__(self, stream: io.StringIO) -> None:
        """Initialize the handler with an in-memory stream.

        Args:
            stream: Writable text stream used to capture emitted output.

        Returns:
            None.
        """
        super().__init__(stream)
        self.records: List[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        """Store the record before delegating to the base StreamHandler.

        Args:
            record: LogRecord being emitted by the handler.

        Returns:
            None.
        """
        self.records.append(record)
        super().emit(record)


def build_text_pipeline(
    level: str = "INFO",
    fmt: str = "%(message)s",
) -> tuple[LogPipeline, io.StringIO, CapturingStreamHandler]:
    """Assemble a LogPipeline with an in-memory text handler for tests.

    Args:
        level: Textual threshold configured on the pipeline.
        fmt: Formatter template applied by the text formatter.

    Returns:
        Tuple with the pipeline, the backing StringIO stream, and the handler.
    """
    stream = io.StringIO()
    handler = CapturingStreamHandler(stream)
    formatter = TextFormatterWithContext(fmt)
    handler.setFormatter(formatter)
    pipeline = LogPipeline(
        level=level,
        format_type="TEXT",
        filters=(),
        formatter=formatter,
        handler=handler,
        registry=InMemoryLoggingRegistry(),
    )
    return pipeline, stream, handler


def test_log_process_short_circuits_below_pipeline_level() -> None:
    """Messages below the configured threshold must not reach the handler."""
    pipeline, stream, handler = build_text_pipeline(level="INFO")

    pipeline.log_process(logging.DEBUG, "test", "skip me")

    assert stream.getvalue() == ""
    assert handler.records == []


def test_log_process_emits_message_when_level_passes_threshold() -> None:
    """Messages at or above the threshold must be emitted by the handler."""
    pipeline, stream, _ = build_text_pipeline(level="INFO")

    pipeline.log_process(logging.INFO, "test", "hello")

    assert stream.getvalue().strip() == "hello"


def test_log_process_applies_extra_attributes_to_record_output() -> None:
    """Extra record attributes must be visible to the configured formatter."""
    pipeline, stream, _ = build_text_pipeline(level="INFO")

    pipeline.log_process(
        logging.INFO,
        "test",
        "hello",
        extra={"target": "http://x"},
    )

    assert stream.getvalue().strip() == "hello [target=http://x]"


def test_log_process_includes_exception_traceback_when_exception_is_provided() -> None:
    """Exception instances must be normalized into traceback output."""
    pipeline, stream, _ = build_text_pipeline(level="INFO")

    try:
        raise RuntimeError("boom")
    except RuntimeError as error:
        pipeline.log_process(
            logging.ERROR,
            "test",
            "hello",
            exc_info=error,
        )

    output = stream.getvalue()
    assert "Traceback" in output
    assert "RuntimeError: boom" in output


def test_log_process_uses_call_site_metadata_from_the_caller_frame() -> None:
    """Caller path, line, and function name must come from the invoking frame."""
    pipeline, _, handler = build_text_pipeline(level="INFO")

    def invoke_pipeline() -> int:
        call_line = sys._getframe().f_lineno + 1
        pipeline.log_process(logging.INFO, "test", "hello")
        return call_line

    expected_line = invoke_pipeline()
    record = handler.records[-1]

    assert Path(record.pathname).resolve() == Path(__file__).resolve()
    assert record.lineno == expected_line
    assert record.funcName == "invoke_pipeline"


def test_install_attaches_handler_and_level_via_registry() -> None:
    """First install must clear, attach, level, and mark the registry."""
    handler = logging.NullHandler()
    registry = InMemoryLoggingRegistry()
    pipeline = LogPipeline(
        level="WARNING",
        format_type="TEXT",
        filters=(),
        formatter=logging.Formatter("%(message)s"),
        handler=handler,
        registry=registry,
    )

    pipeline.install()

    assert registry.added_handlers == [handler]
    assert registry.root_level == logging.WARNING
    assert registry.is_attached() is True


def test_install_raises_for_repeated_installation() -> None:
    """Repeated install on the same pipeline must fail loudly."""
    handler = logging.NullHandler()
    registry = InMemoryLoggingRegistry()
    pipeline = LogPipeline(
        level="INFO",
        format_type="TEXT",
        filters=(),
        formatter=logging.Formatter("%(message)s"),
        handler=handler,
        registry=registry,
    )
    pipeline.install()

    with pytest.raises(RuntimeError, match="LogPipeline already installed"):
        pipeline.install()


def test_install_calls_registry_methods_in_expected_order() -> None:
    """Install must clear existing handlers before attaching the new handler."""
    handler = logging.NullHandler()
    registry = InMemoryLoggingRegistry()
    pipeline = LogPipeline(
        level="ERROR",
        format_type="TEXT",
        filters=(),
        formatter=logging.Formatter("%(message)s"),
        handler=handler,
        registry=registry,
    )

    pipeline.install()

    assert registry.call_log == [
        "clear_root_handlers",
        "add_root_handler",
        "set_root_level",
        "mark_attached",
    ]


def test_to_numeric_returns_numeric_level_for_valid_name() -> None:
    """Valid textual levels must resolve to stdlib numeric constants."""
    assert _to_numeric("INFO") == logging.INFO


def test_to_numeric_raises_for_unknown_level_name() -> None:
    """Unknown textual levels must raise ValueError."""
    with pytest.raises(ValueError, match="Invalid log level: BOGUS"):
        _to_numeric("BOGUS")


def test_normalize_exc_info_returns_none_when_absent() -> None:
    """Absent exception data must remain None."""
    assert _normalize_exc_info(None) is None


def test_normalize_exc_info_keeps_exc_info_tuples_unchanged() -> None:
    """Prebuilt exc_info tuples must be passed through unchanged."""
    try:
        raise RuntimeError("boom")
    except RuntimeError:
        exc_info = cast(
            tuple[type[BaseException], BaseException, TracebackType | None],
            sys.exc_info(),
        )

    assert _normalize_exc_info(exc_info) is exc_info
