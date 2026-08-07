"""Tests for pfp_core.unified_model.merchant."""

# pyright: reportMissingImports=false, reportAttributeAccessIssue=false

import pytest

pytest.importorskip(
    "pfp_core.unified_model", reason="unified_model removed: legacy tests disabled"
)

from pfp_core.unified_model.merchant import Merchant


def test_merchant_stores_required_fields() -> None:
    """Store seller_name and seller_url values without additional normalization."""
    merchant = Merchant(seller_name="Seller", seller_url="https://seller.example")
    assert merchant.seller_name == "Seller"
    assert merchant.seller_url == "https://seller.example"
