import pytest

from pfp_core.ext.ext_types import MISSING
from pfp_core.ext.mapping.module_mapping_to_int import get_spec
from tests.pfp_core.ext.mapping._helpers import call_spec


def test_module_mapping_to_int_preserves_missing_and_none() -> None:
    """to_int preserves MISSING and None values unchanged."""
    spec = get_spec()
    assert spec.op_id == "to_int"
    assert call_spec(spec, MISSING, {}) is MISSING
    assert call_spec(spec, None, {}) is None


def test_module_mapping_to_int_converts_supported_inputs() -> None:
    """to_int converts valid numeric string and integer inputs."""
    spec = get_spec()
    assert spec.op_id == "to_int"
    assert call_spec(spec, "42", {}) == 42
    assert call_spec(spec, 7, {}) == 7


def test_module_mapping_to_int_rejects_invalid_inputs() -> None:
    """to_int rejects invalid, bool, empty-string and unknown inputs."""
    spec = get_spec()
    assert spec.op_id == "to_int"
    with pytest.raises(ValueError):
        call_spec(spec, "x", {})

    with pytest.raises(ValueError):
        call_spec(spec, True, {})

    with pytest.raises(ValueError):
        call_spec(spec, "   ", {})

    with pytest.raises(ValueError):
        call_spec(spec, object(), {})
