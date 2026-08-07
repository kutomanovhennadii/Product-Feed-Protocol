"""Dependency-missing patch helpers for fixture records."""

from typing import Callable

from ..builders.base import UMRecord, delete_path, set_path

PatchFunc = Callable[[UMRecord], UMRecord]


def sale_price_without_window() -> PatchFunc:
    """Create patch for dependency case: sale_price set, window missing.

    Returns:
        Patch callable.
    """

    def _patch(record: UMRecord) -> UMRecord:
        updated = set_path(
            record,
            "offer.sale_price",
            {
                "amount": "15.99",
                "currency": "USD",
            },
        )
        return delete_path(updated, "offer.sale_price_effective_date")

    return _patch


def checkout_without_merchant_links() -> PatchFunc:
    """Create patch for dependency case: checkout enabled, merchant links missing.

    Returns:
        Patch callable.
    """

    def _patch(record: UMRecord) -> UMRecord:
        updated = set_path(record, "is_eligible_checkout", True)
        updated = delete_path(updated, "merchant.seller_privacy_policy")
        return delete_path(updated, "merchant.seller_tos")

    return _patch


def preorder_without_availability_date() -> PatchFunc:
    """Create patch for dependency case: preorder without date.

    Returns:
        Patch callable.
    """

    def _patch(record: UMRecord) -> UMRecord:
        updated = set_path(record, "inventory.availability", "pre_order")
        return delete_path(updated, "inventory.availability_date")

    return _patch
