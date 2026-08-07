"""Tests for builtins writer registry assembly."""

import inspect

import pfp_core.writers.writer_builtins as builtins_module
from pfp_core.writers.impl.csv_writer import CSVWriter
from pfp_core.writers.impl.jsonl_writer import JSONLWriter
from pfp_core.writers.writer_builtins import build_default_writer_registry


def test_builtins_module_imports_concrete_writers_from_impl() -> None:
    """Import concrete writers only from impl package in builtins assembly."""

    source = inspect.getsource(builtins_module)

    assert "from pfp_core.writers.impl.csv_writer import CSVWriter" in source
    assert "from pfp_core.writers.impl.jsonl_writer import JSONLWriter" in source


def test_registry_lists_default_ids_sorted() -> None:
    """Return sorted writer ids for builtin registry."""

    registry = build_default_writer_registry()

    assert registry.list_ids() == ("csv", "jsonl")


def test_registry_create_instantiates_builtin_writers() -> None:
    """Instantiate builtin writer classes through registry factories."""

    registry = build_default_writer_registry()

    csv_writer = registry.create(
        "csv",
        {"columns": ["id"], "include_header": False},
        {"content_type": "text/csv", "file_extension": ".csv", "encoding": "utf-8"},
    )
    jsonl_writer = registry.create(
        "jsonl",
        {},
        {
            "content_type": "application/x-ndjson",
            "file_extension": ".jsonl",
            "encoding": "utf-8",
        },
    )

    assert isinstance(csv_writer, CSVWriter)
    assert isinstance(jsonl_writer, JSONLWriter)
