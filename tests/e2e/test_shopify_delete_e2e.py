"""End-to-end test: Shopify Product Delete webhook → Stripe Catalog Delete CSV via PFPFactory."""

from __future__ import annotations

import csv
import io
from pathlib import Path

from pfp_runtime.shell.factory import PFPFactory

_E2E_DIR = Path(__file__).resolve().parent
_PYTHON_ROOT = _E2E_DIR.parent.parent
_FIXTURE = _E2E_DIR / "fixtures" / "shopify_delete_input.json"
_INFRA_PATH = _PYTHON_ROOT / "config" / "shopify_delete" / "infra_shopify_delete.yaml"
_SHOPIFY_DELETE_CONFIG_DIR = _PYTHON_ROOT / "config" / "shopify_delete"

EXPECTED_COLUMNS = [
    "id",
    "delete",
]


def test_shopify_delete_e2e(monkeypatch) -> None:
    """Shopify Delete pipeline returns a complete SUCCESS report and valid CSV payload."""
    monkeypatch.chdir(_SHOPIFY_DELETE_CONFIG_DIR)

    factory = PFPFactory()
    worker = factory.build_worker(infra_path=_INFRA_PATH)
    report = worker.run(_FIXTURE.read_bytes())

    # --- Block 1: Report quality ---
    assert report.status == "SUCCESS", (
        f"Pipeline failed: step={report.failed_step}, "
        f"reason={report.reason_code}, msg={report.message}"
    )
    assert report.failed_step == ""
    assert report.reason_code == ""
    assert report.message == "Pipeline completed successfully"
    assert report.error_type is None
    assert isinstance(report.timings, dict)
    assert report.timings != {}
    assert "total" in report.timings
    assert report.timings["total"] >= 0
    assert len(report.artifacts) >= 1
    assert report.run_id is None
    assert report.correlation_id is None

    for key in ("ingestion_extract", "core", "publish"):
        assert key in report.timings
        assert report.timings[key] >= 0

    error_diags = [
        d
        for d in (report.validation_report.diagnostics or ())
        if d.severity in ("ERROR", "FATAL")
    ]
    # Record 3 (missing id) is dropped at connector_mapper level
    # (required source field missing), so no validation-level error diagnostics.
    assert error_diags == [], f"Unexpected error diagnostics: {error_diags}"
    assert (report.validation_report.diagnostics or []) == []

    counters = report.counters
    assert isinstance(counters, dict)
    assert counters.get("error", 0) == 0
    artifacts_count = counters.get("artifacts_count", 0)
    processed_count = counters.get("processed", 0)
    dropped_count = counters.get("dropped", 0)
    input_items_count = counters.get("input_items_count")
    assert isinstance(artifacts_count, int)
    assert isinstance(processed_count, int)
    assert isinstance(dropped_count, int)
    assert artifacts_count >= 1
    assert processed_count >= 0
    assert dropped_count >= 0
    if input_items_count is not None:
        assert isinstance(input_items_count, int)
        assert processed_count <= input_items_count
    by_severity = counters.get("diagnostics_count_by_severity", {})
    assert isinstance(by_severity, dict)
    for sev in ("ERROR", "WARN", "INFO"):
        assert sev in by_severity

    published = report.artifacts[0]
    metadata = published.metadata
    assert metadata.target == "stripe.shopify_delete"
    assert metadata.schema_version == "1.0.0"
    assert metadata.content_type == "text/csv"
    assert metadata.encoding == "utf-8"
    assert metadata.generated_at is not None

    location = getattr(metadata, "location", None)
    assert location is None
    assert getattr(metadata, "archive_skipped", False) is True
    assert getattr(metadata, "delivery_skipped", False) is True
    assert getattr(metadata, "delivery_status_code", None) is None

    # --- Block 2: CSV header (2 columns) ---
    payload_bytes = b"".join(published.payload)
    csv_text = payload_bytes.decode(metadata.encoding)
    assert csv_text, "CSV artifact is empty"
    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)
    # fixture has 3 records: rows 1-2 valid, row 3 missing id → dropped
    assert len(rows) >= 3, f"Expected header + 2 data rows, got {len(rows)}"

    header = rows[0]
    assert (
        header == EXPECTED_COLUMNS
    ), f"CSV header mismatch.\nExpected: {EXPECTED_COLUMNS}\nActual:   {header}"

    # --- Block 3: Golden record (row 1) ---
    row1 = dict(zip(header, rows[1]))
    assert row1["id"] == "gid://shopify/Product/123456789"
    assert row1["delete"] == "true"

    # --- Block 4: Second valid record (row 2) ---
    row2 = dict(zip(header, rows[2]))
    assert row2["id"] == "gid://shopify/Product/987654321"
    assert row2["delete"] == "true"

    # --- Block 5: drop_invalid — record without id is dropped ---
    # Record 3 has no id → connector drops it (required source field missing).
    # It never reaches core, so no ID exists to check against.
    assert (
        len(rows) == 3
    ), f"Expected exactly header + 2 data rows (record 3 dropped), got {len(rows)}"
