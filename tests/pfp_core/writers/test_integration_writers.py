"""Integration tests for the pfp_core.writers block."""

from __future__ import annotations

from pfp_core.writers import build_default_writer_registry


def test_writer_registry_serializes_csv_rows_through_builtin_factory() -> None:
    """Builtin writer registry creates CSV writers that stream concrete rows."""

    writer = build_default_writer_registry().create(
        "csv",
        {"columns": ["id", "title"], "include_header": True},
        {"content_type": "text/csv", "file_extension": ".csv", "encoding": "utf-8"},
    )

    chunks = list(writer.write([("SKU-1", "Runner")]))

    assert chunks == [b"id,title\n", b"SKU-1,Runner\n"]


def test_writer_registry_serializes_jsonl_objects_through_builtin_factory() -> None:
    """Builtin writer registry creates JSONL writers that serialize records."""

    writer = build_default_writer_registry().create(
        "jsonl",
        {"sort_keys": True},
        {
            "content_type": "application/x-ndjson",
            "file_extension": ".jsonl",
            "encoding": "utf-8",
        },
    )

    chunks = list(writer.write([{"id": "SKU-1", "title": "Runner"}]))

    assert chunks == [b'{"id":"SKU-1","title":"Runner"}\n']
