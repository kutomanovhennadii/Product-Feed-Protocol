from typing import Any, Mapping

import pytest

from pfp_core.ext.ext_types import MISSING, ProducerContext
from pfp_core.ext.mapping.module_mapping_map_tax_code import get_spec


def _lookup_payload() -> Mapping[str, Any]:
    """Return deterministic lookup payload for map_tax_code tests."""
    return {
        "mappings": {
            "Apparel & Accessories": "txcd_20030000",
            "Apparel & Accessories > Clothing": "txcd_20031000",
        },
        "default_taxable": "txcd_99999999",
        "default_exempt": "txcd_00000000",
    }


def _producer_context(
    *, tax_mapping: Mapping[str, Any] | None = None
) -> ProducerContext:
    """Build ProducerContext fixture for map_tax_code prepare tests."""
    return ProducerContext(
        tax_mapping=_lookup_payload() if tax_mapping is None else tax_mapping
    )


def _prepared_args() -> Mapping[str, Any]:
    """Build compiled args by invoking op prepare callback."""
    spec = get_spec()
    assert spec.prepare is not None
    return spec.prepare({}, _producer_context())


def test_module_mapping_map_tax_code_spec_id() -> None:
    """Spec declares correct op_id."""
    assert get_spec().op_id == "map_tax_code"


def test_module_mapping_map_tax_code_spec_has_no_lookup_file_arg() -> None:
    """Spec no longer declares lookup_file in the public args schema."""
    field_names = {field.name for field in get_spec().args_spec.fields}
    assert field_names == {"override_key", "category_key", "taxable_key"}


def test_module_mapping_map_tax_code_prepare_enriches_args() -> None:
    """Prepare injects lookup data and longest-prefix sorted keys."""
    prepared = _prepared_args()
    assert "_lookup_data" in prepared
    assert "_sorted_keys" in prepared
    # Longest prefix first guarantees deterministic best-match lookup.
    assert prepared["_sorted_keys"][0] == "Apparel & Accessories > Clothing"


def test_module_mapping_map_tax_code_prepare_requires_context() -> None:
    """Prepare rejects missing ProducerContext for tax mapping resolution."""
    spec = get_spec()
    assert spec.prepare is not None
    with pytest.raises(ValueError, match="producer context"):
        spec.prepare({}, None)


def test_module_mapping_map_tax_code_prepare_requires_tax_mapping() -> None:
    """Prepare rejects ProducerContext without tax_mapping payload."""
    spec = get_spec()
    assert spec.prepare is not None
    with pytest.raises(ValueError, match="producer context"):
        spec.prepare({}, ProducerContext())


def test_module_mapping_map_tax_code_preserves_missing() -> None:
    """MISSING passes through unchanged."""
    spec = get_spec()
    assert spec.call(MISSING, {"_lookup_data": {}, "_sorted_keys": ()}) is MISSING


def test_module_mapping_map_tax_code_preserves_none() -> None:
    """None passes through unchanged."""
    spec = get_spec()
    assert spec.call(None, {"_lookup_data": {}, "_sorted_keys": ()}) is None


def test_module_mapping_map_tax_code_rejects_non_dict() -> None:
    """Non-dict values raise TypeError."""
    spec = get_spec()
    prepared = _prepared_args()
    with pytest.raises(TypeError):
        spec.call("not-a-dict", prepared)


def test_module_mapping_map_tax_code_override_has_highest_priority() -> None:
    """Explicit tax_code_override wins over category and taxable fallback."""
    spec = get_spec()
    prepared = _prepared_args()
    value = {
        "tax_code_override": "txcd_12345678",
        "tax_category": "Apparel & Accessories > Clothing",
        "taxable": False,
    }
    assert spec.call(value, prepared) == "txcd_12345678"


def test_module_mapping_map_tax_code_longest_prefix_match() -> None:
    """Category lookup uses longest prefix, not first partial match."""
    spec = get_spec()
    prepared = _prepared_args()
    value = {"tax_category": "Apparel & Accessories > Clothing > Activewear"}
    assert spec.call(value, prepared) == "txcd_20031000"


@pytest.mark.parametrize("taxable_value", [False, "false", "0", "no", 0])
def test_module_mapping_map_tax_code_exempt_fallback(
    taxable_value: Any,
) -> None:
    """Falsy taxable values resolve to default exempt code."""
    spec = get_spec()
    prepared = _prepared_args()
    assert spec.call({"taxable": taxable_value}, prepared) == "txcd_00000000"


def test_module_mapping_map_tax_code_taxable_fallback() -> None:
    """Unknown category with taxable true resolves to default taxable code."""
    spec = get_spec()
    prepared = _prepared_args()
    value = {"tax_category": "Unknown > Category", "taxable": True}
    assert spec.call(value, prepared) == "txcd_99999999"
