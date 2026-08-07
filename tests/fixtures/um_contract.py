"""Story 7.2 UM contract note for fixtures.

TARGET_REQUIRED_PATHS is a test-only convention for fixtures; it is not a normative source of truth.
Paths listed here are for FULL-mode fixtures; DIFF/DELETE semantics (missing/clear/tombstone) are handled elsewhere.

Contract source used by fixtures:
- Unified model dataclasses have been removed (Story A5); runtime uses dict-based records.
- Runtime accepts dict-like UM records in schema-driven API/tests.
- Current embedded schemas use these input paths:
  - ``item_id``
  - ``title``
  - ``description``
  - ``url``
  - ``inventory.availability``

Fixtures in this package intentionally build dict-based UM records because this is
the shape used by pipeline tests and baseline fixtures.
"""

from typing import Dict, Tuple

TARGET_REQUIRED_PATHS: Dict[str, Tuple[str, ...]] = {
    "stripe.product": (
        "item_id",
        "title",
    ),
    "stripe.inventory": (
        "item_id",
        "inventory.availability",
    ),
    "stripe.price": (
        "item_id",
        "offer.price.amount",
        "offer.price.currency",
    ),
    "openai.product": (
        "item_id",
        "title",
    ),
}


def required_paths_for_target(target: str) -> Tuple[str, ...]:
    """Return minimal required UM paths for a known fixture target.

    Args:
        target: Canonical target identifier.

    Returns:
        Tuple of minimal required paths.
    """
    if target not in TARGET_REQUIRED_PATHS:
        raise KeyError(f"Unknown fixture target: {target}")
    return TARGET_REQUIRED_PATHS[target]
