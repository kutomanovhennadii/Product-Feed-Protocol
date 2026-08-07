from pfp_core.ext.ext_builtin_catalog import build_builtin_catalog
from pfp_core.ext.ext_types import MISSING


def test_required_module() -> None:
    """required fails on missing/null and passes on present values."""
    catalog = build_builtin_catalog()
    module = catalog.get_validation_module("required")

    assert module.call(MISSING, {}, None, None).ok is False
    assert module.call(None, {}, None, None).ok is False
    assert module.call("x", {}, None, None).ok is True
