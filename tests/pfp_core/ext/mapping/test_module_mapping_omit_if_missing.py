from pfp_core.ext.ext_types import MISSING, Emission
from pfp_core.ext.mapping.module_mapping_omit_if_missing import get_spec
from tests.pfp_core.ext.mapping._helpers import call_spec


def test_module_mapping_omit_if_missing_always_returns_omit_emission() -> None:
    """omit_if_missing always emits OMIT regardless of input presence."""
    spec = get_spec()
    assert spec.op_id == "omit_if_missing"
    missing_result = call_spec(spec, MISSING, {})
    value_result = call_spec(spec, "value", {})

    assert isinstance(missing_result, Emission)
    assert missing_result.kind == "OMIT"
    assert missing_result.value is None

    assert isinstance(value_result, Emission)
    assert value_result.kind == "OMIT"
    assert value_result.value is None
