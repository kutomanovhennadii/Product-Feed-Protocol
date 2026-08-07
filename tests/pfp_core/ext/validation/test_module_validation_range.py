from decimal import Decimal

import pytest

from pfp_core.ext.ext_builtin_catalog import build_builtin_catalog
from pfp_core.ext.ext_types import MISSING


def test_range_module_for_int_and_decimal() -> None:
    """range checks numeric bounds and validates min/max configuration."""
    catalog = build_builtin_catalog()
    module = catalog.get_validation_module("range")

    assert module.call(MISSING, {"min": 1}, None, None).ok is True
    assert module.call(None, {"min": 1}, None, None).ok is True
    assert module.call(10, {"min": 1, "max": 20}, None, None).ok is True
    assert module.call(Decimal("2.5"), {"min": 2, "max": 3}, None, None).ok is True
    assert module.call(0, {"min": 1}, None, None).ok is False
    assert module.call(99, {"max": 50}, None, None).ok is False
    assert module.call("abc", {"min": 1}, None, None).ok is True

    with pytest.raises(ValueError):
        module.call(5, {}, None, None)

    with pytest.raises(ValueError):
        module.call(5, {"min": 10, "max": 1}, None, None)


def test_range_module_is_typing_first_for_bool_values() -> None:
    """range does not fail for non-numeric values; type checking is separate."""
    catalog = build_builtin_catalog()
    module = catalog.get_validation_module("range")

    assert module.call(True, {"min": 1}, None, None).ok is True
