"""Tests for RowsAdapter orchestrator pipeline."""

import logging
from collections import OrderedDict
from typing import Any, Mapping

import pytest

from pfp_runtime.connectors.adapters.adapter_contract import AdapterFormatError
from pfp_runtime.connectors.adapters.rows_adapter import RowsAdapter
from pfp_utils.logging import LogPipeline
from pfp_utils.logging.log_registry import InMemoryLoggingRegistry


class _LogPipelineStub(LogPipeline):
    """Forward log calls into stdlib logging so caplog can capture them."""

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
    "max_records": 50000,
}


def test_rows_adapter_initialization():
    """Verify that constants are stored and max_records is extracted correctly.

    Given: Constants dict with explicit max_records.
    When: RowsAdapter is initialized.
    Then: format_name, max_records, and constants are set as expected.
    """
    adapter = RowsAdapter({"max_records": 100}, log_pipeline=_LogPipelineStub())
    assert adapter.max_records == 100
    assert adapter.format_name == "rows"
    assert adapter.constants == {"max_records": 100}


def test_rows_adapter_initialization_defaults():
    """Verify that max_records falls back to 50000 when not provided.

    Given: Empty constants dict.
    When: RowsAdapter is initialized.
    Then: max_records defaults to 50000.
    """
    adapter = RowsAdapter({}, log_pipeline=_LogPipelineStub())
    assert adapter.max_records == 50000


def test_rows_adapter_parse_valid_list():
    """Verify that a list of mapping records is yielded as plain dicts unchanged.

    Given: A list of two mapping records.
    When: parse is consumed.
    Then: Yields exact copies of each record as plain dicts.
    """
    adapter = RowsAdapter(_DEFAULT_CONSTANTS, log_pipeline=_LogPipelineStub())
    records = list(
        adapter.parse([{"id": "1", "name": "Alpha"}, {"id": "2", "name": "Beta"}])
    )
    assert records == [{"id": "1", "name": "Alpha"}, {"id": "2", "name": "Beta"}]


def test_rows_adapter_parse_generator_input():
    """Verify that a generator (lazy iterable) is consumed correctly.

    Given: A generator that yields two mapping records.
    When: parse is consumed.
    Then: Yields all records correctly without materializing the whole input.
    """

    def row_gen():
        yield {"sku": "A"}
        yield {"sku": "B"}

    adapter = RowsAdapter(_DEFAULT_CONSTANTS, log_pipeline=_LogPipelineStub())
    records = list(adapter.parse(row_gen()))
    assert records == [{"sku": "A"}, {"sku": "B"}]


def test_rows_adapter_parse_empty_input():
    """Verify that an empty iterable produces an empty result without errors.

    Given: An empty list.
    When: parse is consumed.
    Then: Returns empty iterable without crash.
    """
    adapter = RowsAdapter(_DEFAULT_CONSTANTS, log_pipeline=_LogPipelineStub())
    records = list(adapter.parse([]))
    assert records == []


def test_rows_adapter_rejects_string_input():
    """Verify that a raw string payload is rejected with a helpful error message.

    Given: A raw JSON string payload (common programmer mistake).
    When: parse is invoked.
    Then: AdapterFormatError is raised directing caller to use json/csv adapters.
    """
    adapter = RowsAdapter(_DEFAULT_CONSTANTS, log_pipeline=_LogPipelineStub())
    with pytest.raises(AdapterFormatError, match="not a string or bytes"):
        list(adapter.parse('{"id": "1"}'))


def test_rows_adapter_rejects_bytes_input():
    """Verify that raw bytes payload is rejected.

    Given: Raw bytes payload.
    When: parse is invoked.
    Then: AdapterFormatError is raised with a helpful message.
    """
    adapter = RowsAdapter(_DEFAULT_CONSTANTS, log_pipeline=_LogPipelineStub())
    with pytest.raises(AdapterFormatError, match="not a string or bytes"):
        list(adapter.parse(b"id,name\n1,Alpha"))


def test_rows_adapter_rejects_integer_input():
    """Verify that a non-iterable integer is rejected.

    Given: An integer value.
    When: parse is invoked.
    Then: AdapterFormatError is raised indicating iterable is required.
    """
    adapter = RowsAdapter(_DEFAULT_CONSTANTS, log_pipeline=_LogPipelineStub())
    with pytest.raises(AdapterFormatError, match="requires an iterable"):
        list(adapter.parse(42))


def test_rows_adapter_rejects_none_input():
    """Verify that None is rejected as non-iterable input.

    Given: None value.
    When: parse is invoked.
    Then: AdapterFormatError is raised.
    """
    adapter = RowsAdapter(_DEFAULT_CONSTANTS, log_pipeline=_LogPipelineStub())
    with pytest.raises(AdapterFormatError, match="requires an iterable"):
        list(adapter.parse(None))


def test_rows_adapter_skips_non_mapping_with_warning(caplog):
    """Verify that non-mapping items are skipped and each triggers a WARNING log.

    Given: Iterable containing scalars and lists mixed with valid mappings.
    When: parse is consumed.
    Then: Yields only mapping records; logs WARNING for each skipped non-mapping item.
    """
    adapter = RowsAdapter(_DEFAULT_CONSTANTS, log_pipeline=_LogPipelineStub())
    raw = [{"id": "1"}, "not_a_dict", 42, ["list_item"], {"id": "2"}]

    with caplog.at_level(logging.WARNING):
        records = list(adapter.parse(raw))

    assert records == [{"id": "1"}, {"id": "2"}]
    warnings = [r for r in caplog.records if r.levelname == "WARNING"]
    assert len(warnings) == 3
    assert getattr(warnings[0], "row_index", None) == 1
    assert getattr(warnings[1], "row_index", None) == 2
    assert getattr(warnings[2], "row_index", None) == 3


def test_rows_adapter_max_records_exceeded():
    """Verify that exceeding max_records raises AdapterFormatError.

    Given: Input with more records than max_records limit.
    When: parse is consumed past the limit.
    Then: AdapterFormatError is raised naming the limit value.
    """
    adapter = RowsAdapter({"max_records": 3}, log_pipeline=_LogPipelineStub())
    data = [{"id": str(i)} for i in range(5)]

    with pytest.raises(AdapterFormatError, match="exceeds maximum limit of 3"):
        list(adapter.parse(data))


def test_rows_adapter_exactly_at_limit():
    """Verify that exactly max_records items are yielded without error.

    Given: Input with exactly max_records items.
    When: parse is consumed.
    Then: All records are yielded successfully.
    """
    adapter = RowsAdapter({"max_records": 3}, log_pipeline=_LogPipelineStub())
    data = [{"id": str(i)} for i in range(3)]
    records = list(adapter.parse(data))
    assert len(records) == 3


def test_rows_adapter_one_over_limit():
    """Verify that max_records + 1 items triggers AdapterFormatError on the extra item.

    Given: Input with max_records + 1 items.
    When: parse is consumed.
    Then: AdapterFormatError is raised on the first item over the limit.
    """
    adapter = RowsAdapter({"max_records": 3}, log_pipeline=_LogPipelineStub())
    data = [{"id": str(i)} for i in range(4)]

    with pytest.raises(AdapterFormatError, match="exceeds maximum limit of 3"):
        list(adapter.parse(data))


def test_rows_adapter_dict_subclass_is_yielded():
    """Verify that dict subclasses (e.g. OrderedDict) are recognized as Mapping and yielded.

    Given: Input records that are OrderedDict instances.
    When: parse is consumed.
    Then: Items are recognized as Mapping and yielded as plain dicts.
    """
    adapter = RowsAdapter(_DEFAULT_CONSTANTS, log_pipeline=_LogPipelineStub())
    records = list(adapter.parse([OrderedDict([("key", "value")])]))
    assert records == [{"key": "value"}]
    assert type(records[0]) is dict


def test_rows_adapter_yields_plain_dict_copy():
    """Verify that yielded records are plain dict copies, not references to the original.

    Given: A mapping record.
    When: parse is consumed.
    Then: Yields a plain dict copy that equals the original but is not the same object.
    """
    adapter = RowsAdapter(_DEFAULT_CONSTANTS, log_pipeline=_LogPipelineStub())
    original = {"a": 1, "b": 2}
    records = list(adapter.parse([original]))
    assert records[0] == original
    assert records[0] is not original
