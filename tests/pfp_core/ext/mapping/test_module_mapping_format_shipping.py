import pytest

from pfp_core.ext.ext_types import MISSING
from pfp_core.ext.mapping.module_mapping_format_shipping import get_spec
from tests.pfp_core.ext.mapping._helpers import call_spec

_STRIPE_PATTERN = "{country}:{region}:{service}:{speed_range}:{price}"
_STRIPE_DEFAULTS = {"region": "ALL", "service": "Standard"}

_OPENAI_PATTERN = (
    "{country}:{region}:{service}:{price}"
    ":{min_handling_time}:{max_handling_time}:{min_transit_time}:{max_transit_time}"
)
_OPENAI_DEFAULTS = {
    "region": "",
    "service": "Standard",
    "min_handling_time": "0",
    "max_handling_time": "0",
    "min_transit_time": "0",
    "max_transit_time": "0",
}


def _stripe_entry(**overrides):  # type: ignore[no-untyped-def]
    base = {
        "country": "US",
        "region": "ALL",
        "service": "Standard",
        "price": "0.00 USD",
        "min_handling_time": 1,
        "max_handling_time": 2,
        "min_transit_time": 1,
        "max_transit_time": 3,
    }
    base.update(overrides)
    return base


def _openai_entry(**overrides):  # type: ignore[no-untyped-def]
    base = {
        "country": "US",
        "region": "CA",
        "service": "Overnight",
        "price": "16.00 USD",
        "min_handling_time": 1,
        "max_handling_time": 2,
        "min_transit_time": 1,
        "max_transit_time": 3,
    }
    base.update(overrides)
    return base


def test_spec_id() -> None:
    """Spec declares correct op_id."""
    assert get_spec().op_id == "format_shipping"


# --- Stripe-like pattern ---


def test_stripe_single_entry() -> None:
    """Single dict formats to stripe colon-delimited string."""
    spec = get_spec()
    result = call_spec(
        spec,
        _stripe_entry(),
        {"pattern": _STRIPE_PATTERN, "defaults": _STRIPE_DEFAULTS},
    )
    assert result == "US:ALL:Standard:2-5:0.00 USD"


def test_stripe_list_of_two() -> None:
    """List of two dicts joins with comma."""
    spec = get_spec()
    entries = [
        _stripe_entry(),
        _stripe_entry(service="Expedited", price="12.99 USD"),
    ]
    result = call_spec(
        spec, entries, {"pattern": _STRIPE_PATTERN, "defaults": _STRIPE_DEFAULTS}
    )
    assert result == "US:ALL:Standard:2-5:0.00 USD,US:ALL:Expedited:2-5:12.99 USD"


def test_stripe_speed_range_computation() -> None:
    """speed_range = (min_handling+min_transit)-(max_handling+max_transit)."""
    spec = get_spec()
    entry = _stripe_entry(
        min_handling_time=2,
        max_handling_time=3,
        min_transit_time=1,
        max_transit_time=4,
    )
    result = call_spec(
        spec, entry, {"pattern": _STRIPE_PATTERN, "defaults": _STRIPE_DEFAULTS}
    )
    assert result == "US:ALL:Standard:3-7:0.00 USD"


def test_stripe_defaults_applied() -> None:
    """Missing region/service in entry fall back to defaults."""
    spec = get_spec()
    entry = {
        "country": "DE",
        "price": "5.00 EUR",
        "min_handling_time": 0,
        "max_handling_time": 0,
        "min_transit_time": 0,
        "max_transit_time": 0,
    }
    result = call_spec(
        spec, entry, {"pattern": _STRIPE_PATTERN, "defaults": _STRIPE_DEFAULTS}
    )
    assert result == "DE:ALL:Standard:0-0:5.00 EUR"


def test_stripe_no_time_fields_default_zero() -> None:
    """Without time fields and no defaults, speed_range is 0-0."""
    spec = get_spec()
    entry = {"country": "US", "price": "0.00 USD"}
    result = call_spec(
        spec, entry, {"pattern": _STRIPE_PATTERN, "defaults": _STRIPE_DEFAULTS}
    )
    assert result == "US:ALL:Standard:0-0:0.00 USD"


# --- OpenAI-like pattern ---


def test_openai_single_entry() -> None:
    """Single dict formats to openai 8-component string."""
    spec = get_spec()
    result = call_spec(
        spec,
        _openai_entry(),
        {"pattern": _OPENAI_PATTERN, "defaults": _OPENAI_DEFAULTS},
    )
    assert result == "US:CA:Overnight:16.00 USD:1:2:1:3"


def test_openai_empty_region_via_defaults() -> None:
    """Empty region via defaults produces double-colon."""
    spec = get_spec()
    entry = {"country": "US", "service": "Standard", "price": "5.00 USD"}
    result = call_spec(
        spec, entry, {"pattern": _OPENAI_PATTERN, "defaults": _OPENAI_DEFAULTS}
    )
    assert result == "US::Standard:5.00 USD:0:0:0:0"


def test_openai_list_of_two() -> None:
    """List of two dicts joins with comma."""
    spec = get_spec()
    entries = [
        _openai_entry(),
        _openai_entry(country="DE", region="", service="Standard", price="5.00 EUR"),
    ]
    result = call_spec(
        spec, entries, {"pattern": _OPENAI_PATTERN, "defaults": _OPENAI_DEFAULTS}
    )
    parts = result.split(",")
    assert len(parts) == 2
    assert parts[0] == "US:CA:Overnight:16.00 USD:1:2:1:3"


# --- Custom pattern ---


def test_custom_pattern() -> None:
    """Arbitrary pattern works without speed_range."""
    spec = get_spec()
    entry = {"country": "US", "service": "Standard", "price": "5.00 USD"}
    result = call_spec(spec, entry, {"pattern": "{country}-{service} ({price})"})
    assert result == "US-Standard (5.00 USD)"


def test_custom_separator() -> None:
    """Custom separator used for join."""
    spec = get_spec()
    entries = [
        {"country": "US", "price": "5.00"},
        {"country": "DE", "price": "3.00"},
    ]
    result = call_spec(
        spec, entries, {"pattern": "{country}={price}", "separator": "|"}
    )
    assert result == "US=5.00|DE=3.00"


# --- Passthrough ---


def test_missing_passthrough() -> None:
    """MISSING input passes through."""
    spec = get_spec()
    assert call_spec(spec, MISSING, {"pattern": "{x}"}) is MISSING


def test_none_passthrough() -> None:
    """None input passes through."""
    spec = get_spec()
    assert call_spec(spec, None, {"pattern": "{x}"}) is None


def test_string_passthrough() -> None:
    """String input passes through unchanged."""
    spec = get_spec()
    result = call_spec(spec, "US:ALL:Standard:3-5:0.00 USD", {"pattern": "{x}"})
    assert result == "US:ALL:Standard:3-5:0.00 USD"


def test_list_with_strings() -> None:
    """List of strings joined with separator."""
    spec = get_spec()
    result = call_spec(spec, ["a", "b"], {"pattern": "{x}"})
    assert result == "a,b"


# --- Sanitize ---


def test_strip_colons_default() -> None:
    """Colons in field values are stripped by default."""
    spec = get_spec()
    entry = {"country": "U:S", "price": "5.00"}
    result = call_spec(spec, entry, {"pattern": "{country}={price}"})
    assert result == "US=5.00"


def test_strip_colons_false() -> None:
    """strip_colons=false preserves colons in values."""
    spec = get_spec()
    entry = {"country": "U:S", "price": "5.00"}
    result = call_spec(
        spec, entry, {"pattern": "{country}={price}", "strip_colons": False}
    )
    assert result == "U:S=5.00"


# --- Errors ---


def test_missing_pattern_raises() -> None:
    """Missing pattern arg raises ValueError."""
    spec = get_spec()
    with pytest.raises(ValueError):
        call_spec(spec, {"x": "1"}, {})


def test_empty_pattern_raises() -> None:
    """Empty pattern raises ValueError."""
    spec = get_spec()
    with pytest.raises(ValueError):
        call_spec(spec, {"x": "1"}, {"pattern": ""})


def test_unresolved_placeholder_raises() -> None:
    """Placeholder not in entry or defaults raises ValueError."""
    spec = get_spec()
    with pytest.raises(ValueError):
        call_spec(spec, {"country": "US"}, {"pattern": "{country}:{missing_field}"})


def test_non_dict_non_str_entry_raises() -> None:
    """List entry that is not dict or str raises ValueError."""
    spec = get_spec()
    with pytest.raises(ValueError):
        call_spec(spec, [123], {"pattern": "{x}"})


def test_invalid_int_for_speed_range_raises() -> None:
    """Non-integer time field raises ValueError when speed_range is used."""
    spec = get_spec()
    entry = {
        "country": "US",
        "price": "5.00",
        "min_handling_time": "abc",
    }
    with pytest.raises(ValueError):
        call_spec(
            spec,
            entry,
            {"pattern": "{country}:{speed_range}:{price}"},
        )


def test_invalid_defaults_separator_and_strip_colons_raise() -> None:
    """Config parser rejects invalid defaults, separator, and strip_colons types."""

    spec = get_spec()

    with pytest.raises(ValueError, match="defaults"):
        call_spec(spec, {"country": "US"}, {"pattern": "{country}", "defaults": []})

    with pytest.raises(ValueError, match="separator"):
        call_spec(spec, {"country": "US"}, {"pattern": "{country}", "separator": 1})

    with pytest.raises(ValueError, match="strip_colons"):
        call_spec(
            spec,
            {"country": "US"},
            {"pattern": "{country}", "strip_colons": "yes"},
        )


def test_scalar_non_collection_input_raises_for_invalid_entry_type() -> None:
    """Scalar non-string inputs are treated as a single invalid shipping entry."""

    spec = get_spec()

    with pytest.raises(ValueError, match="entry must be dict or str"):
        call_spec(spec, 123, {"pattern": "{country}"})


def test_spec_declares_strip_colons_argument() -> None:
    """Spec contract exposes strip_colons as an optional boolean argument."""

    field_names = tuple(field.name for field in get_spec().args_spec.fields)

    assert field_names == ("pattern", "defaults", "separator", "strip_colons")


def test_invalid_pattern_formatting_is_wrapped() -> None:
    """Invalid format strings are wrapped into stable format_shipping errors."""

    spec = get_spec()

    with pytest.raises(ValueError, match="pattern formatting failed"):
        call_spec(spec, {"country": "US"}, {"pattern": "{country"})
