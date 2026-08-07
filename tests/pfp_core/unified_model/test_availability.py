"""Tests for pfp_core.unified_model.availability."""

# pyright: reportMissingImports=false, reportAttributeAccessIssue=false

import pytest

pytest.importorskip(
    "pfp_core.unified_model", reason="unified_model removed: legacy tests disabled"
)

from pfp_core.unified_model.availability import Fulfillment, Inventory


def test_inventory_accepts_optional_fields() -> None:
    """Create Inventory with optional availability metadata preserved as provided."""
    inventory = Inventory(availability="in_stock", inventory_quantity=10)
    assert inventory.availability == "in_stock"
    assert inventory.inventory_quantity == 10


def test_fulfillment_accepts_shipping_collection() -> None:
    """Create Fulfillment with a shipping collection and keep original structure."""
    fulfillment = Fulfillment(shipping=["US::Ground:5.00 USD"])
    assert fulfillment.shipping == ["US::Ground:5.00 USD"]
