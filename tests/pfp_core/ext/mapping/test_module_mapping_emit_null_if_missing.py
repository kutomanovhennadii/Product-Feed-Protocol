from pfp_core.ext.ext_types import MISSING, Emission
from pfp_core.ext.mapping.module_mapping_emit_null_if_missing import get_spec
from tests.pfp_core.ext.mapping._helpers import call_spec


def test_module_mapping_emit_null_if_missing_always_returns_null_emission() -> None:
    """emit_null_if_missing always emits NULL regardless of input presence."""
    spec = get_spec()
    assert spec.op_id == "emit_null_if_missing"
    missing_result = call_spec(spec, MISSING, {})
    value_result = call_spec(spec, "value", {})

    assert isinstance(missing_result, Emission)
    assert missing_result.kind == "NULL"
    assert missing_result.value is None

    assert isinstance(value_result, Emission)
    assert value_result.kind == "NULL"
    assert value_result.value is None
