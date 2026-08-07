"""Deterministic ID helpers for fixture records."""

from typing import Optional


def padded_index(index: int, width: int = 4) -> str:
    """Return zero-padded deterministic index string.

    Args:
        index: Positive integer index.
        width: Total width for zero padding.

    Returns:
        Zero-padded index text.
    """
    if index < 0 or width <= 0:
        raise ValueError("Invalid index/width for deterministic id")
    return str(index).zfill(width)


def make_item_id(prefix: str = "item", index: int = 1) -> str:
    """Build deterministic ``item_id`` value.

    Args:
        prefix: Stable item prefix.
        index: Sequence index.

    Returns:
        Deterministic item identifier.
    """
    return prefix + "_" + padded_index(index)


def make_sku(index: int = 1, prefix: str = "SKU") -> str:
    """Build deterministic SKU value.

    Args:
        index: Sequence index.
        prefix: Stable SKU prefix.

    Returns:
        Deterministic SKU.
    """
    return prefix + "_" + padded_index(index)


def make_group_id(index: int = 1, prefix: str = "GRP") -> str:
    """Build deterministic variant group identifier.

    Args:
        index: Sequence index.
        prefix: Stable group prefix.

    Returns:
        Deterministic group id.
    """
    return prefix + "_" + padded_index(index)


def coalesce_identifier(
    *,
    item_id: Optional[str],
    sku: Optional[str],
    index: int = 1,
) -> str:
    """Resolve deterministic ID preference for fixture builders.

    Args:
        item_id: Optional explicit item id.
        sku: Optional explicit sku.
        index: Fallback deterministic index.

    Returns:
        Resolved identifier string.
    """
    if item_id:
        return item_id
    if sku:
        return sku
    return make_sku(index=index, prefix="SKU")
