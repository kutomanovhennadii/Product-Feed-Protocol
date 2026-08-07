import pytest

from pfp_core.ext.ext_types import MISSING
from pfp_core.ext.mapping.module_mapping_lower import get_spec
from tests.pfp_core.ext.mapping._helpers import call_spec


def test_module_mapping_lower_transforms_and_preserves_special_values() -> None:
    """lower converts text to lowercase and preserves MISSING/None."""
    spec = get_spec()
    assert spec.op_id == "lower"
    assert call_spec(spec, "AbC", {}) == "abc"
    assert call_spec(spec, MISSING, {}) is MISSING
    assert call_spec(spec, None, {}) is None


def test_module_mapping_lower_rejects_non_string() -> None:
    """lower raises ValueError for non-string values."""
    spec = get_spec()
    assert spec.op_id == "lower"
    with pytest.raises(ValueError):
        call_spec(spec, 1, {})
