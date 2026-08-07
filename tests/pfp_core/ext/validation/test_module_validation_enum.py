import pytest

from pfp_core.ext.ext_builtin_catalog import build_builtin_catalog
from pfp_core.ext.ext_types import MISSING


def test_enum_module() -> None:
    """enum enforces membership for strings and validates allowed config."""
    catalog = build_builtin_catalog()
    module = catalog.get_validation_module("enum")

    assert module.call(MISSING, {"allowed": ["a"]}, None, None).ok is True
    assert module.call(None, {"allowed": ["a"]}, None, None).ok is True
    assert module.call("a", {"allowed": ["a", "b"]}, None, None).ok is True
    assert module.call("z", {"allowed": ["a", "b"]}, None, None).ok is False
    assert module.call(123, {"allowed": ["1", "2"]}, None, None).ok is True

    with pytest.raises(ValueError):
        module.call("a", {"allowed": []}, None, None)
