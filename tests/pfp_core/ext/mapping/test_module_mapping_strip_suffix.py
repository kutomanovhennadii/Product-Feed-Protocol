import pytest

from pfp_core.ext.ext_types import MISSING
from pfp_core.ext.mapping.module_mapping_strip_suffix import get_spec
from tests.pfp_core.ext.mapping._helpers import call_spec


def test_module_mapping_strip_suffix_spec_id() -> None:
    """Spec declares correct op_id."""
    assert get_spec().op_id == "strip_suffix"


def test_module_mapping_strip_suffix_single_delimiter() -> None:
    """Strips at the last occurrence of a single delimiter."""
    spec = get_spec()
    assert call_spec(spec, "TSH-RED-S", {"delimiters": ["-"]}) == "TSH-RED"


def test_module_mapping_strip_suffix_multiple_delimiters_rightmost() -> None:
    """With multiple delimiters, cuts at the rightmost position among all."""
    spec = get_spec()
    assert call_spec(spec, "A-B_C", {"delimiters": ["-", "_"]}) == "A-B"


def test_module_mapping_strip_suffix_no_delimiter_found() -> None:
    """No delimiter found returns value unchanged."""
    spec = get_spec()
    assert call_spec(spec, "ABCDEF", {"delimiters": ["-"]}) == "ABCDEF"


def test_module_mapping_strip_suffix_delimiter_at_start() -> None:
    """Delimiter at position 0 returns empty string."""
    spec = get_spec()
    assert call_spec(spec, "-ABC", {"delimiters": ["-"]}) == ""


def test_module_mapping_strip_suffix_consecutive_delimiters() -> None:
    """Consecutive delimiters — cuts at the last one."""
    spec = get_spec()
    assert call_spec(spec, "A--B", {"delimiters": ["-"]}) == "A-"


def test_module_mapping_strip_suffix_missing_passthrough() -> None:
    """MISSING input passes through unchanged."""
    spec = get_spec()
    assert call_spec(spec, MISSING, {"delimiters": ["-"]}) is MISSING


def test_module_mapping_strip_suffix_none_passthrough() -> None:
    """None input passes through unchanged."""
    spec = get_spec()
    assert call_spec(spec, None, {"delimiters": ["-"]}) is None


def test_module_mapping_strip_suffix_non_string_input() -> None:
    """Non-string input is converted via str() before processing."""
    spec = get_spec()
    assert call_spec(spec, 12345, {"delimiters": ["3"]}) == "12"


def test_module_mapping_strip_suffix_missing_delimiters_raises() -> None:
    """Missing 'delimiters' arg raises ValueError."""
    spec = get_spec()
    with pytest.raises(ValueError):
        call_spec(spec, "abc", {})


def test_module_mapping_strip_suffix_empty_delimiters_raises() -> None:
    """Empty 'delimiters' list raises ValueError."""
    spec = get_spec()
    with pytest.raises(ValueError):
        call_spec(spec, "abc", {"delimiters": []})


def test_module_mapping_strip_suffix_non_string_delimiter_raises() -> None:
    """Non-string element in 'delimiters' raises ValueError."""
    spec = get_spec()
    with pytest.raises(ValueError):
        call_spec(spec, "abc", {"delimiters": ["-", 1]})
