import pytest

from pfp_core.ext.ext_types import MISSING
from pfp_core.ext.mapping.module_mapping_normalize_whitespace import get_spec
from tests.pfp_core.ext.mapping._helpers import call_spec


def test_module_mapping_normalize_whitespace_transforms_input() -> None:
    """normalize_whitespace collapses internal whitespace and trims result."""
    spec = get_spec()
    assert spec.op_id == "normalize_whitespace"
    assert call_spec(spec, " a\n\tb  c ", {}) == "a b c"
    assert call_spec(spec, MISSING, {}) is MISSING
    assert call_spec(spec, None, {}) is None

    with pytest.raises(ValueError):
        call_spec(spec, 1, {})
