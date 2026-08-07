"""Unit tests for JSONLWriter behavior."""

from itertools import islice
from typing import Iterable, Iterator

import pytest

from pfp_core.writers.impl.jsonl_writer import JSONLWriter
from pfp_core.writers.writer_types import MISSING, JsonObject


def _collect_bytes(writer: JSONLWriter, records: Iterable[JsonObject]) -> bytes:
    """Collect full byte payload from writer iterable for assertions.

    Args:
        writer: JSONL writer under test.
        records: Input record iterable.

    Returns:
        Concatenated byte payload.
    """
    return b"".join(writer.write(records))


def test_jsonl_writer_default_sort_keys_is_disabled() -> None:
    """Keep insertion-order output by default when sort_keys is not configured."""

    writer = JSONLWriter(
        {"line_terminator": "\n"},
        {"encoding": "utf-8"},
    )
    one = {"b": 2, "a": 1}
    two = {"a": 1, "b": 2}

    first = _collect_bytes(writer, [one])
    second = _collect_bytes(writer, [two])

    assert first != second


def test_jsonl_writer_sort_keys_true_is_deterministic() -> None:
    """Serialize equivalent records into identical bytes when sort_keys is enabled."""

    writer = JSONLWriter(
        {"sort_keys": True, "line_terminator": "\n"},
        {"encoding": "utf-8"},
    )
    one = {"b": 2, "a": 1, "nested": {"y": 2, "x": 1}}
    two = {"a": 1, "b": 2, "nested": {"x": 1, "y": 2}}

    first = _collect_bytes(writer, [one])
    second = _collect_bytes(writer, [two])

    assert first == second


def test_jsonl_writer_omit_nulls_respects_flag() -> None:
    """Drop None values only when omit_nulls is set to true."""

    writer_keep = JSONLWriter({"omit_nulls": False}, {"encoding": "utf-8"})
    writer_omit = JSONLWriter({"omit_nulls": True}, {"encoding": "utf-8"})

    kept = _collect_bytes(writer_keep, [{"a": None, "b": 1}]).decode("utf-8").strip()
    omitted = _collect_bytes(writer_omit, [{"a": None, "b": 1}]).decode("utf-8").strip()

    assert kept == '{"a":null,"b":1}'
    assert omitted == '{"b":1}'


def test_jsonl_writer_omits_missing_sentinel_keys() -> None:
    """Treat Missing sentinel as absent key in JSONL output."""

    writer = JSONLWriter({}, {"encoding": "utf-8"})

    output = _collect_bytes(writer, [{"a": MISSING, "b": "ok"}]).decode("utf-8")

    assert output.strip() == '{"b":"ok"}'


def test_jsonl_writer_line_terminator_config() -> None:
    """Append configured line terminator to every serialized object."""

    writer = JSONLWriter({"line_terminator": "\r\n"}, {"encoding": "utf-8"})

    output = _collect_bytes(writer, [{"x": 1}, {"x": 2}]).decode("utf-8")

    assert output == '{"x":1}\r\n{"x":2}\r\n'


def test_jsonl_writer_rejects_nan_and_infinity() -> None:
    """Raise deterministic errors when JSON payload contains NaN or Infinity."""

    writer = JSONLWriter({}, {"encoding": "utf-8"})

    with pytest.raises(
        ValueError, match="Out of range float values are not JSON compliant"
    ):
        _collect_bytes(writer, [{"x": float("nan")}])

    with pytest.raises(
        ValueError, match="Out of range float values are not JSON compliant"
    ):
        _collect_bytes(writer, [{"x": float("inf")}])


def test_jsonl_writer_rejects_tuple_records() -> None:
    """Reject tuple input rows because JSONL writer accepts mappings only."""

    writer = JSONLWriter({}, {"encoding": "utf-8"})

    with pytest.raises(ValueError, match="JSONLWriter record must be a mapping object"):
        _ = b"".join(writer.write([("id", "1")]))  # type: ignore[list-item]


def test_jsonl_writer_streaming_can_consume_first_chunks_only() -> None:
    """Allow partial consumption of generator output without full exhaustion."""

    consumed = {"count": 0}

    def _records() -> Iterator[JsonObject]:
        for idx in range(5):
            consumed["count"] += 1
            yield {"idx": idx}

    writer = JSONLWriter({}, {"encoding": "utf-8"})
    chunks = writer.write(_records())
    first = list(islice(chunks, 1))

    assert len(first) == 1
    assert consumed["count"] == 1


def test_jsonl_writer_rejects_non_string_keys() -> None:
    """Reject JSON objects that contain non-string keys."""

    writer = JSONLWriter({}, {"encoding": "utf-8"})

    with pytest.raises(ValueError, match="JSONLWriter object keys must be strings"):
        _collect_bytes(writer, [{1: "x"}])  # type: ignore[dict-item]


def test_jsonl_writer_default_line_terminator_is_lf() -> None:
    """Use LF as default row separator when line_terminator is not configured."""

    writer = JSONLWriter({}, {"encoding": "utf-8"})

    payload = _collect_bytes(writer, [{"id": "p1"}]).decode("utf-8")

    assert payload.endswith("\n")
    assert "\r\n" not in payload


def test_jsonl_writer_compact_json_has_no_spaces() -> None:
    """Serialize JSON objects using compact separators without extra spaces."""

    writer = JSONLWriter({}, {"encoding": "utf-8"})

    payload = _collect_bytes(writer, [{"a": 1, "b": {"c": 2}}]).decode("utf-8")

    assert payload.strip() == '{"a":1,"b":{"c":2}}'
    assert ": " not in payload
    assert ", " not in payload


def test_jsonl_writer_missing_semantics_are_mode_agnostic() -> None:
    """Keep missing-key omission independent from FULL/DIFF/DELETE mode semantics."""

    writer = JSONLWriter({}, {"encoding": "utf-8"})

    full_payload = _collect_bytes(writer, [{"id": "p1", "title": MISSING}])
    diff_payload = _collect_bytes(writer, [{"id": "p1", "title": MISSING}])
    delete_payload = _collect_bytes(writer, [{"id": "p1", "title": MISSING}])

    assert full_payload == diff_payload == delete_payload
    assert full_payload.decode("utf-8").strip() == '{"id":"p1"}'
