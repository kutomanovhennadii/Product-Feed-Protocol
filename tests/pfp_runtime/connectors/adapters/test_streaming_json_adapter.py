import io
import logging
from logging import WARNING
from typing import Any, Mapping, cast

import pytest

from pfp_runtime.connectors.adapters.adapter_contract import AdapterFormatError
from pfp_runtime.connectors.adapters.streaming_json_adapter import (
    StreamingJsonAdapter,
    _IterableBytesReader,
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


@pytest.fixture
def adapter():
    constants = {"items_path": "item"}
    return StreamingJsonAdapter(constants, log_pipeline=_LogPipelineStub())


def test_streaming_json_success(adapter):
    """Test standard streaming with a byte stream."""
    data = b'[{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]'
    stream = io.BytesIO(data)

    records = list(adapter.parse(stream))
    assert len(records) == 2
    assert records[0] == {"id": 1, "name": "A"}
    assert records[1] == {"id": 2, "name": "B"}


def test_items_path_struct():
    """Test extracting items from a nested structure."""
    adapter = StreamingJsonAdapter(
        {"items_path": "data.products.item"}, log_pipeline=_LogPipelineStub()
    )
    data = b'{"status": "ok", "data": {"products": [{"sku": "P1"}, {"sku": "P2"}]}}'
    stream = io.BytesIO(data)

    records = list(adapter.parse(stream))
    assert len(records) == 2
    assert records[0]["sku"] == "P1"
    assert records[1]["sku"] == "P2"


def test_skip_non_mapping(adapter, caplog):
    """Test that numbers/strings in the array are skipped and logged."""
    data = b'[{"id": 1}, 123, "test", {"id": 2}]'
    stream = io.BytesIO(data)

    with caplog.at_level(WARNING):
        records = list(adapter.parse(stream))

    assert len(records) == 2
    assert records[0] == {"id": 1}
    assert records[1] == {"id": 2}

    warnings = [r for r in caplog.records if r.levelname == "WARNING"]
    assert len(warnings) == 2
    assert "Skipped non-mapping item" in warnings[0].message


def test_security_rule_mask_payload(adapter):
    """Test that malformed JSON raises AdapterFormatError and doesn't leak raw payload."""
    data = b'[{"id": 1}, {broken json...'
    stream = io.BytesIO(data)

    with pytest.raises(AdapterFormatError) as exc_info:
        list(adapter.parse(stream))

    error_msg = str(exc_info.value)
    # Check that exception has masked message
    assert "Failed to decode JSON stream payload" in error_msg
    # Ensure broken piece isn't in the error message
    assert "broken json" not in error_msg


def test_reject_in_memory_strings(adapter):
    """Test that passing str or bytes directly throws an exception."""
    data_str = '[{"id": 1}]'
    data_bytes = b'[{"id": 1}]'

    with pytest.raises(AdapterFormatError) as exc_info1:
        list(adapter.parse(data_str))
    assert "streaming_json format requires a byte stream" in str(exc_info1.value)

    with pytest.raises(AdapterFormatError) as exc_info2:
        list(adapter.parse(data_bytes))
    assert "streaming_json format requires a byte stream" in str(exc_info2.value)


def test_generator_stream(adapter):
    """Test streaming with an Iterable[bytes] rather than IO."""

    def byte_generator():
        yield b"["
        yield b'{"id": 1},'
        yield b'{"id": 2}'
        yield b"]"

    records = list(adapter.parse(byte_generator()))
    assert len(records) == 2
    assert records[0]["id"] == 1
    assert records[1]["id"] == 2


def test_iterable_reader_read_all_mode() -> None:
    """Test that read(-1) returns all buffered and remaining bytes."""
    reader = _IterableBytesReader([b"ab", b"cd"])

    assert reader.read(1) == b"a"
    assert reader.read(-1) == b"bcd"


def test_iterable_reader_rejects_non_bytes_chunk_in_read_all() -> None:
    """Test that read(-1) rejects non-bytes chunks from iterable source."""

    def bad_generator():
        yield b"ok"
        yield "oops"

    reader = _IterableBytesReader(cast(Any, bad_generator()))

    with pytest.raises(TypeError) as exc_info:
        reader.read(-1)

    assert "non-bytes chunk" in str(exc_info.value)


def test_iterable_reader_rejects_non_bytes_chunk_in_sized_read() -> None:
    """Test that read(n) rejects non-bytes chunks from iterable source."""

    def bad_generator():
        yield b"ok"
        yield "oops"

    reader = _IterableBytesReader(cast(Any, bad_generator()))

    with pytest.raises(TypeError) as exc_info:
        reader.read(16)

    assert "non-bytes chunk" in str(exc_info.value)


def test_streaming_json_missing_ijson_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test parse fails with a clear message when ijson dependency is missing."""
    from pfp_runtime.connectors.adapters import streaming_json_adapter as module

    monkeypatch.setattr(module, "ijson", None)
    adapter = StreamingJsonAdapter(
        {"items_path": "item"}, log_pipeline=_LogPipelineStub()  # type: ignore[arg-type]
    )

    with pytest.raises(AdapterFormatError) as exc_info:
        list(adapter.parse(io.BytesIO(b"[]")))

    assert "Missing dependency: 'ijson'" in str(exc_info.value)


def test_safe_ijson_parse_missing_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test internal parser guard raises when ijson is unavailable."""
    from pfp_runtime.connectors.adapters import streaming_json_adapter as module

    monkeypatch.setattr(module, "ijson", None)
    adapter = StreamingJsonAdapter(
        {"items_path": "item"}, log_pipeline=_LogPipelineStub()  # type: ignore[arg-type]
    )

    with pytest.raises(AdapterFormatError) as exc_info:
        list(adapter._safe_ijson_parse(cast(Any, io.BytesIO(b"[]"))))

    assert "Missing dependency: 'ijson'" in str(exc_info.value)


def test_reject_invalid_non_stream_input(adapter) -> None:
    """Test that non-stream and non-iterable input is rejected."""
    with pytest.raises(AdapterFormatError) as exc_info:
        list(adapter.parse(123))  # type: ignore[arg-type]

    assert "Input must implement .read()" in str(exc_info.value)
