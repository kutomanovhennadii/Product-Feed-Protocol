"""Fixture patch helpers package exports."""

from typing import List

from .boundary_lengths import (
    set_brand_length,
    set_description_length,
    set_max_length,
    set_over_max_length,
    set_path_length,
    set_title_length,
)
from .delete_tombstone import as_delete_tombstone
from .dependency_missing import (
    checkout_without_merchant_links,
    preorder_without_availability_date,
    sale_price_without_window,
)
from .diff_missing_vs_clear import set_clear, set_diff_value, set_missing
from .enum_invalid import (
    set_invalid_availability,
    set_invalid_condition,
    set_invalid_enum,
    set_invalid_gender,
)

__all__: List[str] = [
    "as_delete_tombstone",
    "checkout_without_merchant_links",
    "preorder_without_availability_date",
    "sale_price_without_window",
    "set_brand_length",
    "set_clear",
    "set_description_length",
    "set_diff_value",
    "set_invalid_availability",
    "set_invalid_condition",
    "set_invalid_enum",
    "set_invalid_gender",
    "set_max_length",
    "set_missing",
    "set_over_max_length",
    "set_path_length",
    "set_title_length",
]
