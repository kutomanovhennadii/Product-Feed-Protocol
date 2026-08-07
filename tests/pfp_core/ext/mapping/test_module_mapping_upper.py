import pytest

from pfp_core.ext.ext_types import MISSING
from pfp_core.ext.mapping.module_mapping_upper import get_spec
from tests.pfp_core.ext.mapping._helpers import call_spec


def test_module_mapping_upper_transforms_and_preserves_special_values() -> None:
    """upper converts text to uppercase and preserves MISSING/None."""
    spec = get_spec()
    assert spec.op_id == "upper"
    assert call_spec(spec, "aBc", {}) == "ABC"
    assert call_spec(spec, MISSING, {}) is MISSING
    assert call_spec(spec, None, {}) is None


def test_module_mapping_upper_rejects_non_string() -> None:
    """upper raises ValueError for non-string values."""
    spec = get_spec()
    assert spec.op_id == "upper"
    with pytest.raises(ValueError):
        call_spec(spec, 1, {})
