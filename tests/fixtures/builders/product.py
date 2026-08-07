"""Product fixture builders for Story 7.2."""

from typing import Any, Dict, Optional, Sequence

from ..ids import coalesce_identifier, make_group_id
from .base import PatchFunc, apply_patch_chain, normalize_mode
from .merchant import make_merchant


def make_product_record(
    *,
    mode: Any = "FULL",
    item_id: Optional[str] = None,
    sku: Optional[str] = None,
    index: int = 1,
    title: str = "Fixture Product",
    description: str = "Fixture product description.",
    brand: str = "Fixture Brand",
    availability: str = "in_stock",
    currency: str = "USD",
    patches: Optional[Sequence[PatchFunc]] = None,
) -> Dict[str, Any]:
    """Build deterministic product UM record with optional patch chain.

    Args:
        mode: Builder mode (FULL/DIFF/DELETE).
        item_id: Optional explicit item id.
        sku: Optional sku fallback identifier.
        index: Deterministic fallback index.
        title: Product title.
        description: Product description.
        brand: Product brand.
        availability: Inventory availability enum.
        currency: Offer currency.
        patches: Optional patch chain.

    Returns:
        UM product record dictionary.
    """
    normalized_mode = normalize_mode(mode)
    resolved_id = coalesce_identifier(item_id=item_id, sku=sku, index=index)

    if normalized_mode == "DELETE":
        base = {
            "item_id": resolved_id,
            "delete": True,
        }
        return apply_patch_chain(base, patches)

    base = {
        "item_id": resolved_id,
        "title": title,
        "description": description,
        "url": "https://example.test/product/" + resolved_id.lower(),
        "brand": brand,
        "image_url": "https://example.test/media/" + resolved_id.lower() + ".jpg",
        "variant": {
            "group_id": make_group_id(index=index),
            "color": "black",
            "size": "M",
            "gender": "unisex",
        },
        "inventory": {
            "availability": availability,
            "inventory_quantity": 10,
        },
        "offer": {
            "price": {
                "amount": "19.99",
                "currency": currency,
            }
        },
        "merchant": make_merchant(),
        "is_eligible_search": True,
        "is_eligible_checkout": False,
        "listing_has_variations": False,
    }

    if normalized_mode == "DIFF":
        diff_base = {
            "item_id": resolved_id,
            "title": title,
            "description": description,
            "url": "https://example.test/product/" + resolved_id.lower(),
            "brand": brand,
            "image_url": "https://example.test/media/" + resolved_id.lower() + ".jpg",
            "variant": {
                "group_id": make_group_id(index=index),
                "color": "black",
                "size": "M",
                "gender": "unisex",
            },
            "offer": {
                "price": {
                    "amount": "19.99",
                    "currency": currency,
                }
            },
            "inventory": {
                "availability": availability,
                "inventory_quantity": 10,
            },
            "merchant": make_merchant(),
            "is_eligible_search": True,
            "is_eligible_checkout": False,
            "listing_has_variations": False,
        }
        return apply_patch_chain(diff_base, patches)

    return apply_patch_chain(base, patches)


def make_openai_product_record(
    *,
    mode: Any = "FULL",
    item_id: Optional[str] = None,
    sku: Optional[str] = None,
    index: int = 1,
    patches: Optional[Sequence[PatchFunc]] = None,
) -> Dict[str, Any]:
    """Build OpenAI-oriented deterministic product record.

    Args:
        mode: Builder mode (FULL/DIFF/DELETE).
        item_id: Optional explicit item id.
        sku: Optional sku fallback identifier.
        index: Deterministic fallback index.
        patches: Optional patch chain.

    Returns:
        OpenAI-oriented UM product record.
    """
    record = make_product_record(
        mode=mode,
        item_id=item_id,
        sku=sku,
        index=index,
        title="Fixture OpenAI Product",
        description="Fixture OpenAI product description.",
        brand="Fixture OpenAI Brand",
        patches=None,
    )

    if normalize_mode(mode) != "DELETE":
        record["is_eligible_search"] = True
        record["is_eligible_checkout"] = True
        record["merchant"] = make_merchant(
            seller_privacy_policy="https://merchant.example.test/privacy",
            seller_tos="https://merchant.example.test/terms",
        )

    return apply_patch_chain(record, patches)
