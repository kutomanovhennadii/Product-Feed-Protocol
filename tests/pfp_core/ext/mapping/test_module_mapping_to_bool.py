import pytest

from pfp_core.ext.ext_types import MISSING
from pfp_core.ext.mapping.module_mapping_to_bool import get_spec
from tests.pfp_core.ext.mapping._helpers import call_spec


def test_module_mapping_to_bool_preserves_missing_and_none() -> None:
    """to_bool preserves MISSING and None values unchanged."""
    spec = get_spec()
    assert spec.op_id == "to_bool"
    assert call_spec(spec, MISSING, {}) is MISSING
    assert call_spec(spec, None, {}) is None


def test_module_mapping_to_bool_converts_supported_inputs() -> None:
    """to_bool converts supported str/int/bool values."""
    spec = get_spec()
    assert spec.op_id == "to_bool"
    assert call_spec(spec, "true", {}) is True
    assert call_spec(spec, " FALSE ", {}) is False
    assert call_spec(spec, True, {}) is True
    assert call_spec(spec, 0, {}) is False
    assert call_spec(spec, 1, {}) is True


def test_module_mapping_to_bool_rejects_invalid_inputs() -> None:
    """to_bool rejects unrecognized strings, integers and objects."""
    spec = get_spec()
    assert spec.op_id == "to_bool"
    with pytest.raises(ValueError):
        call_spec(spec, 2, {})

    with pytest.raises(ValueError):
        call_spec(spec, "maybe", {})

    with pytest.raises(ValueError):
        call_spec(spec, object(), {})
