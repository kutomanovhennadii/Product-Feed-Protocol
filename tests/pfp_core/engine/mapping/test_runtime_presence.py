from pfp_core.engine.mapping.runtime_presence import _apply_presence
from pfp_core.engine.plan_types import FieldMappingPlan, FieldPresencePlan
from pfp_core.ext.ext_types import MISSING


def test_apply_presence_emit_null_if_missing() -> None:
    issues: list[dict[str, str]] = []
    field = FieldMappingPlan(
        field_id="title",
        source_path="title",
        presence=FieldPresencePlan(behavior="emit_null_if_missing"),
    )
    emission = _apply_presence(
        current=MISSING,
        field_plan=field,
        issues=issues,
        issue_factory=lambda code, path, message: {
            "code": code,
            "path": path,
            "message": message,
        },
    )

    assert emission.kind == "NULL"
