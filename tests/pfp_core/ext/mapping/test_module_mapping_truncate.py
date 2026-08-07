import pytest

from pfp_core.ext.ext_types import MISSING
from pfp_core.ext.mapping.module_mapping_truncate import get_spec
from tests.pfp_core.ext.mapping._helpers import call_spec


def test_module_mapping_truncate_spec_id() -> None:
    """Spec declares correct op_id."""
    assert get_spec().op_id == "truncate"


def test_module_mapping_truncate_long_string() -> None:
    """String longer than max_length is truncated."""
    spec = get_spec()
    assert call_spec(spec, "ABCDEFGHIJ", {"max_length": 5}) == "ABCDE"


def test_module_mapping_truncate_exact_length() -> None:
    """String exactly at max_length passes through unchanged."""
    spec = get_spec()
    assert call_spec(spec, "ABCDE", {"max_length": 5}) == "ABCDE"


def test_module_mapping_truncate_short_string() -> None:
    """String shorter than max_length passes through unchanged."""
    spec = get_spec()
    assert call_spec(spec, "ABC", {"max_length": 5}) == "ABC"


def test_module_mapping_truncate_min_length() -> None:
    """max_length=1 truncates to single character."""
    spec = get_spec()
    assert call_spec(spec, "ABC", {"max_length": 1}) == "A"


def test_module_mapping_truncate_missing_passthrough() -> None:
    """MISSING input passes through unchanged."""
    spec = get_spec()
    assert call_spec(spec, MISSING, {"max_length": 5}) is MISSING


def test_module_mapping_truncate_none_passthrough() -> None:
    """None input passes through unchanged."""
    spec = get_spec()
    assert call_spec(spec, None, {"max_length": 5}) is None


def test_module_mapping_truncate_non_string_input() -> None:
    """Non-string input is converted via str() before truncating."""
    spec = get_spec()
    assert call_spec(spec, 123456, {"max_length": 3}) == "123"


def test_module_mapping_truncate_missing_arg_raises() -> None:
    """Missing 'max_length' arg raises ValueError."""
    spec = get_spec()
    with pytest.raises(ValueError):
        call_spec(spec, "abc", {})


def test_module_mapping_truncate_zero_raises() -> None:
    """max_length=0 raises ValueError."""
    spec = get_spec()
    with pytest.raises(ValueError):
        call_spec(spec, "abc", {"max_length": 0})


def test_module_mapping_truncate_negative_raises() -> None:
    """Negative max_length raises ValueError."""
    spec = get_spec()
    with pytest.raises(ValueError):
        call_spec(spec, "abc", {"max_length": -1})


def test_module_mapping_truncate_non_int_raises() -> None:
    """Non-int max_length raises ValueError."""
    spec = get_spec()
    with pytest.raises(ValueError):
        call_spec(spec, "abc", {"max_length": "5"})


def test_module_mapping_truncate_bool_raises() -> None:
    """Bool max_length raises ValueError (bool is subclass of int)."""
    spec = get_spec()
    with pytest.raises(ValueError):
        call_spec(spec, "abc", {"max_length": True})
