from pfp_core.engine.compile_support.types import (
    is_type_mismatch,
    is_validation_type_mismatch,
    to_plan_type_id,
)


def test_compiler_type_helpers() -> None:
    assert to_plan_type_id("string") == "string"
    assert to_plan_type_id("unknown") is None
    assert is_type_mismatch(current_type="string", expected_input="int") is True
    assert (
        is_validation_type_mismatch(
            field_type="string",
            expected_value_type="int",
        )
        is True
    )


def test_is_validation_type_mismatch_ignores_unknown_field_type() -> None:
    assert (
        is_validation_type_mismatch(
            field_type=None,
            expected_value_type="string",
        )
        is False
    )
