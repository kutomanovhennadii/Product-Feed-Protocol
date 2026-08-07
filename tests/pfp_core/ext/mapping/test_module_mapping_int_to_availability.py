import pytest

from pfp_core.ext.ext_types import MISSING
from pfp_core.ext.mapping.module_mapping_int_to_availability import get_spec
from tests.pfp_core.ext.mapping._helpers import call_spec


def test_module_mapping_int_to_availability_spec_id() -> None:
    """Spec declares correct op_id."""
    assert get_spec().op_id == "int_to_availability"


def test_module_mapping_int_to_availability_preserves_missing() -> None:
    """MISSING passes through unchanged."""
    spec = get_spec()
    assert call_spec(spec, MISSING, {}) is MISSING


def test_module_mapping_int_to_availability_none_out_of_stock() -> None:
    """None (untracked inventory) maps to 'out_of_stock'."""
    spec = get_spec()
    assert call_spec(spec, None, {}) == "out_of_stock"


def test_module_mapping_int_to_availability_positive_in_stock() -> None:
    """Positive integer maps to 'in_stock'."""
    spec = get_spec()
    assert call_spec(spec, 1, {}) == "in_stock"
    assert call_spec(spec, 42, {}) == "in_stock"
    assert call_spec(spec, 1000, {}) == "in_stock"


def test_module_mapping_int_to_availability_zero_out_of_stock() -> None:
    """Zero maps to 'out_of_stock'."""
    spec = get_spec()
    assert call_spec(spec, 0, {}) == "out_of_stock"


def test_module_mapping_int_to_availability_negative_out_of_stock() -> None:
    """Negative integer (oversell) maps to 'out_of_stock'."""
    spec = get_spec()
    assert call_spec(spec, -1, {}) == "out_of_stock"
    assert call_spec(spec, -3, {}) == "out_of_stock"
    assert call_spec(spec, -100, {}) == "out_of_stock"


def test_module_mapping_int_to_availability_bool_raises() -> None:
    """bool raises TypeError (bool is subclass of int, must be rejected explicitly)."""
    spec = get_spec()
    with pytest.raises(TypeError):
        call_spec(spec, True, {})
    with pytest.raises(TypeError):
        call_spec(spec, False, {})


def test_module_mapping_int_to_availability_unsupported_type_raises() -> None:
    """Unsupported types (str, float, list) raise TypeError."""
    spec = get_spec()
    with pytest.raises(TypeError):
        call_spec(spec, "42", {})
    with pytest.raises(TypeError):
        call_spec(spec, 1.0, {})
    with pytest.raises(TypeError):
        call_spec(spec, [], {})
