import pytest

from pfp_core.ext.ext_types import MISSING
from pfp_core.ext.mapping.module_mapping_format_price import get_spec
from tests.pfp_core.ext.mapping._helpers import call_spec


def test_module_mapping_format_price_spec_id() -> None:
    """Spec declares correct op_id."""
    assert get_spec().op_id == "format_price"


def test_module_mapping_format_price_preserves_missing() -> None:
    """MISSING passes through unchanged."""
    spec = get_spec()
    assert call_spec(spec, MISSING, {}) is MISSING


def test_module_mapping_format_price_preserves_none() -> None:
    """None passes through unchanged."""
    spec = get_spec()
    assert call_spec(spec, None, {}) is None


def test_module_mapping_format_price_amount_and_currency() -> None:
    """Both amount and currency produce 'amount currency' string."""
    spec = get_spec()
    result = call_spec(spec, "29.99", {"currency": "USD"})
    assert result == "29.99 USD"


def test_module_mapping_format_price_no_currency_key() -> None:
    """Amount without currency key in args returns amount only."""
    spec = get_spec()
    result = call_spec(spec, "29.99", {})
    assert result == "29.99"


def test_module_mapping_format_price_currency_none() -> None:
    """Currency is None returns amount only."""
    spec = get_spec()
    result = call_spec(spec, "29.99", {"currency": None})
    assert result == "29.99"


def test_module_mapping_format_price_currency_missing() -> None:
    """Currency is MISSING returns amount only."""
    spec = get_spec()
    result = call_spec(spec, "29.99", {"currency": MISSING})
    assert result == "29.99"


def test_module_mapping_format_price_currency_empty() -> None:
    """Currency is empty string returns amount only."""
    spec = get_spec()
    result = call_spec(spec, "29.99", {"currency": ""})
    assert result == "29.99"


def test_module_mapping_format_price_currency_whitespace_only() -> None:
    """Currency is whitespace-only returns amount only."""
    spec = get_spec()
    result = call_spec(spec, "29.99", {"currency": "  "})
    assert result == "29.99"


def test_module_mapping_format_price_empty_amount() -> None:
    """Empty amount string returns MISSING."""
    spec = get_spec()
    result = call_spec(spec, "", {"currency": "USD"})
    assert result is MISSING


def test_module_mapping_format_price_whitespace_amount() -> None:
    """Whitespace-only amount returns MISSING."""
    spec = get_spec()
    result = call_spec(spec, "  ", {"currency": "USD"})
    assert result is MISSING


def test_module_mapping_format_price_strips_whitespace() -> None:
    """Leading/trailing whitespace is stripped from amount and currency."""
    spec = get_spec()
    result = call_spec(spec, "  29.99  ", {"currency": "  USD  "})
    assert result == "29.99 USD"


def test_module_mapping_format_price_numeric_int() -> None:
    """Integer amount is stringified and formatted with currency."""
    spec = get_spec()
    result = call_spec(spec, 30, {"currency": "EUR"})
    assert result == "30 EUR"


def test_module_mapping_format_price_numeric_float() -> None:
    """Float amount is stringified and formatted with currency."""
    spec = get_spec()
    result = call_spec(spec, 29.99, {"currency": "USD"})
    assert result == "29.99 USD"


def test_module_mapping_format_price_zero_amount() -> None:
    """Zero amount is valid (free product)."""
    spec = get_spec()
    result = call_spec(spec, "0", {"currency": "USD"})
    assert result == "0 USD"


def test_module_mapping_format_price_rejects_bool() -> None:
    """Boolean values are rejected (not a valid amount)."""
    spec = get_spec()
    with pytest.raises(TypeError):
        call_spec(spec, True, {"currency": "USD"})
    with pytest.raises(TypeError):
        call_spec(spec, False, {})


def test_module_mapping_format_price_rejects_non_scalar() -> None:
    """Non-scalar types (list, dict) raise TypeError."""
    spec = get_spec()
    with pytest.raises(TypeError):
        call_spec(spec, ["29.99"], {"currency": "USD"})
    with pytest.raises(TypeError):
        call_spec(spec, {"amount": "29.99"}, {"currency": "USD"})
