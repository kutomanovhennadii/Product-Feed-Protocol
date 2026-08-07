import pytest

from pfp_core.ext.ext_types import MISSING
from pfp_core.ext.mapping.module_mapping_trim import get_spec
from tests.pfp_core.ext.mapping._helpers import call_spec


def test_module_mapping_trim_trims_text_and_preserves_special_values() -> None:
    """trim strips edges, keeps empty text, and preserves MISSING/None."""
    spec = get_spec()
    assert spec.op_id == "trim"
    assert call_spec(spec, "  x  ", {}) == "x"
    assert call_spec(spec, "", {}) == ""
    assert call_spec(spec, MISSING, {}) is MISSING
    assert call_spec(spec, None, {}) is None


def test_module_mapping_trim_rejects_non_string() -> None:
    """trim raises ValueError for non-string values."""
    spec = get_spec()
    assert spec.op_id == "trim"
    with pytest.raises(ValueError):
        call_spec(spec, 1, {})
