"""Inventory fixture builder for Story 7.2."""

from typing import Any, Dict, Optional, Sequence

from ..ids import coalesce_identifier
from .base import PatchFunc, apply_patch_chain, normalize_mode


def make_inventory_record(
    *,
    mode: Any = "FULL",
    item_id: Optional[str] = None,
    sku: Optional[str] = None,
    index: int = 1,
    availability: str = "in_stock",
    availability_date: Optional[str] = None,
    inventory_quantity: int = 10,
    patches: Optional[Sequence[PatchFunc]] = None,
) -> Dict[str, Any]:
    """Build deterministic inventory-focused UM record.

    Args:
        mode: Builder mode (FULL/DIFF/DELETE).
        item_id: Optional explicit item id.
        sku: Optional sku fallback identifier.
        index: Deterministic fallback index.
        availability: Inventory availability value.
        availability_date: Optional availability date.
        inventory_quantity: Quantity value.
        patches: Optional patch chain.

    Returns:
        Inventory-focused UM record.
    """
    normalized_mode = normalize_mode(mode)
    resolved_id = coalesce_identifier(item_id=item_id, sku=sku, index=index)

    if normalized_mode == "DELETE":
        base = {"item_id": resolved_id, "delete": True}
        return apply_patch_chain(base, patches)

    inventory_payload: Dict[str, Any] = {
        "availability": availability,
        "inventory_quantity": inventory_quantity,
    }
    if availability_date is not None:
        inventory_payload["availability_date"] = availability_date

    if normalized_mode == "DIFF":
        base = {"item_id": resolved_id, "inventory": inventory_payload}
        return apply_patch_chain(base, patches)

    base = {
        "item_id": resolved_id,
        "inventory": inventory_payload,
    }
    return apply_patch_chain(base, patches)
