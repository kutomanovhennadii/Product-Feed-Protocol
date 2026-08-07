import pytest

from pfp_core.ext.ext_types import MISSING
from pfp_core.ext.mapping.module_mapping_bool_to_availability import get_spec
from tests.pfp_core.ext.mapping._helpers import call_spec


def test_module_mapping_bool_to_availability_spec_id() -> None:
    """Spec declares correct op_id."""
    assert get_spec().op_id == "bool_to_availability"


def test_module_mapping_bool_to_availability_preserves_missing() -> None:
    """MISSING passes through unchanged."""
    spec = get_spec()
    assert call_spec(spec, MISSING, {}) is MISSING


def test_module_mapping_bool_to_availability_preserves_none() -> None:
    """None passes through unchanged."""
    spec = get_spec()
    assert call_spec(spec, None, {}) is None


def test_module_mapping_bool_to_availability_true_bool() -> None:
    """Python True maps to 'in_stock'."""
    spec = get_spec()
    assert call_spec(spec, True, {}) == "in_stock"


def test_module_mapping_bool_to_availability_false_bool() -> None:
    """Python False maps to 'out_of_stock'."""
    spec = get_spec()
    assert call_spec(spec, False, {}) == "out_of_stock"


def test_module_mapping_bool_to_availability_true_strings() -> None:
    """String variants of true ('true', 'yes', '1') map to 'in_stock'."""
    spec = get_spec()
    assert call_spec(spec, "true", {}) == "in_stock"
    assert call_spec(spec, "True", {}) == "in_stock"
    assert call_spec(spec, "TRUE", {}) == "in_stock"
    assert call_spec(spec, "yes", {}) == "in_stock"
    assert call_spec(spec, "1", {}) == "in_stock"


def test_module_mapping_bool_to_availability_false_strings() -> None:
    """String variants of false ('false', 'no', '0') map to 'out_of_stock'."""
    spec = get_spec()
    assert call_spec(spec, "false", {}) == "out_of_stock"
    assert call_spec(spec, "False", {}) == "out_of_stock"
    assert call_spec(spec, "FALSE", {}) == "out_of_stock"
    assert call_spec(spec, "no", {}) == "out_of_stock"
    assert call_spec(spec, "0", {}) == "out_of_stock"


def test_module_mapping_bool_to_availability_int_1() -> None:
    """Integer 1 maps to 'in_stock'."""
    spec = get_spec()
    assert call_spec(spec, 1, {}) == "in_stock"


def test_module_mapping_bool_to_availability_int_0() -> None:
    """Integer 0 maps to 'out_of_stock'."""
    spec = get_spec()
    assert call_spec(spec, 0, {}) == "out_of_stock"


def test_module_mapping_bool_to_availability_unknown_string_raises() -> None:
    """Unrecognized string raises ValueError."""
    spec = get_spec()
    with pytest.raises(ValueError):
        call_spec(spec, "available", {})
    with pytest.raises(ValueError):
        call_spec(spec, "in_stock", {})
    with pytest.raises(ValueError):
        call_spec(spec, "", {})


def test_module_mapping_bool_to_availability_unknown_int_raises() -> None:
    """Integer other than 0/1 raises ValueError."""
    spec = get_spec()
    with pytest.raises(ValueError):
        call_spec(spec, 2, {})
    with pytest.raises(ValueError):
        call_spec(spec, -1, {})


def test_module_mapping_bool_to_availability_unsupported_type_raises() -> None:
    """Unsupported types (float, list, dict) raise TypeError."""
    spec = get_spec()
    with pytest.raises(TypeError):
        call_spec(spec, 1.0, {})
    with pytest.raises(TypeError):
        call_spec(spec, [], {})
