"""Unit tests for CSVWriter behavior."""

import inspect
from itertools import islice
from typing import Iterable, Iterator, Tuple

import pytest

import pfp_core.writers.impl.csv_writer as csv_writer_module
from pfp_core.writers.impl.csv_writer import CSVWriter
from pfp_core.writers.writer_types import MISSING


def _collect_bytes(writer: CSVWriter, rows: Iterable[Tuple[object, ...]]) -> bytes:
    """Collect full byte payload from writer iterable for assertions.

    Args:
        writer: CSV writer under test.
        rows: Input row iterable.

    Returns:
        Concatenated byte payload.
    """
    return b"".join(writer.write(rows))


def test_csv_writer_deterministic_output() -> None:
    """Produce identical bytes for identical rows and config."""

    writer = CSVWriter(
        {
            "columns": ["id", "title"],
            "include_header": True,
            "line_terminator": "\n",
        },
        {"encoding": "utf-8"},
    )
    rows = [("1", "Alpha"), ("2", "Beta")]

    first = _collect_bytes(writer, rows)
    second = _collect_bytes(writer, rows)

    assert first == second


def test_csv_writer_default_header_is_disabled() -> None:
    """Do not emit header when include_header is omitted from config."""

    writer = CSVWriter(
        {
            "columns": ["id", "title"],
            "missing_value_marker": "<missing>",
            "null_value_marker": "<null>",
        },
        {"encoding": "utf-8"},
    )

    output = _collect_bytes(writer, [("1", "A")]).decode("utf-8")

    assert output.strip() == "1,A"


def test_csv_writer_header_emitted_once() -> None:
    """Emit a single header row before data rows when include_header is enabled."""

    writer = CSVWriter(
        {
            "columns": ["id", "title"],
            "include_header": True,
            "missing_value_marker": "<missing>",
            "null_value_marker": "<null>",
        },
        {"encoding": "utf-8"},
    )

    output = _collect_bytes(writer, [("1", "A"), ("2", "B")]).decode("utf-8")
    lines = output.strip().split("\n")

    assert lines[0] == "id,title"
    assert lines[1] == "1,A"
    assert lines[2] == "2,B"
    assert len(lines) == 3


def test_csv_writer_header_uses_constructor_columns_when_config_omits_them() -> None:
    """Use columns provided by caller when include_header=true and config has no columns."""

    writer = CSVWriter(
        {
            "include_header": True,
            "missing_value_marker": "<missing>",
            "null_value_marker": "<null>",
        },
        {"encoding": "utf-8"},
        columns=("id", "title"),
    )

    output = _collect_bytes(writer, [("1", "A")]).decode("utf-8")
    lines = output.strip().split("\n")

    assert lines[0] == "id,title"
    assert lines[1] == "1,A"


def test_csv_writer_escapes_special_values() -> None:
    """Escape delimiter, quotes, and newline consistently through csv dialect."""

    writer = CSVWriter(
        {
            "columns": ["id", "title"],
            "include_header": False,
            "missing_value_marker": "<missing>",
            "null_value_marker": "<null>",
        },
        {"encoding": "utf-8"},
    )

    output = _collect_bytes(
        writer,
        [("1", "a,b"), ("2", 'a"b'), ("3", "a\nb")],
    ).decode("utf-8")

    assert '1,"a,b"' in output
    assert '2,"a""b"' in output
    assert '3,"a\nb"' in output


def test_csv_writer_distinguishes_missing_and_none() -> None:
    """Keep Missing and explicit None distinct using deterministic markers."""

    writer = CSVWriter(
        {
            "columns": ["id", "title", "description"],
            "include_header": False,
            "missing_value_marker": "<missing>",
            "null_value_marker": "NULL",
        },
        {"encoding": "utf-8"},
    )

    output = _collect_bytes(writer, [("1", MISSING, None)]).decode("utf-8").strip()

    assert output == "1,<missing>,NULL"


def test_csv_writer_marker_conflict_raises_on_missing_and_none() -> None:
    """Raise deterministic error when Missing and None become indistinguishable."""

    writer = CSVWriter(
        {
            "columns": ["id", "title", "description"],
            "include_header": False,
        },
        {"encoding": "utf-8"},
    )

    with pytest.raises(ValueError, match="csv writer error: marker_conflict"):
        _collect_bytes(writer, [("1", MISSING, None)])


def test_csv_writer_streaming_can_consume_first_chunks_only() -> None:
    """Allow consuming first chunks without exhausting the whole input stream."""

    consumed = {"count": 0}

    def _rows() -> Iterator[Tuple[object, ...]]:
        for idx in range(5):
            consumed["count"] += 1
            yield (str(idx),)

    writer = CSVWriter(
        {
            "columns": ["id"],
            "include_header": False,
            "missing_value_marker": "<missing>",
            "null_value_marker": "<null>",
        },
        {"encoding": "utf-8"},
    )

    chunks = writer.write(_rows())
    first_two = list(islice(chunks, 2))

    assert len(first_two) == 2
    assert consumed["count"] == 2


def test_csv_writer_rejects_dict_record_type() -> None:
    """Accept only CsvRow tuple inputs and reject mapping records."""

    writer = CSVWriter(
        {
            "columns": ["id"],
            "include_header": False,
            "missing_value_marker": "<missing>",
            "null_value_marker": "<null>",
        },
        {"encoding": "utf-8"},
    )

    with pytest.raises(ValueError, match="csv writer error: row_type expected=tuple"):
        _collect_bytes(writer, [{"id": "1"}])  # type: ignore[list-item]


def test_csv_writer_module_has_no_ext_import_dependency() -> None:
    """Keep CSV writer independent from ext-layer imports."""

    source = inspect.getsource(csv_writer_module)

    assert "pfp_core.ext" not in source


def test_csv_writer_header_requires_columns_definition() -> None:
    """Raise deterministic error when header is enabled without columns."""

    with pytest.raises(
        ValueError,
        match="csv writer error: columns_required include_header=true",
    ):
        _ = CSVWriter(
            {"include_header": True},
            {"encoding": "utf-8"},
        )


def test_csv_writer_rejects_invalid_columns_type() -> None:
    """Reject non-sequence columns config values."""

    with pytest.raises(
        ValueError,
        match=r"csv writer error: columns_type expected=sequence\[str\]",
    ):
        _ = CSVWriter(
            {
                "columns": 123,
                "missing_value_marker": "<missing>",
                "null_value_marker": "<null>",
            },
            {"encoding": "utf-8"},
        )


def test_csv_writer_rejects_non_string_columns_values() -> None:
    """Reject columns list items that are not strings."""

    with pytest.raises(
        ValueError,
        match="csv writer error: columns_value_type expected=str",
    ):
        _ = CSVWriter(
            {
                "columns": ["id", 2],
                "missing_value_marker": "<missing>",
                "null_value_marker": "<null>",
            },
            {"encoding": "utf-8"},
        )


def test_csv_writer_rejects_non_string_marker_values() -> None:
    """Reject non-string marker values in writer configuration."""

    with pytest.raises(
        ValueError,
        match="csv writer error: marker_type key=missing_value_marker expected=str",
    ):
        _ = CSVWriter(
            {
                "columns": ["id"],
                "missing_value_marker": 1,
                "null_value_marker": "<null>",
            },
            {"encoding": "utf-8"},
        )


def test_csv_writer_rejects_row_size_mismatch() -> None:
    """Raise deterministic error when row size does not match columns length."""

    writer = CSVWriter(
        {
            "columns": ["id", "title"],
            "missing_value_marker": "<missing>",
            "null_value_marker": "<null>",
        },
        {"encoding": "utf-8"},
    )

    with pytest.raises(ValueError, match="csv writer error: row_size_mismatch"):
        _collect_bytes(writer, [("1",)])


def test_csv_writer_serializes_booleans_as_lowercase_tokens() -> None:
    """Serialize bool values into lowercase true/false CSV tokens."""

    writer = CSVWriter(
        {
            "columns": ["flag_true", "flag_false"],
            "missing_value_marker": "<missing>",
            "null_value_marker": "<null>",
        },
        {"encoding": "utf-8"},
    )

    output = _collect_bytes(writer, [(True, False)]).decode("utf-8").strip()

    assert output == "true,false"
