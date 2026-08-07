"""Fixtures package for Story 7.2 test data builders.

This module exports only public fixture factories used by tests, while internal helper modules remain implementation details and are not part of the public API contract.
"""

from typing import List

from .builders.inventory import make_inventory_record
from .builders.price import make_price_record
from .builders.product import make_openai_product_record, make_product_record

__all__: List[str] = [
    "make_inventory_record",
    "make_openai_product_record",
    "make_price_record",
    "make_product_record",
]
