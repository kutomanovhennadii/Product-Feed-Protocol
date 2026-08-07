from datetime import date, datetime
from decimal import Decimal

import pytest

from pfp_core.ext.ext_builtin_catalog import build_builtin_catalog
from pfp_core.ext.ext_types import MISSING
from pfp_core.ext.validation.module_validation_type import _matches_type


def test_type_module_for_string() -> None:
    """type validates configured type_id=string and ignores missing/null."""
    catalog = build_builtin_catalog()
    module = catalog.get_validation_module("type")

    assert module.call(MISSING, {"type_id": "string"}, None, None).ok is True
    assert module.call(None, {"type_id": "string"}, None, None).ok is True
    assert module.call("hello", {"type_id": "string"}, None, None).ok is True
    assert module.call(1, {"type_id": "string"}, None, None).ok is False


def test_type_module_for_integer_and_number() -> None:
    """int and decimal contracts are validated via type_id config."""
    catalog = build_builtin_catalog()
    module = catalog.get_validation_module("type")

    assert module.call(3, {"type_id": "int"}, None, None).ok is True
    assert module.call(True, {"type_id": "int"}, None, None).ok is False
    assert module.call(Decimal("3.5"), {"type_id": "decimal"}, None, None).ok is True
    assert module.call(False, {"type_id": "decimal"}, None, None).ok is False
    assert module.call(True, {"type_id": "bool"}, None, None).ok is True


def test_type_module_for_any_date_and_datetime() -> None:
    """any/date/datetime contracts are applied as declared by type_id."""
    catalog = build_builtin_catalog()
    module = catalog.get_validation_module("type")

    assert module.call({"k": "v"}, {"type_id": "any"}, None, None).ok is True
    assert module.call(date(2026, 3, 5), {"type_id": "date"}, None, None).ok is True
    assert (
        module.call(datetime(2026, 3, 5, 10, 0, 0), {"type_id": "date"}, None, None).ok
        is False
    )
    assert (
        module.call(
            datetime(2026, 3, 5, 10, 0, 0), {"type_id": "datetime"}, None, None
        ).ok
        is True
    )


def test_type_module_for_array_and_object() -> None:
    """array/object checks built-in Python list/dict compatibility."""
    catalog = build_builtin_catalog()
    module = catalog.get_validation_module("type")

    assert module.call(["a", "b"], {"type_id": "array[string]"}, None, None).ok is True
    assert module.call({"a": 1}, {"type_id": "object"}, None, None).ok is True
    assert module.call({}, {"type_id": "array[string]"}, None, None).ok is False
    assert module.call([], {"type_id": "object"}, None, None).ok is False


def test_type_module_invalid_config_raises() -> None:
    """Invalid or missing type_id config fails fast with ValueError."""
    catalog = build_builtin_catalog()
    module = catalog.get_validation_module("type")

    with pytest.raises(ValueError):
        module.call("v", {}, None, None)


def test_type_matches_type_unknown_id_falls_back_to_false() -> None:
    """Internal matcher returns False for unknown type_id fallback branch."""
    assert _matches_type("x", "__unknown__") is False
