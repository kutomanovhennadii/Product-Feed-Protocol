"""Tests for JsonlAdapter orchestrator pipeline."""

import logging
from typing import Any, Mapping

import pytest

from pfp_runtime.connectors.adapters.adapter_contract import AdapterFormatError
from pfp_runtime.connectors.adapters.jsonl_adapter import JsonlAdapter
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
    "max_line_bytes": 1024,
    "max_json_depth": 32,
    "max_json_container_items": 100,
}


def test_jsonl_adapter_success_multiple_lines():
    """Test standard valid JSONL lines parsing.

    Given: Initialized adapter configuration.
    When: Adapter executes the target operation.
    Then: It validates the expected structural outcome or throws AdapterFormatError."""
    adapter = JsonlAdapter(_DEFAULT_CONSTANTS, log_pipeline=_LogPipelineStub())
    payload = '{"id": 1}\n{"id": 2}\n\n{"id": 3}'

    records = list(adapter.parse(payload))
    assert records == [{"id": 1}, {"id": 2}, {"id": 3}]


def test_jsonl_adapter_success_bytes_input():
    """Test bytes input decoding.

    Given: Initialized adapter configuration.
    When: Adapter executes the target operation.
    Then: It validates the expected structural outcome or throws AdapterFormatError."""
    adapter = JsonlAdapter(_DEFAULT_CONSTANTS, log_pipeline=_LogPipelineStub())
    payload = b'{"a": 1}\n{"b": 2}'

    records = list(adapter.parse(payload))
    assert records == [{"a": 1}, {"b": 2}]


def test_jsonl_adapter_max_line_length_exceeded():
    """Test max line length enforcement.

    Given: Initialized adapter configuration.
    When: Adapter executes the target operation.
    Then: It validates the expected structural outcome or throws AdapterFormatError."""
    adapter = JsonlAdapter({"max_line_bytes": 10}, log_pipeline=_LogPipelineStub())
    payload = '{"a": 1}\n{"excessively long line": "breaks limits"}'

    with pytest.raises(
        AdapterFormatError, match="Line 1 length .* exceeds maximum limit of 10 bytes"
    ):
        list(adapter.parse(payload))


def test_jsonl_adapter_safe_deserialize_error(caplog):
    """Test JSONDecodeError is masked and wrapped without leaking raw inputs.

    Given: Initialized adapter configuration.
    When: Adapter executes the target operation.
    Then: It validates the expected structural outcome or throws AdapterFormatError."""
    adapter = JsonlAdapter(_DEFAULT_CONSTANTS, log_pipeline=_LogPipelineStub())
    payload = '{"valid": 1}\n{"invalid: formatting, secret: "DO_NOT_LOG_ME"}'

    with caplog.at_level(logging.ERROR):
        with pytest.raises(
            AdapterFormatError, match="Failed to decode JSON payload at line 1"
        ) as exc:
            list(adapter.parse(payload))

    assert "DO_NOT_LOG" not in str(exc.value)

    errors = [record for record in caplog.records if record.levelname == "ERROR"]
    assert len(errors) == 1
    assert "Failed to decode JSONL line" in errors[0].message
    assert getattr(errors[0], "line_index", None) == 1


def test_jsonl_adapter_max_json_depth_exceeded():
    """Test structural depth limit.

    Given: Initialized adapter configuration.
    When: Adapter executes the target operation.
    Then: It validates the expected structural outcome or throws AdapterFormatError."""
    adapter = JsonlAdapter(
        {"max_line_bytes": 1024, "max_json_depth": 2}, log_pipeline=_LogPipelineStub()
    )
    # Depth: 1=dict {"a": depth 2}, depth 2=dict {"b": depth 3} -> Error at depth 3
    payload = '{"id": 1}\n{"a": {"b": { "c": 1 } } }'

    with pytest.raises(
        AdapterFormatError, match="JSON depth 3 at line 1 exceeds maximum limit of 2"
    ):
        list(adapter.parse(payload))


def test_jsonl_adapter_object_items_limit():
    """Test max object items count.

    Given: Initialized adapter configuration.
    When: Adapter executes the target operation.
    Then: It validates the expected structural outcome or throws AdapterFormatError."""
    adapter = JsonlAdapter(
        {"max_line_bytes": 1024, "max_json_container_items": 2},
        log_pipeline=_LogPipelineStub(),
    )
    payload = '{"a": 1, "b": 2}\n{"x": 1, "y": 2, "z": 3}'  # Line 1 has 3 elements

    with pytest.raises(
        AdapterFormatError,
        match="JSON object item count 3 at line 1 exceeds maximum limit of 2",
    ):
        list(adapter.parse(payload))


def test_jsonl_adapter_array_items_limit():
    """Test max array items count.

    Given: Initialized adapter configuration.
    When: Adapter executes the target operation.
    Then: It validates the expected structural outcome or throws AdapterFormatError."""
    adapter = JsonlAdapter(
        {"max_line_bytes": 1024, "max_json_container_items": 2},
        log_pipeline=_LogPipelineStub(),
    )
    payload = '{"a": [1, 2, 3]}'

    with pytest.raises(
        AdapterFormatError,
        match="JSON array item count 3 at line 0 exceeds maximum limit of 2",
    ):
        list(adapter.parse(payload))


def test_jsonl_adapter_native_recursion_error():
    """Test that native RecursionError is caught and wrapped during tree validation.

    Given: Initialized adapter configuration.
    When: Adapter executes the target operation.
    Then: It validates the expected structural outcome or throws AdapterFormatError."""
    adapter = JsonlAdapter(
        {"max_line_bytes": 1024, "max_json_depth": 5000},
        log_pipeline=_LogPipelineStub(),
    )

    recursive_dict = {}
    recursive_dict["loop"] = recursive_dict

    with pytest.raises(
        AdapterFormatError,
        match="JSON depth exceeds internal system limits .* at line 0",
    ):
        adapter._validate_tree_limits(recursive_dict, 0)


def test_jsonl_adapter_extract_mapping_skips_non_mappings(caplog):
    """Test that lines parsing as arrays or scalars issue warnings instead of hard crashing.

    Given: Initialized adapter configuration.
    When: Adapter executes the target operation.
    Then: It validates the expected structural outcome or throws AdapterFormatError."""
    adapter = JsonlAdapter(_DEFAULT_CONSTANTS, log_pipeline=_LogPipelineStub())
    payload = '{"valid": 1}\n"just a string"\n123\n[1, 2, 3]\n{"valid": 2}'

    with caplog.at_level(logging.WARNING):
        records = list(adapter.parse(payload))

    assert records == [{"valid": 1}, {"valid": 2}]

    warnings = [r for r in caplog.records if r.levelname == "WARNING"]
    assert len(warnings) == 3
    assert "Skipped non-mapping jsonl line" in warnings[0].message
    assert getattr(warnings[0], "line_index", None) == 1
    assert getattr(warnings[1], "line_index", None) == 2
    assert getattr(warnings[2], "line_index", None) == 3
