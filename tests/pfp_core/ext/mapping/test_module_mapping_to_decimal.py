from decimal import Decimal

import pytest

from pfp_core.ext.ext_types import MISSING
from pfp_core.ext.mapping.module_mapping_to_decimal import get_spec
from tests.pfp_core.ext.mapping._helpers import call_spec


def test_module_mapping_to_decimal_preserves_missing_and_none() -> None:
    """to_decimal preserves MISSING and None values unchanged."""
    spec = get_spec()
    assert spec.op_id == "to_decimal"
    assert call_spec(spec, MISSING, {}) is MISSING
    assert call_spec(spec, None, {}) is None


def test_module_mapping_to_decimal_converts_supported_inputs() -> None:
    """to_decimal converts numeric text and Decimal input."""
    spec = get_spec()
    assert spec.op_id == "to_decimal"
    assert call_spec(spec, "10.25", {}) == Decimal("10.25")
    assert call_spec(spec, Decimal("1.5"), {}) == Decimal("1.5")


def test_module_mapping_to_decimal_rejects_invalid_inputs() -> None:
    """to_decimal rejects bool and non-numeric string inputs."""
    spec = get_spec()
    assert spec.op_id == "to_decimal"
    with pytest.raises(ValueError):
        call_spec(spec, True, {})

    with pytest.raises(ValueError):
        call_spec(spec, "not-a-number", {})
