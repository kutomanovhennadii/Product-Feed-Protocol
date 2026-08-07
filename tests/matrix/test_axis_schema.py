"""Schema-axis matrix coverage for Phase 10.

Returns:
    None.
"""

from __future__ import annotations

import pytest

from pfp_runtime.publishing.contracts import PublishMetadata
from tests.matrix._axis_helpers import (
    MATRIX_ROOT,
    assert_success_baseline,
)
from tests.matrix.matrix_runner import run_matrix_cell

_SCHEMA_CASES = (
    pytest.param(
        "infra_stripe_product_feed.yaml",
        "stripe.product_feed.jsonl",
        "stripe.product_feed.csv",
        "stripe.product_feed",
        "text/csv",
        ".csv",
        id="stripe-product-feed",
    ),
    pytest.param(
        "infra_stripe_inventory_price_feed.yaml",
        "stripe.inventory_price_feed.jsonl",
        "stripe.inventory_price_feed.csv",
        "stripe.inventory_price_feed",
        "text/csv",
        ".csv",
        id="stripe-inventory-price-feed",
    ),
    pytest.param(
        "infra_shopify_bulk.yaml",
        "stripe.shopify_bulk.jsonl",
        "stripe.shopify_bulk.csv",
        "stripe.shopify_bulk",
        "text/csv",
        ".csv",
        id="shopify-bulk",
    ),
    pytest.param(
        "infra_shopify_delete.yaml",
        "stripe.shopify_delete.json",
        "stripe.shopify_delete.csv",
        "stripe.shopify_delete",
        "text/csv",
        ".csv",
        id="shopify-delete",
    ),
    pytest.param(
        "infra_shopify_inventory.yaml",
        "stripe.shopify_inventory.json",
        "stripe.shopify_inventory.csv",
        "stripe.shopify_inventory",
        "text/csv",
        ".csv",
        id="shopify-inventory",
    ),
    pytest.param(
        "infra_shopify_realtime.yaml",
        "stripe.shopify_realtime.json",
        "stripe.shopify_realtime.csv",
        "stripe.shopify_realtime",
        "text/csv",
        ".csv",
        id="shopify-realtime",
    ),
    pytest.param(
        "infra_openai_product_feed.yaml",
        "openai.product_feed.jsonl",
        "openai.product_feed.jsonl",
        "openai.product_feed",
        "application/x-ndjson",
        ".jsonl",
        id="openai-product-feed",
    ),
)


@pytest.mark.parametrize(
    (
        "infra_name",
        "fixture_name",
        "golden_name",
        "expected_target",
        "expected_content_type",
        "expected_extension",
    ),
    _SCHEMA_CASES,
)
def test_schema_axis_matches_target_specific_golden(
    infra_name: str,
    fixture_name: str,
    golden_name: str,
    expected_target: str,
    expected_content_type: str,
    expected_extension: str,
) -> None:
    """Each schema target must emit its committed golden artifact.

    Args:
        infra_name: Matrix infra file selecting the target schema.
        fixture_name: Source fixture path for the case.
        golden_name: Expected committed output filename.
        expected_target: Protocol id stored in produced metadata.
        expected_content_type: MIME type emitted by the producer.
        expected_extension: Deterministic filename suffix for the target.

    Returns:
        None.
    """
    infra_path = MATRIX_ROOT / "infra" / "schema" / infra_name
    fixture_path = MATRIX_ROOT / "fixtures" / "schema" / fixture_name
    golden_path = MATRIX_ROOT / "golden" / "schema" / golden_name

    result = run_matrix_cell(infra_path=infra_path, fixture_path=fixture_path)

    assert_success_baseline(
        result,
        golden_path=golden_path,
        expected_target=expected_target,
        expected_content_type=expected_content_type,
        expected_input_count=None,
    )

    metadata = result.report.artifacts[0].metadata
    assert isinstance(metadata, PublishMetadata)
    assert metadata.schema_version == "1.0.0"
    assert metadata.filename_hint is not None
    assert metadata.filename_hint.endswith(expected_extension)
    assert metadata.archive_skipped is True
    assert metadata.delivery_skipped is True
    assert metadata.delivery_status_code is None
