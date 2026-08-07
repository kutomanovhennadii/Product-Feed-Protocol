import pytest

from pfp_core.ext.ext_types import MISSING
from pfp_core.ext.mapping.module_mapping_format_money import get_spec
from tests.pfp_core.ext.mapping._helpers import call_spec


def test_module_mapping_format_money_and_args_validation() -> None:
    """format_money is Decimal-based and validates configuration arguments."""
    spec = get_spec()
    assert spec.op_id == "format_money"
    assert (
        call_spec(
            spec,
            "12.345",
            {"decimals": 2, "pattern": "{amount} {currency}", "currency": "USD"},
        )
        == "12.35 USD"
    )

    with pytest.raises(ValueError):
        call_spec(spec, "1", {"decimals": "2", "pattern": "{amount}"})

    with pytest.raises(ValueError):
        call_spec(spec, "1", {"decimals": 2, "pattern": ""})

    with pytest.raises(ValueError):
        call_spec(
            spec,
            "1",
            {"decimals": 2, "pattern": "{amount}", "currency": 123},
        )

    with pytest.raises(ValueError):
        call_spec(
            spec,
            "not-a-number",
            {"decimals": 2, "pattern": "{amount}"},
        )

    with pytest.raises(ValueError):
        call_spec(
            spec,
            "1",
            {"decimals": 2, "pattern": "{missing}", "currency": "USD"},
        )

    assert (
        call_spec(
            spec,
            MISSING,
            {"decimals": 2, "pattern": "{amount}", "currency": "USD"},
        )
        is MISSING
    )
    assert (
        call_spec(
            spec,
            None,
            {"decimals": 2, "pattern": "{amount}", "currency": "USD"},
        )
        is None
    )
