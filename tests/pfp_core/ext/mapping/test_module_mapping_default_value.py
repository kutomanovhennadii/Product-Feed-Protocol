import pytest

from pfp_core.ext.ext_types import MISSING
from pfp_core.ext.mapping.module_mapping_default_value import get_spec
from tests.pfp_core.ext.mapping._helpers import call_spec


def test_module_mapping_default_value_spec_id() -> None:
    """Spec declares correct op_id."""
    assert get_spec().op_id == "default_value"


def test_module_mapping_default_value_missing_returns_default() -> None:
    """MISSING input is replaced by the configured default."""
    spec = get_spec()
    assert call_spec(spec, MISSING, {"value": "USD"}) == "USD"


def test_module_mapping_default_value_none_returns_default() -> None:
    """None input is replaced by the configured default."""
    spec = get_spec()
    assert call_spec(spec, None, {"value": "USD"}) == "USD"


def test_module_mapping_default_value_present_value_unchanged() -> None:
    """Non-missing, non-None input passes through unchanged."""
    spec = get_spec()
    assert call_spec(spec, "EUR", {"value": "USD"}) == "EUR"


def test_module_mapping_default_value_non_string_default() -> None:
    """Default value may be a non-string type (int, bool)."""
    spec = get_spec()
    assert call_spec(spec, MISSING, {"value": 0}) == 0
    assert call_spec(spec, MISSING, {"value": False}) is False


def test_module_mapping_default_value_missing_arg_raises() -> None:
    """Missing 'value' arg raises ValueError."""
    spec = get_spec()
    with pytest.raises(ValueError):
        call_spec(spec, MISSING, {})


def test_module_mapping_default_value_falsy_values_not_replaced() -> None:
    """Falsy but present values (empty string, 0, False) are NOT replaced."""
    spec = get_spec()
    assert call_spec(spec, "", {"value": "fallback"}) == ""
    assert call_spec(spec, 0, {"value": 99}) == 0
    assert call_spec(spec, False, {"value": True}) is False
