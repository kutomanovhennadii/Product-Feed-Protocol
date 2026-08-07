"""Tests for telemetry handler factory."""

import logging
import sys
import types
from types import SimpleNamespace

import pytest

from pfp_utils.telemetry.telemetry_factory import (
    _split_handler_path,
    create_telemetry_handler,
)
from pfp_utils.telemetry.telemetry_handlers import (
    ConsoleTelemetryHandler,
    NoOpTelemetryHandler,
)


class _LogPipelineStub:
    def log_process(self, level, module_name, message, *args, **kwargs) -> None:
        extra = kwargs.get("extra")
        exc_info = kwargs.get("exc_info")
        logging.getLogger(module_name).log(
            level,
            message,
            *args,
            extra=extra,
            exc_info=exc_info,
        )


def test_create_handler_disabled_returns_noop() -> None:
    """Disabled telemetry config should return NoOp handler regardless of type."""
    handler = create_telemetry_handler(
        SimpleNamespace(enabled=False, handler="console"),
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    )
    assert isinstance(handler, NoOpTelemetryHandler)


def test_create_handler_accepts_instance() -> None:
    """Pre-built handler instances must be returned unchanged."""

    class CustomHandler:
        def __init__(self):
            self.duration_calls = 0
            self.inc_calls = 0

        def observe_duration(self, stage, duration, labels):
            self.duration_calls += 1

        def inc(self, name, value=1.0, labels=None):
            self.inc_calls += 1

    instance = CustomHandler()
    handler = create_telemetry_handler(
        SimpleNamespace(enabled=True, handler=instance),
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    )
    assert handler is instance
    handler.observe_duration("stage", 0.1, {})
    handler.inc("counter")
    assert instance.duration_calls == 1
    assert instance.inc_calls == 1


def test_create_handler_rejects_partial_instance_without_inc() -> None:
    """Partial pre-built handlers must be rejected via ValueError."""

    class PartialHandler:
        def observe_duration(self, stage, duration, labels):
            pass

    with pytest.raises(ValueError, match="must be a string or handler"):
        create_telemetry_handler(
            SimpleNamespace(enabled=True, handler=PartialHandler()),
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
        )


def test_create_handler_console_type() -> None:
    """String value 'console' should produce ConsoleTelemetryHandler."""
    handler = create_telemetry_handler(
        SimpleNamespace(enabled=True, handler="console"),
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    )
    assert isinstance(handler, ConsoleTelemetryHandler)


def test_create_handler_unknown_string_warns(caplog) -> None:
    """Unknown handler strings must log a warning and fall back to NoOp."""
    with caplog.at_level(logging.WARNING):
        handler = create_telemetry_handler(
            SimpleNamespace(enabled=True, handler="mystery"),
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
        )
    assert isinstance(handler, NoOpTelemetryHandler)
    assert "Unknown telemetry handler" in caplog.text


def test_create_handler_noop_aliases() -> None:
    """Various noop aliases should resolve to NoOpTelemetryHandler."""
    handler = create_telemetry_handler(
        SimpleNamespace(enabled=True, handler="NoOp"),
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    )
    assert isinstance(handler, NoOpTelemetryHandler)


def test_create_handler_dynamic_import_success() -> None:
    """Dynamic import with module path should instantiate provided handler class."""
    module_name = "tests.fake_telemetry_handler"
    module = types.ModuleType(module_name)

    class CustomHandler:
        def observe_duration(self, stage, duration, labels):
            pass

        def inc(self, name, value=1.0, labels=None):
            pass

    setattr(module, "CustomHandler", CustomHandler)
    sys.modules[module_name] = module
    try:
        handler = create_telemetry_handler(
            SimpleNamespace(
                enabled=True, handler="{0}:CustomHandler".format(module_name)
            ),
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
        )
        assert isinstance(handler, CustomHandler)
    finally:
        sys.modules.pop(module_name, None)


def test_create_handler_dynamic_import_missing_method(caplog) -> None:
    """Handlers missing observe_duration must log warning and fall back to NoOp."""
    module_name = "tests.bad_telemetry_handler"
    module = types.ModuleType(module_name)

    class BadHandler:
        pass

    setattr(module, "BadHandler", BadHandler)
    sys.modules[module_name] = module
    try:
        with caplog.at_level(logging.WARNING):
            handler = create_telemetry_handler(
                SimpleNamespace(
                    enabled=True, handler="{0}.BadHandler".format(module_name)
                ),
                log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
            )
        assert isinstance(handler, NoOpTelemetryHandler)
        assert "falling back to NoOp" in caplog.text
    finally:
        sys.modules.pop(module_name, None)


def test_create_handler_invalid_type() -> None:
    """Non-string/non-handler values should raise ValueError."""
    with pytest.raises(ValueError, match="must be a string or handler"):
        create_telemetry_handler(
            SimpleNamespace(enabled=True, handler=123),
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
        )


def test_split_handler_path_variants() -> None:
    """_split_handler_path must support colon and dot notation with validation."""
    module, attr = _split_handler_path("pkg.module:Class")
    assert module == "pkg.module"
    assert attr == "Class"

    module, attr = _split_handler_path("pkg.module.Class")
    assert module == "pkg.module"
    assert attr == "Class"

    with pytest.raises(ValueError):
        _split_handler_path(":Broken")
