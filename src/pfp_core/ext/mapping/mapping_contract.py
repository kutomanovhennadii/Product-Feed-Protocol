"""Explicit mapping-operations contract registry.

The contract is defined as a mapping from ``op_id`` to lazy ``MappingOpSpec``
builders. The registry represents the allowed set of mapping operations.
"""

from typing import Callable, Dict, List

from pfp_core.ext.ext_types import MappingOpSpec
from pfp_core.ext.mapping.module_mapping_bool_to_availability import (
    get_spec as bool_to_availability_spec,
)
from pfp_core.ext.mapping.module_mapping_default_value import (
    get_spec as default_value_spec,
)
from pfp_core.ext.mapping.module_mapping_emit_if_present import (
    get_spec as emit_if_present_spec,
)
from pfp_core.ext.mapping.module_mapping_emit_null_if_missing import (
    get_spec as emit_null_if_missing_spec,
)
from pfp_core.ext.mapping.module_mapping_format_date import get_spec as format_date_spec
from pfp_core.ext.mapping.module_mapping_format_datetime_utc import (
    get_spec as format_datetime_utc_spec,
)
from pfp_core.ext.mapping.module_mapping_format_money import (
    get_spec as format_money_spec,
)
from pfp_core.ext.mapping.module_mapping_format_price import (
    get_spec as format_price_spec,
)
from pfp_core.ext.mapping.module_mapping_format_shipping import (
    get_spec as format_shipping_spec,
)
from pfp_core.ext.mapping.module_mapping_get_path import get_spec as get_path_spec
from pfp_core.ext.mapping.module_mapping_int_to_availability import (
    get_spec as int_to_availability_spec,
)
from pfp_core.ext.mapping.module_mapping_lower import get_spec as lower_spec
from pfp_core.ext.mapping.module_mapping_map_tax_code import (
    get_spec as map_tax_code_spec,
)
from pfp_core.ext.mapping.module_mapping_normalize_whitespace import (
    get_spec as normalize_whitespace_spec,
)
from pfp_core.ext.mapping.module_mapping_omit_if_missing import (
    get_spec as omit_if_missing_spec,
)
from pfp_core.ext.mapping.module_mapping_parse_date import get_spec as parse_date_spec
from pfp_core.ext.mapping.module_mapping_regex_extract import (
    get_spec as regex_extract_spec,
)
from pfp_core.ext.mapping.module_mapping_round_decimal import (
    get_spec as round_decimal_spec,
)
from pfp_core.ext.mapping.module_mapping_strip_html import get_spec as strip_html_spec
from pfp_core.ext.mapping.module_mapping_strip_suffix import (
    get_spec as strip_suffix_spec,
)
from pfp_core.ext.mapping.module_mapping_to_bool import get_spec as to_bool_spec
from pfp_core.ext.mapping.module_mapping_to_decimal import get_spec as to_decimal_spec
from pfp_core.ext.mapping.module_mapping_to_int import get_spec as to_int_spec
from pfp_core.ext.mapping.module_mapping_to_str import get_spec as to_str_spec
from pfp_core.ext.mapping.module_mapping_trim import get_spec as trim_spec
from pfp_core.ext.mapping.module_mapping_truncate import get_spec as truncate_spec
from pfp_core.ext.mapping.module_mapping_upper import get_spec as upper_spec

MAPPING_OP_REGISTRY: Dict[str, Callable[[], MappingOpSpec]] = {
    "default_value": default_value_spec,
    "get_path": get_path_spec,
    "to_str": to_str_spec,
    "to_int": to_int_spec,
    "to_decimal": to_decimal_spec,
    "to_bool": to_bool_spec,
    "bool_to_availability": bool_to_availability_spec,
    "int_to_availability": int_to_availability_spec,
    "trim": trim_spec,
    "lower": lower_spec,
    "upper": upper_spec,
    "normalize_whitespace": normalize_whitespace_spec,
    "parse_date": parse_date_spec,
    "format_date": format_date_spec,
    "format_datetime_utc": format_datetime_utc_spec,
    "round_decimal": round_decimal_spec,
    "format_money": format_money_spec,
    "format_price": format_price_spec,
    "format_shipping": format_shipping_spec,
    "map_tax_code": map_tax_code_spec,
    "regex_extract": regex_extract_spec,
    "strip_html": strip_html_spec,
    "strip_suffix": strip_suffix_spec,
    "truncate": truncate_spec,
    "emit_if_present": emit_if_present_spec,
    "emit_null_if_missing": emit_null_if_missing_spec,
    "omit_if_missing": omit_if_missing_spec,
}


def get_mapping_op_spec(op_id: str) -> MappingOpSpec:
    """Return mapping operation spec by contract operation id."""
    builder = MAPPING_OP_REGISTRY.get(op_id)
    if builder is None:
        raise ValueError(f"Unknown mapping op_id: {op_id}")
    return builder()


def list_mapping_op_ids() -> List[str]:
    """Return sorted mapping operation ids declared by the contract."""
    return sorted(MAPPING_OP_REGISTRY.keys())


def _validate_mapping_op_registry() -> None:
    """Validate op-id mapping integrity between registry keys and specs."""
    for op_id, builder in MAPPING_OP_REGISTRY.items():
        spec = builder()
        if not spec.op_id:
            raise ValueError(
                f"Mapping op registry mismatch: key={op_id!r}, spec.op_id is empty"
            )
        if spec.op_id != op_id:
            raise ValueError(
                f"Mapping op registry mismatch: key={op_id!r}, spec.op_id={spec.op_id!r}"
            )


_validate_mapping_op_registry()
