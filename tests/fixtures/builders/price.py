"""Price fixture builder for Story 7.2."""

from typing import Any, Dict, Optional, Sequence

from ..ids import coalesce_identifier
from .base import PatchFunc, apply_patch_chain, normalize_mode


def make_price_record(
    *,
    mode: Any = "FULL",
    item_id: Optional[str] = None,
    sku: Optional[str] = None,
    index: int = 1,
    amount: str = "19.99",
    currency: str = "USD",
    sale_amount: Optional[str] = None,
    sale_window: Optional[str] = None,
    patches: Optional[Sequence[PatchFunc]] = None,
) -> Dict[str, Any]:
    """Build deterministic price-focused UM record.

    Args:
        mode: Builder mode (FULL/DIFF/DELETE).
        item_id: Optional explicit item id.
        sku: Optional sku fallback identifier.
        index: Deterministic fallback index.
        amount: Base price amount.
        currency: Base price currency.
        sale_amount: Optional sale price amount.
        sale_window: Optional sale effective date window.
        patches: Optional patch chain.

    Returns:
        Price-focused UM record.
    """
    normalized_mode = normalize_mode(mode)
    resolved_id = coalesce_identifier(item_id=item_id, sku=sku, index=index)

    if normalized_mode == "DELETE":
        base = {"item_id": resolved_id, "delete": True}
        return apply_patch_chain(base, patches)

    offer_payload: Dict[str, Any] = {
        "price": {
            "amount": amount,
            "currency": currency,
        }
    }
    if sale_amount is not None:
        offer_payload["sale_price"] = {
            "amount": sale_amount,
            "currency": currency,
        }
    if sale_window is not None:
        offer_payload["sale_price_effective_date"] = sale_window

    if normalized_mode == "DIFF":
        base = {"item_id": resolved_id, "offer": offer_payload}
        return apply_patch_chain(base, patches)

    base = {
        "item_id": resolved_id,
        "offer": offer_payload,
    }
    return apply_patch_chain(base, patches)
