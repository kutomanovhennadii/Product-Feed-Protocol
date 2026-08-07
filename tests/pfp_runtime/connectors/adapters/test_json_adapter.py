"""Tests for JsonAdapter orchestrator pipeline."""

import json
import logging
from typing import Any, Mapping

import pytest

from pfp_runtime.connectors.adapters.adapter_contract import AdapterFormatError
from pfp_runtime.connectors.adapters.json_adapter import JsonAdapter
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


# Basic constants structure for JsonAdapter
_DEFAULT_CONSTANTS = {
    "max_input_bytes": 1024,
}


def test_json_adapter_success_root_array():
    """Test standard array of objects at JSON root.

    Given: Initialized adapter configuration.
    When: Adapter executes the target operation.
    Then: It validates the expected structural outcome or throws AdapterFormatError."""
    adapter = JsonAdapter(_DEFAULT_CONSTANTS, log_pipeline=_LogPipelineStub())
    payload = json.dumps([{"id": 1}, {"id": 2}])

    records = list(adapter.parse(payload))
    assert records == [{"id": 1}, {"id": 2}]


def test_json_adapter_success_items_path():
    """Test array of objects nested deep in JSON.

    Given: Initialized adapter configuration.
    When: Adapter executes the target operation.
    Then: It validates the expected structural outcome or throws AdapterFormatError."""
    adapter = JsonAdapter(
        {"max_input_bytes": 1024, "items_path": "data.products"},
        log_pipeline=_LogPipelineStub(),
    )
    payload = json.dumps(
        {"status": "ok", "data": {"products": [{"p_id": 10}, {"p_id": 20}]}}
    )

    records = list(adapter.parse(payload.encode("utf-8")))
    assert records == [{"p_id": 10}, {"p_id": 20}]


def test_json_adapter_limits_exceeded():
    """Test exceeding maximum input bytes.

    Given: Initialized adapter configuration.
    When: Adapter executes the target operation.
    Then: It validates the expected structural outcome or throws AdapterFormatError."""
    adapter = JsonAdapter({"max_input_bytes": 10}, log_pipeline=_LogPipelineStub())
    payload = json.dumps([{"a": 1}, {"b": 2}])  # length > 10

    with pytest.raises(AdapterFormatError, match="exceeds maximum limit"):
        list(adapter.parse(payload))


def test_json_adapter_limits_invalid_type():
    """Test unsupported raw input types.

    Given: Initialized adapter configuration.
    When: Adapter executes the target operation.
    Then: It validates the expected structural outcome or throws AdapterFormatError."""
    adapter = JsonAdapter(_DEFAULT_CONSTANTS, log_pipeline=_LogPipelineStub())

    with pytest.raises(AdapterFormatError, match="must be a string or bytes"):
        list(adapter.parse(12345))  # type: ignore


def test_json_adapter_safe_deserialize_error():
    """Test JSONDecodeError correctly wraps into AdapterFormatError without raw data.

    Given: Initialized adapter configuration.
    When: Adapter executes the target operation.
    Then: It validates the expected structural outcome or throws AdapterFormatError."""
    adapter = JsonAdapter(_DEFAULT_CONSTANTS, log_pipeline=_LogPipelineStub())
    bad_payload = "{bad_json: 123, secret_key: 'DO_NOT_LOG_ME'}"

    with pytest.raises(
        AdapterFormatError, match="Failed to decode JSON payload"
    ) as exc_info:
        list(adapter.parse(bad_payload))

    assert "DO_NOT_LOG" not in str(exc_info.value)


def test_json_adapter_locate_items_not_found():
    """Test items path localization failure.

    Given: Initialized adapter configuration.
    When: Adapter executes the target operation.
    Then: It validates the expected structural outcome or throws AdapterFormatError."""
    adapter = JsonAdapter(
        {"max_input_bytes": 1024, "items_path": "data.missing"},
        log_pipeline=_LogPipelineStub(),
    )
    payload = json.dumps({"data": {"exists": True}})

    with pytest.raises(
        AdapterFormatError, match="Path 'data.missing' not found in JSON data"
    ):
        list(adapter.parse(payload))


def test_json_adapter_locate_single_object_at_root():
    """Test lack of items_path but JSON has single object at root.

    Given: Initialized adapter configuration.
    When: Adapter parses a single JSON object (not an array).
    Then: The object is wrapped in a list and yielded as one record."""
    adapter = JsonAdapter(_DEFAULT_CONSTANTS, log_pipeline=_LogPipelineStub())
    payload = json.dumps({"some": "dict"})

    result = list(adapter.parse(payload))

    assert result == [{"some": "dict"}]


def test_json_adapter_locate_items_path_not_array():
    """Test that items_path must yield an array.

    Given: Initialized adapter configuration.
    When: Adapter executes the target operation.
    Then: It validates the expected structural outcome or throws AdapterFormatError."""
    adapter = JsonAdapter(
        {"max_input_bytes": 1024, "items_path": "data.scalar"},
        log_pipeline=_LogPipelineStub(),
    )
    payload = json.dumps({"data": {"scalar": 123}})

    with pytest.raises(
        AdapterFormatError, match="Target items location does not contain an array"
    ):
        list(adapter.parse(payload))


def test_json_adapter_yield_skips_non_mappings(caplog):
    """Test that scalar/primitives in array are skipped and logged as warning.

    Given: Initialized adapter configuration.
    When: Adapter executes the target operation.
    Then: It validates the expected structural outcome or throws AdapterFormatError."""
    adapter = JsonAdapter(_DEFAULT_CONSTANTS, log_pipeline=_LogPipelineStub())
    payload = json.dumps([{"id": 1}, "just a string", 123, {"id": 2}])

    with caplog.at_level(logging.WARNING):
        records = list(adapter.parse(payload))

    assert records == [{"id": 1}, {"id": 2}]
    assert "Skipped non-mapping item" in caplog.text
    # Ensure warnings happened
    warnings = [record for record in caplog.records if record.levelname == "WARNING"]
    assert len(warnings) == 2
    assert getattr(warnings[0], "index", None) == 1
    assert getattr(warnings[1], "index", None) == 2


def test_json_adapter_depth_limit_exceeded():
    """Test that max_json_depth limit raises an error.

    Given: Initialized adapter configuration.
    When: Adapter executes the target operation.
    Then: It validates the expected structural outcome or throws AdapterFormatError."""
    adapter = JsonAdapter(
        {"max_input_bytes": 1024, "max_json_depth": 3}, log_pipeline=_LogPipelineStub()
    )
    # Depth 1 = list, Depth 2 = dict, Depth 3 = list, Depth 4 = dict (violates limit 3)
    payload = json.dumps([{"nested": [{"deep": True}]}])

    with pytest.raises(
        AdapterFormatError, match="JSON depth 4 exceeds maximum limit of 3"
    ):
        list(adapter.parse(payload))


def test_json_adapter_object_items_limit_exceeded():
    """Test that max_json_container_items limit on objects raises an error.

    Given: Initialized adapter configuration.
    When: Adapter executes the target operation.
    Then: It validates the expected structural outcome or throws AdapterFormatError."""
    adapter = JsonAdapter(
        {"max_input_bytes": 1024, "max_json_container_items": 2},
        log_pipeline=_LogPipelineStub(),
    )
    payload = json.dumps([{"a": 1, "b": 2, "c": 3}])  # dict has 3 items, limit is 2

    with pytest.raises(
        AdapterFormatError, match="JSON object item count 3 exceeds maximum limit of 2"
    ):
        list(adapter.parse(payload))


def test_json_adapter_array_items_limit_exceeded():
    """Test that max_json_container_items limit on arrays raises an error.

    Given: Initialized adapter configuration.
    When: Adapter executes the target operation.
    Then: It validates the expected structural outcome or throws AdapterFormatError."""
    adapter = JsonAdapter(
        {"max_input_bytes": 1024, "max_json_container_items": 3},
        log_pipeline=_LogPipelineStub(),
    )
    payload = json.dumps([1, 2, 3, 4])  # root array has 4 items, limit is 3

    with pytest.raises(
        AdapterFormatError, match="JSON array item count 4 exceeds maximum limit of 3"
    ):
        list(adapter.parse(payload))


def test_json_adapter_native_recursion_error():
    """Test that native RecursionError is caught and wrapped during tree validation.

    Given: Initialized adapter configuration.
    When: Adapter executes the target operation.
    Then: It validates the expected structural outcome or throws AdapterFormatError."""
    # Set limit higher than Python's default recursion limit (usually 1000)
    adapter = JsonAdapter({"max_json_depth": 5000}, log_pipeline=_LogPipelineStub())

    # Create cyclic reference to force infinite recursion during validation
    recursive_dict = {}
    recursive_dict["loop"] = recursive_dict

    with pytest.raises(
        AdapterFormatError, match="JSON depth exceeds internal system limits"
    ):
        adapter._validate_tree_limits(recursive_dict)
