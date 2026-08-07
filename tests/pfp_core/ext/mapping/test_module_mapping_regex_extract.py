import pytest

from pfp_core.ext.ext_types import MISSING
from pfp_core.ext.mapping.module_mapping_regex_extract import get_spec
from tests.pfp_core.ext.mapping._helpers import call_spec


def test_module_mapping_regex_extract_spec_id() -> None:
    """Spec declares correct op_id."""
    assert get_spec().op_id == "regex_extract"


def test_module_mapping_regex_extract_basic_match() -> None:
    """Extracts capture group 1 from a matching string."""
    spec = get_spec()
    assert call_spec(spec, "TSH-RED-S", {"pattern": "^([A-Z]+)", "group": 1}) == "TSH"


def test_module_mapping_regex_extract_group_zero() -> None:
    """Group 0 returns the entire match."""
    spec = get_spec()
    assert call_spec(spec, "TSH-RED-S", {"pattern": "^([A-Z]+)", "group": 0}) == "TSH"


def test_module_mapping_regex_extract_default_group() -> None:
    """Without explicit group arg, defaults to group 1."""
    spec = get_spec()
    assert call_spec(spec, "TSH-RED-S", {"pattern": "^([A-Z]+)"}) == "TSH"


def test_module_mapping_regex_extract_no_match_returns_missing() -> None:
    """No match returns MISSING sentinel."""
    spec = get_spec()
    assert call_spec(spec, "123-456", {"pattern": "^([A-Z]+)"}) is MISSING


def test_module_mapping_regex_extract_missing_passthrough() -> None:
    """MISSING input passes through unchanged."""
    spec = get_spec()
    assert call_spec(spec, MISSING, {"pattern": "^([A-Z]+)"}) is MISSING


def test_module_mapping_regex_extract_none_passthrough() -> None:
    """None input passes through unchanged."""
    spec = get_spec()
    assert call_spec(spec, None, {"pattern": "^([A-Z]+)"}) is None


def test_module_mapping_regex_extract_non_string_input() -> None:
    """Non-string input is converted via str() before matching."""
    spec = get_spec()
    assert call_spec(spec, 12345, {"pattern": "(\\d{3})", "group": 1}) == "123"


def test_module_mapping_regex_extract_missing_pattern_raises() -> None:
    """Missing 'pattern' arg raises ValueError."""
    spec = get_spec()
    with pytest.raises(ValueError):
        call_spec(spec, "abc", {})


def test_module_mapping_regex_extract_empty_pattern_raises() -> None:
    """Empty string 'pattern' raises ValueError."""
    spec = get_spec()
    with pytest.raises(ValueError):
        call_spec(spec, "abc", {"pattern": ""})


def test_module_mapping_regex_extract_non_int_group_raises() -> None:
    """Non-int 'group' arg raises ValueError."""
    spec = get_spec()
    with pytest.raises(ValueError):
        call_spec(spec, "abc", {"pattern": "(a)", "group": "1"})


def test_module_mapping_regex_extract_negative_group_raises() -> None:
    """Negative 'group' arg raises ValueError."""
    spec = get_spec()
    with pytest.raises(ValueError):
        call_spec(spec, "abc", {"pattern": "(a)", "group": -1})


def test_module_mapping_regex_extract_group_out_of_range_raises() -> None:
    """Group number exceeding capture groups raises ValueError."""
    spec = get_spec()
    with pytest.raises(ValueError):
        call_spec(spec, "abc", {"pattern": "(a)", "group": 5})
