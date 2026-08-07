"""Root-level contract tests for `pfp_core.engine.plan_types`."""

from dataclasses import FrozenInstanceError
from typing import Any, cast

import pytest

from pfp_core.engine.plan_types import (
    CompileDiagItem,
    FieldMappingPlan,
    FieldPresencePlan,
    MappingPlan,
    ValidationPlan,
    ValidationRulePlan,
    WriterSpec,
    sort_compile_diagnostics,
)


def test_plan_type_defaults_use_immutable_mappings() -> None:
    field_presence = FieldPresencePlan(behavior="omit_missing")
    mapping_plan = MappingPlan(output_kind="json_object")
    validation_rule = ValidationRulePlan(module_id="required")
    writer_spec = WriterSpec(
        writer_id="csv",
        artifact_content_type="text/csv",
        artifact_file_extension=".csv",
    )

    with pytest.raises(FrozenInstanceError):
        cast(Any, field_presence).behavior = "emit_null"

    with pytest.raises(TypeError):
        cast(Any, mapping_plan.fields)["id"] = mapping_plan.fields.get("id")

    with pytest.raises(TypeError):
        cast(Any, validation_rule.config)["x"] = 1

    with pytest.raises(TypeError):
        cast(Any, writer_spec.writer_config)["x"] = 1


def test_plan_type_defaults_use_expected_empty_shapes() -> None:
    mapping_plan = MappingPlan(output_kind="json_object")
    field_plan = FieldMappingPlan(field_id="id", source_path="id")
    validation_plan = ValidationPlan()

    assert mapping_plan.output_order is None
    assert dict(mapping_plan.fields) == {}
    assert field_plan.transforms == ()
    assert validation_plan.rules == ()


def test_plan_type_dataclasses_are_frozen() -> None:
    item = CompileDiagItem(code="C", path="p", message="m")

    with pytest.raises(FrozenInstanceError):
        cast(Any, item).code = "NEW"


def test_sort_compile_diagnostics_is_deterministic_and_ordered() -> None:
    items = [
        CompileDiagItem(code="B", path="z", message="2", DiagnosticSeverity="WARN"),
        CompileDiagItem(code="A", path="b", message="3", DiagnosticSeverity="ERROR"),
        CompileDiagItem(code="A", path="a", message="1", DiagnosticSeverity="ERROR"),
    ]

    first = sort_compile_diagnostics(items)
    second = sort_compile_diagnostics(items)

    assert first == second
    assert [item.DiagnosticSeverity for item in first] == ["ERROR", "ERROR", "WARN"]
    assert [item.path for item in first] == ["a", "b", "z"]
