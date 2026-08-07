from pfp_core.engine.mapping.runtime_values import (
    _apply_transform,
    _extract_by_source_path,
)
from pfp_core.engine.plan_types import (
    FieldMappingPlan,
    FieldPresencePlan,
    MappingOpCall,
)
from pfp_core.ext.ext_builtin_catalog import build_builtin_catalog


def test_extract_by_source_path_supports_nested_and_list() -> None:
    record = {"a": {"b": ["x", "y"]}}
    assert _extract_by_source_path(record, "a.b.1") == "y"


def test_apply_transform_unknown_op_adds_issue() -> None:
    issues: list[dict[str, str]] = []
    field = FieldMappingPlan(
        field_id="id",
        source_path="id",
        presence=FieldPresencePlan(behavior="omit_missing"),
    )
    current, stop = _apply_transform(
        catalog=build_builtin_catalog(),
        current="1",
        op_call=MappingOpCall(op_id="unknown"),
        field_plan=field,
        transform_index=0,
        issues=issues,
        issue_factory=lambda code, path, message: {
            "code": code,
            "path": path,
            "message": message,
        },
    )

    assert stop is True
    assert issues[0]["code"] == "EXEC_MAPPING_OP_NOT_FOUND"
    assert current is not None
