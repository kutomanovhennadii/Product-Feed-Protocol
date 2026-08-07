from pfp_core.ext.ext_types import MISSING
from pfp_core.ext.mapping.module_mapping_to_str import get_spec
from tests.pfp_core.ext.mapping._helpers import call_spec


def test_module_mapping_to_str_preserves_missing_and_converts() -> None:
    """to_str preserves MISSING and converts scalar values to text."""
    spec = get_spec()
    assert spec.op_id == "to_str"
    assert call_spec(spec, MISSING, {}) is MISSING
    assert call_spec(spec, 10, {}) == "10"
