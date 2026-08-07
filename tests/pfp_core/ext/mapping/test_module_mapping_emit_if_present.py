from pfp_core.ext.ext_types import MISSING, Emission
from pfp_core.ext.mapping.module_mapping_emit_if_present import get_spec
from tests.pfp_core.ext.mapping._helpers import call_spec


def test_module_mapping_presence_helpers_emit_expected_kinds() -> None:
    """emit_if_present emits VALUE/OMIT/NULL according to input presence."""
    spec = get_spec()
    assert spec.op_id == "emit_if_present"
    omit = call_spec(spec, MISSING, {})
    null = call_spec(spec, None, {})
    val = call_spec(spec, 7, {})

    assert isinstance(omit, Emission)
    assert omit.kind == "OMIT"
    assert null.kind == "NULL"
    assert val.kind == "VALUE"
    assert val.value == "7"
