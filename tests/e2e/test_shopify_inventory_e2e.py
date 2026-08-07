"""End-to-end test: Shopify Inventory webhook → Stripe Inventory Feed CSV via PFPFactory."""

from __future__ import annotations

import csv
import io
from pathlib import Path

from pfp_runtime.shell.factory import PFPFactory

_E2E_DIR = Path(__file__).resolve().parent
_PYTHON_ROOT = _E2E_DIR.parent.parent
_FIXTURE = _E2E_DIR / "fixtures" / "shopify_inventory_input.json"
_INFRA_PATH = (
    _PYTHON_ROOT / "config" / "shopify_inventory" / "infra_shopify_inventory.yaml"
)
_SHOPIFY_INVENTORY_CONFIG_DIR = _PYTHON_ROOT / "config" / "shopify_inventory"

EXPECTED_COLUMNS = [
    "id",
    "inventory_quantity",
    "availability",
]


def test_shopify_inventory_e2e(monkeypatch) -> None:
    """Shopify Inventory pipeline returns a complete SUCCESS report and valid CSV payload."""
    monkeypatch.chdir(_SHOPIFY_INVENTORY_CONFIG_DIR)

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
    # Record 4 (missing inventory_item_id) is dropped at connector_mapper level
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
    assert metadata.target == "stripe.shopify_inventory"
    assert metadata.schema_version == "1.0.0"
    assert metadata.content_type == "text/csv"
    assert metadata.encoding == "utf-8"
    assert metadata.generated_at is not None

    location = getattr(metadata, "location", None)
    assert location is None
    assert getattr(metadata, "archive_skipped", False) is True
    assert getattr(metadata, "delivery_skipped", False) is True
    assert getattr(metadata, "delivery_status_code", None) is None

    # --- Block 2: CSV header (3 columns) ---
    payload_bytes = b"".join(published.payload)
    csv_text = payload_bytes.decode(metadata.encoding)
    assert csv_text, "CSV artifact is empty"
    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)
    # fixture has 4 records: rows 1-3 valid, row 4 missing inventory_item_id → dropped
    assert len(rows) >= 4, f"Expected header + 3 data rows, got {len(rows)}"

    header = rows[0]
    assert (
        header == EXPECTED_COLUMNS
    ), f"CSV header mismatch.\nExpected: {EXPECTED_COLUMNS}\nActual:   {header}"

    # --- Block 3: Golden record (row 1 — available=42 → in_stock) ---
    row1 = dict(zip(header, rows[1]))
    assert row1["id"] == "48513488879793"
    assert row1["inventory_quantity"] == "42"
    assert row1["availability"] == "in_stock"

    # --- Block 4: Edge case — available == 0 → out_of_stock (row 2) ---
    row2 = dict(zip(header, rows[2]))
    assert row2["id"] == "48513488879794"
    assert row2["inventory_quantity"] == "0"
    assert row2["availability"] == "out_of_stock"

    # --- Block 5: Edge case — available < 0 (oversell) → out_of_stock (row 3) ---
    row3 = dict(zip(header, rows[3]))
    assert row3["id"] == "48513488879795"
    assert row3["inventory_quantity"] == "-3"
    assert row3["availability"] == "out_of_stock"

    # --- Block 6: drop_invalid — record without inventory_item_id is dropped ---
    # Record 4 has no inventory_item_id → connector drops it (required source
    # field missing).  It never reaches core, so no ID exists to check against.
    assert (
        len(rows) == 4
    ), f"Expected exactly header + 3 data rows (record 4 dropped), got {len(rows)}"
