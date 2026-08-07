import pytest

from pfp_core.ext.ext_types import MISSING
from pfp_core.ext.mapping.module_mapping_get_path import get_spec
from tests.pfp_core.ext.mapping._helpers import call_spec


def test_module_mapping_get_path_returns_value_and_missing() -> None:
    """get_path returns extracted value or the MISSING sentinel."""
    spec = get_spec()
    assert spec.op_id == "get_path"
    doc = {"a": {"b": 1}}
    assert call_spec(spec, doc, {"path": "a.b"}) == 1
    assert call_spec(spec, doc, {"path": "a.c"}) is MISSING


def test_module_mapping_get_path_list_indexing_and_invalid_path() -> None:
    """get_path supports list indexing and rejects invalid path args."""
    spec = get_spec()
    assert spec.op_id == "get_path"
    doc = {"a": [{"b": 1}, {"b": 2}]}
    assert call_spec(spec, doc, {"path": "a.1.b"}) == 2
    assert call_spec(spec, doc, {"path": "a.2.b"}) is MISSING
    assert call_spec(spec, doc, {"path": "a.-1.b"}) is MISSING
    assert call_spec(spec, doc, {"path": "a.x.b"}) is MISSING

    with pytest.raises(ValueError):
        call_spec(spec, doc, {"path": ""})
