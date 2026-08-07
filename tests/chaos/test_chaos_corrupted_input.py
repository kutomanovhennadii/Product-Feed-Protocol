"""Chaos tests for corrupted input payloads.

The current runtime consumes ingestion lazily while publish renders the
artifact payload, so ingestion iterator failures surface as ``PUBLISH.ERROR``
instead of the architecturally preferable ``INGESTION_EXTRACT`` attribution.
These tests document that observed behavior without treating it as the target
architecture.
"""

from __future__ import annotations

import pytest

from tests.chaos._helpers import (
    build_worker,
    csv_payload_text,
    expected_header,
    jsonl_max_line_bytes,
    write_minimal_infra,
)

pytestmark = [pytest.mark.chaos, pytest.mark.timeout(120)]


def test_corrupted_jsonl_truncated_line(tmp_path) -> None:
    """Truncated JSONL must return a structured failed report."""
    worker = build_worker(write_minimal_infra(tmp_path, input_format="jsonl"))

    report = worker.run(b'{"item_id":"SKU-1","title":"OK"}\n{"item_id":"SKU-2","title"')

    assert report.status == "FAILED"
    assert report.failed_step == "PUBLISH"
    assert report.reason_code == "PUBLISH.ERROR"
    assert report.error_type == "IngestionExtractIterationError"
    assert "decode json payload" in report.message.lower()


def test_corrupted_invalid_utf8(tmp_path) -> None:
    """Broken UTF-8 must return a structured failed report."""
    worker = build_worker(write_minimal_infra(tmp_path, input_format="jsonl"))

    report = worker.run(b'\xff\xfe{"item_id":"SKU-1"}')

    assert report.status == "FAILED"
    assert report.failed_step == "PUBLISH"
    assert report.reason_code == "PUBLISH.ERROR"
    assert report.error_type == "IngestionExtractIterationError"
    assert "utf-8" in report.message.lower()


def test_corrupted_empty_input(tmp_path) -> None:
    """Empty JSONL is a structured boundary case with header-only output."""
    worker = build_worker(write_minimal_infra(tmp_path, input_format="jsonl"))

    report = worker.run(b"")

    assert report.status == "SUCCESS"
    assert report.counters["input_items_count"] == 0
    assert report.counters["processed"] == 0
    assert report.counters["error"] == 0
    assert len(report.artifacts) == 1
    assert csv_payload_text(report) == expected_header()


def test_corrupted_oversized_jsonl_line(tmp_path) -> None:
    """Oversized JSONL lines must return a structured failed report."""
    worker = build_worker(write_minimal_infra(tmp_path, input_format="jsonl"))
    payload = b'{"id":"' + (b"X" * (jsonl_max_line_bytes() + 1)) + b'"}\n'

    report = worker.run(payload)

    assert report.status == "FAILED"
    assert report.failed_step == "PUBLISH"
    assert report.reason_code == "PUBLISH.ERROR"
    assert report.error_type == "IngestionExtractIterationError"
    assert "exceeds maximum limit" in report.message.lower()
