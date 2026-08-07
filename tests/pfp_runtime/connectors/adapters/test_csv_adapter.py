"""Tests for CsvAdapter."""

import csv
from typing import Any, cast

import pytest

from pfp_runtime.connectors.adapters.adapter_contract import AdapterFormatError
from pfp_runtime.connectors.adapters.csv_adapter import CsvAdapter
from pfp_utils.logging import LogPipeline


class _LogPipelineStub:
    """Forwarding stub: routes log_process to stdlib so caplog can capture it."""

    def log_process(
        self, level: int, module_name: str, message: str, *_args: Any, **kwargs: Any
    ) -> None:
        import logging as _stdlib

        extra = kwargs.get("extra")
        _stdlib.getLogger(module_name).log(level, message, extra=extra)


def _log_pipeline_stub() -> LogPipeline:
    """Return the local logging stub typed as the LogPipeline contract."""
    return cast(LogPipeline, _LogPipelineStub())


def test_csv_adapter_initialization():
    """
    Given: Constants dict with max limits and settings.
    When: CsvAdapter is initialized.
    Then: Configures inner limits and delimiters securely.
    """
    adapter = CsvAdapter(
        {"max_input_bytes": 100, "delimiter": ";", "has_header": False},
        log_pipeline=_log_pipeline_stub(),
    )
    assert adapter.max_input_bytes == 100
    assert adapter.delimiter == ";"
    assert adapter.has_header is False
    assert adapter.format_name == "csv"


def test_csv_adapter_limits_protection():
    """
    Given: Input size strictly larger than max_input_bytes.
    When: parse is invoked.
    Then: AdapterFormatError is raised.
    """
    adapter = CsvAdapter({"max_input_bytes": 5}, log_pipeline=_log_pipeline_stub())
    with pytest.raises(AdapterFormatError, match="exceeds maximum limit"):
        list(adapter.parse("123456"))


def test_csv_adapter_decode_error():
    """
    Given: Invalid byte sequence for utf-8.
    When: parse is invoked.
    Then: AdapterFormatError is raised without leaking raw payload.
    """
    adapter = CsvAdapter({}, log_pipeline=_log_pipeline_stub())
    with pytest.raises(AdapterFormatError, match="Failed to decode"):
        list(adapter.parse(b"\xff\xff"))


def test_csv_adapter_empty_header_error():
    """
    Given: CSV with missing/empty column names in the header row.
    When: parse is invoked.
    Then: AdapterFormatError is raised preventing schema corruption.
    """
    adapter = CsvAdapter({"has_header": True}, log_pipeline=_log_pipeline_stub())
    with pytest.raises(AdapterFormatError, match="empty column name"):
        list(adapter.parse("col1,,col3\n1,2,3"))


def test_csv_adapter_parse_valid_string():
    """
    Given: Valid CSV string and has_header=True.
    When: parse is consumed.
    Then: Yields exact mapped dictionaries.
    """
    adapter = CsvAdapter({}, log_pipeline=_log_pipeline_stub())
    records = list(adapter.parse("id,name\n1,Alpha\n2,Beta"))
    assert records == [{"id": "1", "name": "Alpha"}, {"id": "2", "name": "Beta"}]


def test_csv_adapter_parse_no_header():
    """
    Given: Valid CSV bytes and has_header=False.
    When: parse is consumed.
    Then: Generates default column names automatically.
    """
    adapter = CsvAdapter({"has_header": False}, log_pipeline=_log_pipeline_stub())
    records = list(adapter.parse(b"1,Alpha\n2,Beta"))
    assert records == [
        {"col_0": "1", "col_1": "Alpha"},
        {"col_0": "2", "col_1": "Beta"},
    ]


def test_csv_adapter_parse_no_header_empty():
    """
    Given: Empty CSV and has_header=False.
    When: parse is consumed.
    Then: Returns empty iterable without crash.
    """
    adapter = CsvAdapter({"has_header": False}, log_pipeline=_log_pipeline_stub())
    records = list(adapter.parse(""))
    assert records == []


def test_csv_adapter_parse_header_empty():
    """
    Given: Empty CSV and has_header=True.
    When: parse is consumed.
    Then: Returns empty iterable.
    """
    adapter = CsvAdapter({"has_header": True}, log_pipeline=_log_pipeline_stub())
    records = list(adapter.parse(""))
    assert records == []


def test_csv_adapter_row_anomalies_logged(caplog):
    """
    Given: CSV with lines containing too many or too few cells.
    When: parse is consumed.
    Then: Yields adapted dictionaries and logs warnings.
    """
    adapter = CsvAdapter({}, log_pipeline=_log_pipeline_stub())
    csv_data = "id,name\n1,Alpha,Extra\n2"

    with caplog.at_level("WARNING"):
        records = list(adapter.parse(csv_data))

    assert len(records) == 2
    assert records[0] == {"id": "1", "name": "Alpha"}
    assert records[1] == {"id": "2", "name": None}

    warnings = [
        rec.message for rec in caplog.records if "Row keys mismatch" in rec.message
    ]
    assert len(warnings) == 2


def test_csv_adapter_field_size_limit():
    """
    Given: A small field size limit in constants.
    When: parse reads a larger field.
    Then: AdapterFormatError is raised for malformed structure.
    """
    original_limit = csv.field_size_limit()
    adapter = CsvAdapter(
        {"csv_field_size_limit": 10}, log_pipeline=_log_pipeline_stub()
    )
    try:
        with pytest.raises(AdapterFormatError, match="Malformed CSV structure"):
            list(adapter.parse("very_long_header_string,b\n1,2"))
    finally:
        csv.field_size_limit(original_limit)


def test_csv_adapter_field_size_limit_invalid():
    """
    Given: Invalid field size limit.
    When: CsvAdapter initializes safe reader.
    Then: Ignores the limit failure softly.
    """
    original_limit = csv.field_size_limit()
    adapter = CsvAdapter(
        {"csv_field_size_limit": "invalid_limit_format"},
        log_pipeline=_log_pipeline_stub(),
    )
    try:
        records = list(adapter.parse("a,b\n1,2"))
        assert len(records) == 1
    finally:
        csv.field_size_limit(original_limit)


def test_csv_adapter_malformed_has_header_false():
    """
    Given: Malformed CSV with has_header=False.
    When: Next first_row is fetched.
    Then: Raises AdapterFormatError cleanly.
    """
    original_limit = csv.field_size_limit()
    adapter = CsvAdapter(
        {"csv_field_size_limit": 10, "has_header": False},
        log_pipeline=_log_pipeline_stub(),
    )
    try:
        with pytest.raises(AdapterFormatError, match="Malformed CSV structure"):
            list(adapter.parse("very_long_string_without_limit_over_10_chars"))
    finally:
        csv.field_size_limit(original_limit)


def test_csv_adapter_field_size_limit_caught_in_records():
    """
    Given: Short header but a payload where second row is huge.
    When: Generator yields records.
    Then: It triggers csv.Error and raises AdapterFormatError cleanly.
    """
    original_limit = csv.field_size_limit()
    adapter = CsvAdapter(
        {"csv_field_size_limit": 10}, log_pipeline=_log_pipeline_stub()
    )
    try:
        with pytest.raises(AdapterFormatError, match="Malformed CSV structure"):
            list(adapter.parse("a,b\nvery_long_string_in_second_row_over_10_chars,c"))
    finally:
        csv.field_size_limit(original_limit)


def test_csv_adapter_strips_utf8_bom_from_bytes_input():
    """
    Given: CSV bytes that start with a UTF-8 BOM (e.g. exported by Excel).
    When: parse is invoked.
    Then: BOM is stripped and the first column name has no leading \\ufeff.
    """
    adapter = CsvAdapter({}, log_pipeline=_log_pipeline_stub())
    csv_bytes = "﻿id,name\n1,Alpha".encode("utf-8")

    records = list(adapter.parse(csv_bytes))

    assert records == [{"id": "1", "name": "Alpha"}]


def test_csv_adapter_strips_utf8_bom_from_str_input():
    """
    Given: CSV string that already contains a leading \\ufeff character.
    When: parse is invoked.
    Then: BOM is stripped and the first column name has no leading \\ufeff.
    """
    adapter = CsvAdapter({}, log_pipeline=_log_pipeline_stub())

    records = list(adapter.parse("﻿id,name\n1,Alpha"))

    assert records == [{"id": "1", "name": "Alpha"}]
