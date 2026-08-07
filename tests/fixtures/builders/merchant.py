"""Merchant fixture builder utilities."""

from typing import Dict, Optional


def make_merchant(
    *,
    seller_name: str = "Fixture Merchant",
    seller_url: str = "https://merchant.example.test",
    seller_privacy_policy: str = "https://merchant.example.test/privacy",
    seller_tos: str = "https://merchant.example.test/terms",
    marketplace_seller: Optional[str] = None,
) -> Dict[str, Optional[str]]:
    """Build deterministic merchant mapping without any I/O.

    Args:
        seller_name: Merchant display name.
        seller_url: Merchant URL.
        seller_privacy_policy: Merchant privacy policy URL.
        seller_tos: Merchant terms URL.
        marketplace_seller: Optional marketplace seller name.

    Returns:
        Deterministic merchant dictionary.
    """
    return {
        "seller_name": seller_name,
        "seller_url": seller_url,
        "seller_privacy_policy": seller_privacy_policy,
        "seller_tos": seller_tos,
        "marketplace_seller": marketplace_seller,
    }
