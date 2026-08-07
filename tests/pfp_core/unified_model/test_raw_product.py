"""Tests for RawProduct DTOs."""

# pyright: reportMissingImports=false, reportAttributeAccessIssue=false

import pytest

pytest.importorskip(
    "pfp_core.unified_model", reason="unified_model removed: legacy tests disabled"
)

from pfp_core.unified_model.raw_product import (
    RawFulfillment,
    RawInventory,
    RawMerchant,
    RawMoney,
    RawOffer,
    RawProduct,
    RawVariant,
)


def test_raw_product_instantiation() -> None:
    """Test that RawProduct and sub-entities handle string-based data correctly.

    Returns:
        None
    """
    money = RawMoney(amount="12.50", currency="USD")
    offer = RawOffer(price=money, sale_price_start_date="2023-01-01T00:00:00Z")
    variant = RawVariant(listing_has_variations="true", size="XL")
    inventory = RawInventory(inventory_not_tracked="false", inventory_quantity="100")
    fulfillment = RawFulfillment(is_digital="true", free_shipping_threshold=["50.00"])
    merchant = RawMerchant(seller_name="Test Store", seller_url="https://example.com")

    product = RawProduct(
        item_id="123",
        title="Test Product",
        description="A test doc",
        url="https://example.com/p/123",
        delete="true",
        age_restriction="18",
        offer=offer,
        variant=variant,
        inventory=inventory,
        fulfillment=fulfillment,
        merchant=merchant,
    )

    assert product.item_id == "123"
    assert product.delete == "true"
    assert product.age_restriction == "18"
    assert product.offer is not None
    assert product.offer.price is not None
    assert product.offer.price.amount == "12.50"
    assert product.variant is not None
    assert product.variant.listing_has_variations == "true"
    assert product.inventory is not None
    assert product.inventory.inventory_quantity == "100"
    assert product.fulfillment is not None
    assert product.fulfillment.is_digital == "true"
    assert product.merchant is not None
    assert product.merchant.seller_url == "https://example.com"
