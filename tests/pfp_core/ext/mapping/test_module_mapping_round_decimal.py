from decimal import Decimal

import pytest

from pfp_core.ext.ext_types import MISSING
from pfp_core.ext.mapping.module_mapping_round_decimal import get_spec
from tests.pfp_core.ext.mapping._helpers import call_spec


def test_module_mapping_round_decimal_rounds_deterministically() -> None:
    """round_decimal rounds string and Decimal values using decimals arg."""
    spec = get_spec()
    assert spec.op_id == "round_decimal"
    assert call_spec(spec, "12.345", {"decimals": 2}) == Decimal("12.35")
    assert call_spec(spec, Decimal("1.2345"), {"decimals": 3}) == Decimal("1.235")
    assert call_spec(spec, MISSING, {"decimals": 2}) is MISSING
    assert call_spec(spec, None, {"decimals": 2}) is None


def test_module_mapping_round_decimal_rejects_invalid_args_or_values() -> None:
    """round_decimal raises ValueError for invalid decimals or input values."""
    spec = get_spec()
    assert spec.op_id == "round_decimal"
    with pytest.raises(ValueError):
        call_spec(spec, "12.3", {"decimals": -1})

    with pytest.raises(ValueError):
        call_spec(spec, "12.3", {"decimals": "2"})

    with pytest.raises(ValueError):
        call_spec(spec, "x", {"decimals": 2})
