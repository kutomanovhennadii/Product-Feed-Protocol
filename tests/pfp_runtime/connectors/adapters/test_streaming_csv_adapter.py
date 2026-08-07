"""Tests for StreamingCsvAdapter orchestrator pipeline."""

import csv
import io
import logging
from typing import Any, Mapping, cast

import pytest

from pfp_runtime.connectors.adapters.adapter_contract import AdapterFormatError
from pfp_runtime.connectors.adapters.streaming_csv_adapter import StreamingCsvAdapter
from pfp_utils.logging import LogPipeline
from pfp_utils.logging.log_registry import InMemoryLoggingRegistry


class _LogPipelineStub(LogPipeline):
    """Forwarding stub: routes log_process to stdlib so caplog can capture it."""

    def __init__(self) -> None:
        object.__setattr__(self, "level", "INFO")
        object.__setattr__(self, "format_type", "TEXT")
        object.__setattr__(self, "filters", ())
        object.__setattr__(self, "formatter", logging.Formatter("%(message)s"))
        object.__setattr__(self, "handler", logging.NullHandler())
        object.__setattr__(self, "registry", InMemoryLoggingRegistry())

    def log_process(
        self,
        level: int,
        name: str,
        msg: str,
        *args: Any,
        exc_info: Any = None,
        extra: Mapping[str, Any] | None = None,
    ) -> None:
        import logging as _stdlib

        _stdlib.getLogger(name).log(level, msg, *args, exc_info=exc_info, extra=extra)


_DEFAULT_CONSTANTS = {
    "csv_field_size_limit": 131072,
    "delimiter": ",",
    "has_header": True,
}


def _make_stream(*lines: str) -> io.StringIO:
    """Build an in-memory text stream from a sequence of CSV lines."""
    return io.StringIO("\n".join(lines))


def test_streaming_csv_adapter_initialization():
    """Verify that constants are extracted and correct values are set.

    Given: Constants dict with all keys set explicitly.
    When: StreamingCsvAdapter is initialized.
    Then: Attributes reflect the provided values and format_name is correct.
    """
    adapter = StreamingCsvAdapter(
        {"csv_field_size_limit": 512, "delimiter": ";", "has_header": False},
        log_pipeline=_LogPipelineStub(),
    )
    assert adapter.format_name == "streaming_csv"
    assert adapter.csv_field_size_limit == 512
    assert adapter.delimiter == ";"
    assert adapter.has_header is False


def test_streaming_csv_adapter_initialization_defaults():
    """Verify that default constant values are applied when constants dict is empty.

    Given: Empty constants dict.
    When: StreamingCsvAdapter is initialized.
    Then: csv_field_size_limit=131072, delimiter=",", has_header=True.
    """
    adapter = StreamingCsvAdapter({}, log_pipeline=_LogPipelineStub())
    assert adapter.csv_field_size_limit == 131072
    assert adapter.delimiter == ","
    assert adapter.has_header is True


def test_streaming_csv_parse_stringio_stream():
    """Verify that a StringIO stream with valid CSV records is parsed correctly.

    Given: io.StringIO containing a header row and two data rows.
    When: parse is consumed.
    Then: Yields exact dicts in order.
    """
    adapter = StreamingCsvAdapter(_DEFAULT_CONSTANTS, log_pipeline=_LogPipelineStub())
    stream = _make_stream("id,name", "1,Alpha", "2,Beta")
    records = list(adapter.parse(stream))
    assert records == [{"id": "1", "name": "Alpha"}, {"id": "2", "name": "Beta"}]


def test_streaming_csv_parse_generator_stream():
    """Verify that a line generator (Iterable[str]) is consumed correctly.

    Given: A generator function yielding CSV lines one at a time.
    When: parse is consumed.
    Then: Yields all records without materializing the full input.
    """
    adapter = StreamingCsvAdapter(_DEFAULT_CONSTANTS, log_pipeline=_LogPipelineStub())

    def line_gen():
        yield "sku,price\n"
        yield "A,10.00\n"
        yield "B,20.00\n"

    records = list(adapter.parse(line_gen()))
    assert records == [{"sku": "A", "price": "10.00"}, {"sku": "B", "price": "20.00"}]


def test_streaming_csv_parse_empty_stream_with_header():
    """Verify that an empty stream produces an empty result without errors.

    Given: An empty io.StringIO with has_header=True.
    When: parse is consumed.
    Then: Returns empty iterable without crash.
    """
    adapter = StreamingCsvAdapter(_DEFAULT_CONSTANTS, log_pipeline=_LogPipelineStub())
    records = list(adapter.parse(io.StringIO("")))
    assert records == []


def test_streaming_csv_parse_no_header_generates_column_names():
    """Verify that has_header=False generates col_0..col_N and yields all rows as data.

    Given: A stream without a header row and has_header=False.
    When: parse is consumed.
    Then: All rows are yielded with auto-generated column names, including the first row.
    """
    adapter = StreamingCsvAdapter(
        {"csv_field_size_limit": 131072, "delimiter": ",", "has_header": False},
        log_pipeline=_LogPipelineStub(),
    )
    stream = _make_stream("1,Alpha", "2,Beta")
    records = list(adapter.parse(stream))
    assert records == [
        {"col_0": "1", "col_1": "Alpha"},
        {"col_0": "2", "col_1": "Beta"},
    ]


def test_streaming_csv_parse_no_header_empty_stream():
    """Verify that an empty stream with has_header=False produces empty result.

    Given: An empty io.StringIO with has_header=False.
    When: parse is consumed.
    Then: Returns empty iterable without crash.
    """
    adapter = StreamingCsvAdapter(
        {"csv_field_size_limit": 131072, "delimiter": ",", "has_header": False},
        log_pipeline=_LogPipelineStub(),
    )
    records = list(adapter.parse(io.StringIO("")))
    assert records == []


def test_streaming_csv_parse_no_header_generator():
    """Verify that has_header=False works correctly with a non-seekable generator.

    Given: A generator yielding CSV lines without a header row.
    When: parse is consumed with has_header=False.
    Then: All rows yielded with col_0..col_N; no seek is attempted.
    """
    adapter = StreamingCsvAdapter(
        {"csv_field_size_limit": 131072, "delimiter": ",", "has_header": False},
        log_pipeline=_LogPipelineStub(),
    )

    def line_gen():
        yield "X,100\n"
        yield "Y,200\n"

    records = list(adapter.parse(line_gen()))
    assert records == [{"col_0": "X", "col_1": "100"}, {"col_0": "Y", "col_1": "200"}]


def test_streaming_csv_custom_delimiter():
    """Verify that a non-default delimiter is respected.

    Given: A stream using semicolon as delimiter and delimiter=";" in constants.
    When: parse is consumed.
    Then: Yields correctly split records.
    """
    adapter = StreamingCsvAdapter(
        {"csv_field_size_limit": 131072, "delimiter": ";", "has_header": True},
        log_pipeline=_LogPipelineStub(),
    )
    stream = _make_stream("id;name", "1;Alpha", "2;Beta")
    records = list(adapter.parse(stream))
    assert records == [{"id": "1", "name": "Alpha"}, {"id": "2", "name": "Beta"}]


def test_streaming_csv_row_extra_values_logged(caplog):
    """Verify that rows with extra values drop the overflow and log a warning.

    Given: A CSV with a row containing more values than header columns.
    When: parse is consumed.
    Then: Record is yielded without the extra value; WARNING is logged with row_index.
    """
    adapter = StreamingCsvAdapter(_DEFAULT_CONSTANTS, log_pipeline=_LogPipelineStub())
    stream = _make_stream("id,name", "1,Alpha,Extra")
    with caplog.at_level(logging.WARNING):
        records = list(adapter.parse(stream))
    assert records == [{"id": "1", "name": "Alpha"}]
    warnings = [r for r in caplog.records if r.levelname == "WARNING"]
    assert len(warnings) == 1
    assert getattr(warnings[0], "row_index", None) == 0


def test_streaming_csv_row_missing_values_logged(caplog):
    """Verify that rows with missing values produce None for absent columns and log a warning.

    Given: A CSV with a row containing fewer values than header columns.
    When: parse is consumed.
    Then: Record is yielded with None for the missing column; WARNING is logged with row_index.
    """
    adapter = StreamingCsvAdapter(_DEFAULT_CONSTANTS, log_pipeline=_LogPipelineStub())
    stream = _make_stream("id,name", "2")
    with caplog.at_level(logging.WARNING):
        records = list(adapter.parse(stream))
    assert records == [{"id": "2", "name": None}]
    warnings = [r for r in caplog.records if r.levelname == "WARNING"]
    assert len(warnings) == 1
    assert getattr(warnings[0], "row_index", None) == 0


def test_streaming_csv_empty_column_name_raises():
    """Verify that a header with an empty column name raises AdapterFormatError.

    Given: A stream with an empty column name in the header row.
    When: parse is consumed.
    Then: AdapterFormatError is raised.
    """
    adapter = StreamingCsvAdapter(_DEFAULT_CONSTANTS, log_pipeline=_LogPipelineStub())
    stream = _make_stream("id,,name", "1,X,Alpha")
    with pytest.raises(AdapterFormatError, match="empty column names"):
        list(adapter.parse(stream))


def test_streaming_csv_rejects_string_input():
    """Verify that a plain str payload is rejected with a helpful message.

    Given: A raw CSV string (common mistake: use CsvAdapter instead).
    When: parse is invoked.
    Then: AdapterFormatError is raised directing to CsvAdapter.
    """
    adapter = StreamingCsvAdapter(_DEFAULT_CONSTANTS, log_pipeline=_LogPipelineStub())
    with pytest.raises(AdapterFormatError, match="not an in-memory string"):
        list(adapter.parse("id,name\n1,Alpha"))


def test_streaming_csv_rejects_bytes_input():
    """Verify that bytes payload is rejected with a helpful message.

    Given: Raw bytes payload.
    When: parse is invoked.
    Then: AdapterFormatError is raised instructing to open stream in text mode.
    """
    adapter = StreamingCsvAdapter(_DEFAULT_CONSTANTS, log_pipeline=_LogPipelineStub())
    with pytest.raises(AdapterFormatError, match="text mode"):
        list(adapter.parse(cast(Any, b"id,name\n1,Alpha")))


def test_streaming_csv_rejects_integer_input():
    """Verify that a non-iterable value is rejected.

    Given: An integer.
    When: parse is invoked.
    Then: AdapterFormatError is raised.
    """
    adapter = StreamingCsvAdapter(_DEFAULT_CONSTANTS, log_pipeline=_LogPipelineStub())
    with pytest.raises(AdapterFormatError, match="requires an iterable"):
        list(adapter.parse(cast(Any, 42)))


def test_streaming_csv_rejects_none_input():
    """Verify that None is rejected as non-iterable.

    Given: None value.
    When: parse is invoked.
    Then: AdapterFormatError is raised.
    """
    adapter = StreamingCsvAdapter(_DEFAULT_CONSTANTS, log_pipeline=_LogPipelineStub())
    with pytest.raises(AdapterFormatError, match="requires an iterable"):
        list(adapter.parse(cast(Any, None)))


def test_streaming_csv_field_size_limit_in_data_row():
    """Verify that a field exceeding csv_field_size_limit in a data row raises AdapterFormatError.

    Given: A short header and a data row with a field exceeding csv_field_size_limit=10.
    When: parse is consumed.
    Then: AdapterFormatError is raised with "Malformed CSV structure".
    """
    original_limit = csv.field_size_limit()
    adapter = StreamingCsvAdapter(
        {"csv_field_size_limit": 10, "delimiter": ",", "has_header": True},
        log_pipeline=_LogPipelineStub(),
    )
    try:
        with pytest.raises(AdapterFormatError, match="Malformed CSV structure"):
            list(
                adapter.parse(_make_stream("a,b", "very_long_string_exceeding_limit,c"))
            )
    finally:
        csv.field_size_limit(original_limit)


def test_streaming_csv_field_size_limit_no_header():
    """Verify that a field exceeding csv_field_size_limit with has_header=False raises AdapterFormatError.

    Given: A stream with a long first field and csv_field_size_limit=10, has_header=False.
    When: parse is consumed.
    Then: AdapterFormatError is raised.
    """
    original_limit = csv.field_size_limit()
    adapter = StreamingCsvAdapter(
        {"csv_field_size_limit": 10, "delimiter": ",", "has_header": False},
        log_pipeline=_LogPipelineStub(),
    )
    try:
        with pytest.raises(AdapterFormatError, match="Malformed CSV structure"):
            list(adapter.parse(_make_stream("very_long_string_exceeding_limit,c")))
    finally:
        csv.field_size_limit(original_limit)


def test_streaming_csv_field_size_limit_in_header_row():
    """Verify that a header field exceeding csv_field_size_limit raises AdapterFormatError.

    Given: A header row with a field exceeding csv_field_size_limit=10.
    When: parse accesses fieldnames (lazy header read).
    Then: AdapterFormatError is raised with "Malformed CSV structure".
    """
    original_limit = csv.field_size_limit()
    adapter = StreamingCsvAdapter(
        {"csv_field_size_limit": 10, "delimiter": ",", "has_header": True},
        log_pipeline=_LogPipelineStub(),
    )
    try:
        with pytest.raises(AdapterFormatError, match="Malformed CSV structure"):
            list(adapter.parse(_make_stream("very_long_header_name,b", "1,2")))
    finally:
        csv.field_size_limit(original_limit)


def test_streaming_csv_field_size_limit_invalid_value():
    """Verify that an invalid csv_field_size_limit does not crash initialization or parsing.

    Given: A string passed as csv_field_size_limit.
    When: parse is consumed with valid CSV data.
    Then: Records are yielded without crash (graceful fallback).
    """
    original_limit = csv.field_size_limit()
    adapter = StreamingCsvAdapter(
        {"csv_field_size_limit": "not_an_int"}, log_pipeline=_LogPipelineStub()
    )
    try:
        records = list(adapter.parse(_make_stream("a,b", "1,2")))
        assert records == [{"a": "1", "b": "2"}]
    finally:
        csv.field_size_limit(original_limit)
