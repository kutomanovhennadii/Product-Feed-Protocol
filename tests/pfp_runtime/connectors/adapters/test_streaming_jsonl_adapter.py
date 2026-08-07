"""Tests for StreamingJsonlAdapter orchestrator pipeline."""

import io
import json
import logging
from typing import Any, Mapping, cast

import pytest

from pfp_runtime.connectors.adapters.adapter_contract import AdapterFormatError
from pfp_runtime.connectors.adapters.streaming_jsonl_adapter import (
    StreamingJsonlAdapter,
)
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
    "max_line_bytes": 262144,
    "max_json_depth": 32,
    "max_json_container_items": 100000,
}


def _make_stream(*records: dict) -> io.StringIO:
    """Build an in-memory text stream of JSONL lines from a sequence of dicts."""
    return io.StringIO("\n".join(json.dumps(r) for r in records))


def test_streaming_jsonl_adapter_initialization():
    """Verify that constants are extracted and defaults apply when keys are absent.

    Given: Constants dict with all three keys set explicitly.
    When: StreamingJsonlAdapter is initialized.
    Then: Attributes reflect the provided values and format_name is correct.
    """
    adapter = StreamingJsonlAdapter(
        {"max_line_bytes": 1024, "max_json_depth": 5, "max_json_container_items": 50},
        log_pipeline=_LogPipelineStub(),
    )
    assert adapter.format_name == "streaming_jsonl"
    assert adapter.max_line_bytes == 1024
    assert adapter.max_json_depth == 5
    assert adapter.max_json_container_items == 50


def test_streaming_jsonl_adapter_initialization_defaults():
    """Verify that default constant values are applied when constants dict is empty.

    Given: Empty constants dict.
    When: StreamingJsonlAdapter is initialized.
    Then: max_line_bytes=262144, max_json_depth=32, max_json_container_items=100000.
    """
    adapter = StreamingJsonlAdapter({}, log_pipeline=_LogPipelineStub())
    assert adapter.max_line_bytes == 262144
    assert adapter.max_json_depth == 32
    assert adapter.max_json_container_items == 100000


def test_streaming_jsonl_parse_stringio_stream():
    """Verify that a StringIO stream with valid JSONL records is parsed correctly.

    Given: io.StringIO containing three valid JSON objects, one per line.
    When: parse is consumed.
    Then: Yields exact dicts in order.
    """
    adapter = StreamingJsonlAdapter(_DEFAULT_CONSTANTS, log_pipeline=_LogPipelineStub())
    stream = _make_stream({"id": "1"}, {"id": "2"}, {"id": "3"})
    records = list(adapter.parse(stream))
    assert records == [{"id": "1"}, {"id": "2"}, {"id": "3"}]


def test_streaming_jsonl_parse_generator_stream():
    """Verify that a line generator (Iterable[str]) is consumed correctly.

    Given: A generator function yielding JSONL lines one at a time.
    When: parse is consumed.
    Then: Yields all records without materializing the full input.
    """
    adapter = StreamingJsonlAdapter(_DEFAULT_CONSTANTS, log_pipeline=_LogPipelineStub())

    def line_gen():
        yield '{"sku": "A"}\n'
        yield '{"sku": "B"}\n'

    records = list(adapter.parse(line_gen()))
    assert records == [{"sku": "A"}, {"sku": "B"}]


def test_streaming_jsonl_parse_empty_stream():
    """Verify that an empty stream produces an empty result without errors.

    Given: An empty io.StringIO.
    When: parse is consumed.
    Then: Returns empty iterable without crash.
    """
    adapter = StreamingJsonlAdapter(_DEFAULT_CONSTANTS, log_pipeline=_LogPipelineStub())
    records = list(adapter.parse(io.StringIO("")))
    assert records == []


def test_streaming_jsonl_parse_skips_empty_lines():
    """Verify that blank lines between records are silently skipped.

    Given: A stream with empty lines interspersed between valid records.
    When: parse is consumed.
    Then: Yields only the non-empty records.
    """
    adapter = StreamingJsonlAdapter(_DEFAULT_CONSTANTS, log_pipeline=_LogPipelineStub())
    stream = io.StringIO('{"id": "1"}\n\n\n{"id": "2"}\n')
    records = list(adapter.parse(stream))
    assert records == [{"id": "1"}, {"id": "2"}]


def test_streaming_jsonl_rejects_string_input():
    """Verify that a plain str payload is rejected with a helpful message.

    Given: A raw JSONL string (common mistake: use JsonlAdapter instead).
    When: parse is invoked.
    Then: AdapterFormatError is raised directing to JsonlAdapter.
    """
    adapter = StreamingJsonlAdapter(_DEFAULT_CONSTANTS, log_pipeline=_LogPipelineStub())
    with pytest.raises(AdapterFormatError, match="not an in-memory string"):
        list(adapter.parse('{"id": "1"}\n{"id": "2"}'))


def test_streaming_jsonl_rejects_bytes_input():
    """Verify that bytes payload is rejected with a helpful message.

    Given: Raw bytes payload.
    When: parse is invoked.
    Then: AdapterFormatError is raised instructing to open stream in text mode.
    """
    adapter = StreamingJsonlAdapter(_DEFAULT_CONSTANTS, log_pipeline=_LogPipelineStub())
    with pytest.raises(AdapterFormatError, match="text mode"):
        list(adapter.parse(cast(Any, b'{"id": "1"}\n')))


def test_streaming_jsonl_rejects_integer_input():
    """Verify that a non-iterable value is rejected.

    Given: An integer.
    When: parse is invoked.
    Then: AdapterFormatError is raised.
    """
    adapter = StreamingJsonlAdapter(_DEFAULT_CONSTANTS, log_pipeline=_LogPipelineStub())
    with pytest.raises(AdapterFormatError, match="requires an iterable"):
        list(adapter.parse(cast(Any, 42)))


def test_streaming_jsonl_rejects_none_input():
    """Verify that None is rejected as non-iterable.

    Given: None value.
    When: parse is invoked.
    Then: AdapterFormatError is raised.
    """
    adapter = StreamingJsonlAdapter(_DEFAULT_CONSTANTS, log_pipeline=_LogPipelineStub())
    with pytest.raises(AdapterFormatError, match="requires an iterable"):
        list(adapter.parse(cast(Any, None)))


def test_streaming_jsonl_line_length_exceeded():
    """Verify that a line exceeding max_line_bytes raises AdapterFormatError.

    Given: A stream containing one line longer than max_line_bytes.
    When: parse is consumed.
    Then: AdapterFormatError is raised naming the line index and the limit.
    """
    adapter = StreamingJsonlAdapter(
        {"max_line_bytes": 20}, log_pipeline=_LogPipelineStub()
    )
    long_value = "x" * 30
    stream = io.StringIO(json.dumps({"key": long_value}))
    with pytest.raises(AdapterFormatError, match="exceeds maximum limit of 20 bytes"):
        list(adapter.parse(stream))


def test_streaming_jsonl_decode_error_masks_payload():
    """Verify that a broken JSON line raises AdapterFormatError without leaking content.

    Given: A stream with one malformed JSON line containing a sensitive value.
    When: parse is consumed.
    Then: AdapterFormatError is raised; sensitive content is not in the exception message.
    """
    adapter = StreamingJsonlAdapter(_DEFAULT_CONSTANTS, log_pipeline=_LogPipelineStub())
    stream = io.StringIO("{broken json SECRET_TOKEN: 'leak_me'}")
    with pytest.raises(
        AdapterFormatError, match="Failed to decode JSON payload"
    ) as exc_info:
        list(adapter.parse(stream))
    assert "leak_me" not in str(exc_info.value)
    assert "SECRET_TOKEN" not in str(exc_info.value)


def test_streaming_jsonl_depth_limit_exceeded():
    """Verify that a line with JSON nesting deeper than max_json_depth raises an error.

    Given: A line with JSON depth 4 and max_json_depth=3.
    When: parse is consumed.
    Then: AdapterFormatError is raised naming the depth and limit.
    """
    adapter = StreamingJsonlAdapter(
        {
            "max_line_bytes": 262144,
            "max_json_depth": 3,
            "max_json_container_items": 100000,
        },
        log_pipeline=_LogPipelineStub(),
    )
    # Depth: dict(1) -> list(2) -> dict(3) -> dict(4) — violates limit of 3
    deep = {"a": [{"b": {"c": 1}}]}
    stream = io.StringIO(json.dumps(deep))
    with pytest.raises(AdapterFormatError, match="exceeds maximum limit of 3"):
        list(adapter.parse(stream))


def test_streaming_jsonl_container_items_limit_exceeded():
    """Verify that a line with a JSON object exceeding max_json_container_items raises an error.

    Given: A line with an object containing 3 keys and max_json_container_items=2.
    When: parse is consumed.
    Then: AdapterFormatError is raised naming the item count and limit.
    """
    adapter = StreamingJsonlAdapter(
        {"max_line_bytes": 262144, "max_json_depth": 32, "max_json_container_items": 2},
        log_pipeline=_LogPipelineStub(),
    )
    stream = io.StringIO(json.dumps({"a": 1, "b": 2, "c": 3}))
    with pytest.raises(AdapterFormatError, match="exceeds maximum limit of 2"):
        list(adapter.parse(stream))


def test_streaming_jsonl_array_container_items_limit_exceeded():
    """Verify that a line with a JSON array exceeding max_json_container_items raises an error.

    Given: A line with an array containing 4 elements and max_json_container_items=3.
    When: parse is consumed.
    Then: AdapterFormatError is raised naming the item count and limit.
    """
    adapter = StreamingJsonlAdapter(
        {"max_line_bytes": 262144, "max_json_depth": 32, "max_json_container_items": 3},
        log_pipeline=_LogPipelineStub(),
    )
    stream = io.StringIO(json.dumps({"items": [1, 2, 3, 4]}))
    with pytest.raises(AdapterFormatError, match="exceeds maximum limit of 3"):
        list(adapter.parse(stream))


def test_streaming_jsonl_non_mapping_line_skipped_with_warning(caplog):
    """Verify that non-mapping lines are skipped and each triggers a WARNING log.

    Given: A stream with a scalar line and an array line mixed with valid records.
    When: parse is consumed.
    Then: Only mapping records are yielded; WARNING is logged for each skipped line.
    """
    adapter = StreamingJsonlAdapter(_DEFAULT_CONSTANTS, log_pipeline=_LogPipelineStub())
    stream = io.StringIO(
        '{"id": "1"}\n' '"just a string"\n' "[1, 2, 3]\n" '{"id": "2"}\n'
    )
    with caplog.at_level(logging.WARNING):
        records = list(adapter.parse(stream))

    assert records == [{"id": "1"}, {"id": "2"}]
    warnings = [r for r in caplog.records if r.levelname == "WARNING"]
    assert len(warnings) == 2
    assert getattr(warnings[0], "line_index", None) == 1
    assert getattr(warnings[1], "line_index", None) == 2


def test_streaming_jsonl_recursion_error_caught():
    """Verify that a RecursionError during tree validation is wrapped in AdapterFormatError.

    Given: A JSON structure deep enough to trigger Python's recursion limit when
        max_json_depth is set higher than the system default.
    When: _validate_tree_limits is called directly.
    Then: AdapterFormatError is raised instead of crashing with RecursionError.
    """
    adapter = StreamingJsonlAdapter(
        {"max_json_depth": 10000}, log_pipeline=_LogPipelineStub()
    )
    # Build a cyclic-reference dict to force RecursionError during traversal.
    recursive: dict = {}
    recursive["loop"] = recursive
    with pytest.raises(AdapterFormatError, match="RecursionError"):
        adapter._validate_tree_limits(recursive, index=0)
