"""Chaos tests for producer-side validation and record-shape failures."""

from __future__ import annotations

import json

import pytest

from tests.chaos._helpers import (
    build_worker,
    csv_payload_text,
    diagnostics_by_severity,
    expected_header,
    write_producer_validation_infra,
)

pytestmark = [pytest.mark.chaos, pytest.mark.timeout(120)]


def test_all_records_missing_required_field(tmp_path) -> None:
    """A missing required title stops the current build on the first item."""
    worker = build_worker(write_producer_validation_infra(tmp_path))
    payload = _jsonl_payload(
        {"item_id": "SKU-1"},
        {"item_id": "SKU-2"},
        {"item_id": "SKU-3"},
        {"item_id": "SKU-4"},
        {"item_id": "SKU-5"},
    )

    report = worker.run(payload)

    _assert_current_fail_stop_contract(report)
    assert report.counters["input_items_count"] == 1
    assert report.counters["processed"] == 1
    assert diagnostics_by_severity(report, "ERROR") == ["BUILD.FAIL_STOP"]
    assert diagnostics_by_severity(report, "INFO") == ["STRIPE_TITLE_REQUIRED"]


def test_mixed_valid_and_invalid_records(tmp_path) -> None:
    """Once one producer-side FAIL is hit, trailing records are not consumed."""
    worker = build_worker(write_producer_validation_infra(tmp_path))
    payload = _jsonl_payload(
        {"item_id": "SKU-1"},
        {"item_id": "SKU-2", "title": "B"},
        {"item_id": "SKU-3", "title": "C"},
        {"item_id": "SKU-4"},
        {"item_id": "SKU-5", "title": "E"},
        {"item_id": "SKU-6"},
    )

    report = worker.run(payload)

    _assert_current_fail_stop_contract(report)
    assert report.counters["input_items_count"] == 1
    assert report.counters["processed"] == 1
    assert diagnostics_by_severity(report, "ERROR") == ["BUILD.FAIL_STOP"]
    assert diagnostics_by_severity(report, "INFO") == ["STRIPE_TITLE_REQUIRED"]


def test_malformed_value_types(tmp_path) -> None:
    """Malformed title types currently collapse into the same title-required fail-stop."""
    worker = build_worker(write_producer_validation_infra(tmp_path))
    payload = _jsonl_payload(
        {"item_id": "SKU-1", "title": ["array", "instead", "of", "string"]},
        {"item_id": "SKU-2", "title": 12345},
    )

    report = worker.run(payload)

    _assert_current_fail_stop_contract(report)
    codes = [diagnostic.code for diagnostic in report.validation_report.diagnostics]
    assert diagnostics_by_severity(report, "ERROR") == ["BUILD.FAIL_STOP"]
    assert diagnostics_by_severity(report, "INFO") == ["STRIPE_TITLE_REQUIRED"]
    assert "SCHEMA_INVALID_TYPE" not in codes
    assert "SCHEMA_TYPE_MISMATCH" not in codes


def _assert_current_fail_stop_contract(report) -> None:
    """Assert the observed producer chaos contract of the current runtime.

    The current manifest builder leaves fail_on_error_diagnostics disabled, so
    producer-side FAIL decisions surface as SUCCESS reports with BUILD.FAIL_STOP
    diagnostics and a header-only artifact rather than CORE_BUILD failures.
    """
    codes = {diagnostic.code for diagnostic in report.validation_report.diagnostics}

    assert report.status == "SUCCESS"
    assert report.failed_step == ""
    assert report.reason_code == ""
    assert report.error_type is None
    assert report.counters["artifacts_count"] == 1
    assert report.counters["error"] == 0
    assert csv_payload_text(report) == expected_header()
    assert codes >= {"BUILD.FAIL_STOP", "STRIPE_TITLE_REQUIRED"}


def _jsonl_payload(*records: object) -> bytes:
    """Serialize records into one JSONL payload."""
    return ("\n".join(json.dumps(record) for record in records) + "\n").encode("utf-8")
