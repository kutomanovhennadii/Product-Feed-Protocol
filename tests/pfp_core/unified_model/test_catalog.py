"""Tests for pfp_core.unified_model.catalog."""

# pyright: reportMissingImports=false, reportAttributeAccessIssue=false

import pytest

pytest.importorskip(
    "pfp_core.unified_model", reason="unified_model removed: legacy tests disabled"
)

from pfp_core.unified_model import Product
from pfp_core.unified_model.catalog import Offer, Variant


def test_product_requires_string_id() -> None:
    """Reject product construction when item_id is empty."""
    with pytest.raises(ValueError):
        Product(item_id="", title="Title", description="Desc", url="https://x.test")


def test_catalog_entities_import_and_construct() -> None:
    """Construct Offer and Variant from canonical catalog module paths."""
    offer = Offer()
    variant = Variant()
    assert offer.price is None
    assert variant.group_id is None
