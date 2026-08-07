"""Unit tests for writer registry behavior."""

import inspect

import pytest

from pfp_core.writers import writer_registry as registry_module
from pfp_core.writers.impl.csv_writer import CSVWriter
from pfp_core.writers.writer_registry import UnknownWriterError, WriterRegistry


def test_registry_module_is_clean_from_builtin_writers() -> None:
    """Keep registry module decoupled from concrete builtin writer imports."""

    source = inspect.getsource(registry_module)

    assert "build_default_writer_registry" not in source


def test_registry_unknown_writer_raises_deterministic_error() -> None:
    """Raise deterministic UnknownWriterError for unknown writer id."""

    registry = WriterRegistry()

    with pytest.raises(
        UnknownWriterError,
        match="registry error: unknown writer_id=xml",
    ):
        registry.get_factory("xml")


def test_registry_rejects_duplicate_registration() -> None:
    """Reject duplicate writer registrations to keep contract explicit."""

    registry = WriterRegistry()
    registry.register("csv", lambda config, meta: CSVWriter(config, meta))

    with pytest.raises(
        ValueError,
        match="registry error: writer_id already registered: writer_id=csv",
    ):
        registry.register("csv", lambda config, meta: CSVWriter(config, meta))


def test_registry_rejects_empty_writer_id() -> None:
    """Reject empty writer identifiers during registration."""

    registry = WriterRegistry()

    with pytest.raises(
        ValueError,
        match="registry error: writer_id must be non-empty",
    ):
        registry.register("", lambda config, meta: CSVWriter(config, meta))
