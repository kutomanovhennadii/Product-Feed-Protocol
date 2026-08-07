"""End-to-end test: Shopify Bulk → Stripe Catalog CSV via PFPFactory."""

from __future__ import annotations

import csv
import io
from pathlib import Path

from pfp_runtime.shell.factory import PFPFactory

_E2E_DIR = Path(__file__).resolve().parent
_PYTHON_ROOT = _E2E_DIR.parent.parent
_FIXTURE = _E2E_DIR / "fixtures" / "shopify_bulk_input.jsonl"
_INFRA_PATH = _PYTHON_ROOT / "config" / "shopify_bulk" / "infra_shopify_bulk.yaml"
_SHOPIFY_BULK_CONFIG_DIR = _PYTHON_ROOT / "config" / "shopify_bulk"

EXPECTED_COLUMNS = [
    "id",
    "title",
    "description",
    "link",
    "brand",
    "gtin",
    "mpn",
    "image_link",
    "additional_image_link",
    "google_product_category",
    "product_category",
    "condition",
    "weight",
    "item_group_id",
    "item_group_title",
    "color",
    "size",
    "availability",
    "inventory_quantity",
    "price",
    "sale_price",
    "shipping",
    "stripe_product_tax_code",
]


def test_shopify_bulk_e2e(monkeypatch) -> None:
    """Shopify Bulk pipeline returns a complete SUCCESS report and valid CSV payload."""
    monkeypatch.chdir(_SHOPIFY_BULK_CONFIG_DIR)

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
    assert error_diags == [], f"Unexpected error diagnostics: {error_diags}"

    for diag in report.validation_report.diagnostics or ():
        assert diag.code
        assert diag.message

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
    assert metadata.target == "stripe.shopify_bulk"
    assert metadata.schema_version == "1.0.0"
    assert metadata.content_type == "text/csv"
    assert metadata.encoding == "utf-8"
    assert metadata.generated_at is not None

    location = getattr(metadata, "location", None)
    assert location is None
    assert getattr(metadata, "archive_skipped", False) is True
    assert getattr(metadata, "delivery_skipped", False) is True
    assert getattr(metadata, "delivery_status_code", None) is None

    # --- Block 2: CSV header ---
    payload_bytes = b"".join(published.payload)
    csv_text = payload_bytes.decode(metadata.encoding)
    assert csv_text, "CSV artifact is empty"
    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)
    assert len(rows) >= 4, f"Expected header + 3 data rows, got {len(rows)}"

    header = rows[0]
    assert (
        header == EXPECTED_COLUMNS
    ), f"CSV header mismatch.\nExpected: {EXPECTED_COLUMNS}\nActual:   {header}"

    # --- Block 3: Golden record (row 1) ---
    row = dict(zip(header, rows[1]))
    assert row["id"] == "gid://shopify/ProductVariant/123"
    assert row["title"] == "Classic T-Shirt \u2014 Black / M"
    assert row["description"] == "Premium cotton tee."
    assert row["link"] == "https://example.myshopify.com/products/classic-tee"
    assert row["brand"] == "BrandCo"
    assert row["gtin"] == "0123456789012"
    assert row["mpn"] == "CT-BLK-M"
    assert row["image_link"] == "https://cdn.shopify.com/classic-tee-main.jpg"
    assert (
        row["additional_image_link"]
        == "https://cdn.shopify.com/classic-tee-1.jpg,https://cdn.shopify.com/classic-tee-2.jpg"
    )
    assert (
        row["google_product_category"]
        == "Apparel & Accessories > Clothing > Shirts & Tops"
    )
    assert row["product_category"] == "Custom T-Shirts"
    assert row["condition"] == "new"
    assert row["weight"] == "0.3 kg"
    assert row["item_group_id"] == "gid://shopify/Product/456"
    assert row["item_group_title"] == "Classic T-Shirt"
    assert row["color"] == "Black"
    assert row["size"] == "M"
    assert row["availability"] == "in_stock"
    assert row["inventory_quantity"] == "42"
    assert row["price"] == "29.99 USD"
    assert row["sale_price"] == "39.99 USD"
    assert row["shipping"] == "US::Standard Shipping:0-0:5.99 USD"
    assert row["stripe_product_tax_code"] == "txcd_30011000"

    # --- Block 4: Edge case — compareAtPrice is null (row 2) ---
    row2 = dict(zip(header, rows[2]))
    assert row2["id"] == "gid://shopify/ProductVariant/124"
    assert row2["sale_price"] == "__NULL__"
    assert row2["color"] == "White"
    assert row2["size"] == "L"

    # --- Block 5: Edge case — stripe_tax_code_override (row 3) ---
    row3 = dict(zip(header, rows[3]))
    assert row3["id"] == "gid://shopify/ProductVariant/125"
    assert row3["stripe_product_tax_code"] == "txcd_00000000"
    assert row3["availability"] == "out_of_stock"
    assert row3["sale_price"] == "99.99 USD"
