import pytest

from pfp_core.ext.ext_types import MISSING
from pfp_core.ext.mapping.module_mapping_strip_html import get_spec
from tests.pfp_core.ext.mapping._helpers import call_spec


def test_module_mapping_strip_html_spec_id() -> None:
    """Spec declares correct op_id."""
    assert get_spec().op_id == "strip_html"


def test_module_mapping_strip_html_preserves_missing() -> None:
    """MISSING passes through unchanged."""
    spec = get_spec()
    assert call_spec(spec, MISSING, {}) is MISSING


def test_module_mapping_strip_html_preserves_none() -> None:
    """None passes through unchanged."""
    spec = get_spec()
    assert call_spec(spec, None, {}) is None


def test_module_mapping_strip_html_removes_paragraph_tags() -> None:
    """Basic <p> tags are stripped, leaving plain text."""
    spec = get_spec()
    result = call_spec(spec, "<p>Hello world</p>", {})
    assert result == "Hello world"


def test_module_mapping_strip_html_removes_nested_tags() -> None:
    """Nested inline tags (<strong>, <em>) are stripped."""
    spec = get_spec()
    result = call_spec(
        spec,
        "<p>Bring a burst of fun to your <strong>golf game</strong></p>",
        {},
    )
    assert result == "Bring a burst of fun to your golf game"


def test_module_mapping_strip_html_decodes_entities() -> None:
    """HTML entities (&amp;, &lt;, &gt;, &nbsp;) are decoded."""
    spec = get_spec()
    assert call_spec(spec, "AT&amp;T", {}) == "AT&T"
    assert call_spec(spec, "a &lt; b &gt; c", {}) == "a < b > c"


def test_module_mapping_strip_html_collapses_whitespace() -> None:
    """Multiple spaces and newlines from tag removal are collapsed."""
    spec = get_spec()
    result = call_spec(spec, "<p>Line one</p><p>Line two</p>", {})
    assert result == "Line one Line two"


def test_module_mapping_strip_html_plain_string_unchanged() -> None:
    """Plain text without HTML passes through (whitespace may be normalized)."""
    spec = get_spec()
    assert call_spec(spec, "Hello world", {}) == "Hello world"


def test_module_mapping_strip_html_empty_string() -> None:
    """Empty string input returns empty string."""
    spec = get_spec()
    assert call_spec(spec, "", {}) == ""


def test_module_mapping_strip_html_rejects_non_string() -> None:
    """Non-string input (int, bool, list) raises TypeError."""
    spec = get_spec()
    with pytest.raises(TypeError):
        call_spec(spec, 42, {})
    with pytest.raises(TypeError):
        call_spec(spec, True, {})
    with pytest.raises(TypeError):
        call_spec(spec, ["<p>text</p>"], {})
