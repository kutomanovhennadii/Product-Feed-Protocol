"""Unit tests for Story 6b.5 validation and mapping executors."""

from types import MappingProxyType
from typing import Mapping, cast

import pytest

from pfp_core.engine.mapping_executor import MappingExecutor
from pfp_core.engine.plan_types import (
    FieldMappingPlan,
    FieldPresencePlan,
    MappingOpCall,
    MappingPlan,
)
from pfp_core.ext import ExtCatalog, build_builtin_catalog
from pfp_core.ext.ext_types import Emission


def _mapping_plan_csv() -> MappingPlan:
    """Build deterministic CSV mapping plan for tests."""

    return MappingPlan(
        output_kind="csv_row",
        output_order=("id", "title"),
        fields=MappingProxyType(
            {
                "id": FieldMappingPlan(
                    field_id="id",
                    source_path="id",
                    transforms=(MappingOpCall(op_id="to_str"),),
                    presence=FieldPresencePlan(behavior="omit_missing"),
                ),
                "title": FieldMappingPlan(
                    field_id="title",
                    source_path="attributes.title",
                    transforms=(
                        MappingOpCall(op_id="to_str"),
                        MappingOpCall(op_id="trim"),
                    ),
                    presence=FieldPresencePlan(behavior="emit_null_if_missing"),
                ),
            }
        ),
    )


def test_mapping_executor_csv_row_happy_path() -> None:
    """MappingExecutor produces CSV row emissions in output_order order."""

    executor = MappingExecutor(catalog=build_builtin_catalog())
    result = executor.run_one(
        plan=_mapping_plan_csv(),
        input_record={"id": 10, "attributes": {"title": "  Product  "}},
        artifact_profile="catalog_snapshot",
    )

    assert result.issues == ()
    assert isinstance(result.output, tuple)
    assert result.output == (
        Emission(kind="VALUE", value="10"),
        Emission(kind="VALUE", value="Product"),
    )


@pytest.mark.skip(
    reason=(
        "Temporary disabled: legacy omit_missing expectation while mapping "
        "semantics are being finalized for schema-driven line."
    )
)
def test_mapping_executor_json_object_omit_missing_field() -> None:
    """MappingExecutor omits missing field for json_object with omit_missing."""

    plan = MappingPlan(
        output_kind="json_object",
        fields=MappingProxyType(
            {
                "title": FieldMappingPlan(
                    field_id="title",
                    source_path="title",
                    transforms=(MappingOpCall(op_id="to_str"),),
                    presence=FieldPresencePlan(behavior="omit_missing"),
                )
            }
        ),
    )
    executor = MappingExecutor(catalog=build_builtin_catalog())

    result = executor.run_one(
        plan=plan,
        input_record={},
        artifact_profile="catalog_delta",
    )

    assert result.issues == ()
    assert isinstance(result.output, Mapping)
    assert "title" not in result.output


def test_mapping_executor_transform_on_missing_default() -> None:
    """MappingExecutor applies on_missing=default before calling transform."""

    plan = MappingPlan(
        output_kind="json_object",
        fields=MappingProxyType(
            {
                "title": FieldMappingPlan(
                    field_id="title",
                    source_path="title",
                    transforms=(
                        MappingOpCall(
                            op_id="to_str",
                            args=MappingProxyType({"default": "fallback-title"}),
                            on_missing="default",
                        ),
                    ),
                    presence=FieldPresencePlan(behavior="omit_missing"),
                )
            }
        ),
    )
    executor = MappingExecutor(catalog=build_builtin_catalog())

    result = executor.run_one(
        plan=plan,
        input_record={},
        artifact_profile="catalog_snapshot",
    )

    assert result.issues == ()
    mapped_output = cast(Mapping[str, Emission], result.output)
    assert mapped_output["title"] == Emission(kind="VALUE", value="fallback-title")


def test_mapping_executor_deterministic_for_same_input() -> None:
    """MappingExecutor returns deterministic output and issue ordering."""

    executor = MappingExecutor(catalog=build_builtin_catalog())
    plan = _mapping_plan_csv()
    record = {"id": 5, "attributes": {"title": "A"}}

    first = executor.run_one(
        plan=plan,
        input_record=record,
        artifact_profile="catalog_snapshot",
    )
    second = executor.run_one(
        plan=plan,
        input_record=record,
        artifact_profile="catalog_snapshot",
    )

    assert first.output == second.output
    assert first.issues == second.issues


def test_mapping_executor_csv_reports_missing_field_from_output_order() -> None:
    """MappingExecutor reports missing field id from csv output_order deterministically."""

    plan = MappingPlan(
        output_kind="csv_row",
        output_order=("missing",),
        fields=MappingProxyType({}),
    )
    executor = MappingExecutor(catalog=build_builtin_catalog())

    result = executor.run_one(
        plan=plan,
        input_record={},
        artifact_profile="catalog_snapshot",
    )

    assert result.output == (Emission(kind="OMIT"),)
    assert len(result.issues) == 1
    assert result.issues[0].code == "EXEC_MAPPING_FIELD_NOT_FOUND"


def test_mapping_executor_csv_without_output_order_reports_issue() -> None:
    """MappingExecutor reports missing csv output_order and falls back to sorted fields."""

    plan = MappingPlan(
        output_kind="csv_row",
        output_order=None,
        fields=MappingProxyType(
            {
                "a": FieldMappingPlan(
                    field_id="a",
                    source_path="a",
                    transforms=(),
                    presence=FieldPresencePlan(behavior="emit_null_if_missing"),
                )
            }
        ),
    )
    executor = MappingExecutor(catalog=build_builtin_catalog())

    result = executor.run_one(
        plan=plan,
        input_record={},
        artifact_profile="catalog_snapshot",
    )

    assert len(result.issues) == 1
    assert result.issues[0].code == "EXEC_MAPPING_OUTPUT_ORDER_MISSING"


def test_mapping_executor_transform_missing_error_and_default_required() -> None:
    """MappingExecutor emits deterministic issues for on_missing error/default branches."""

    plan = MappingPlan(
        output_kind="json_object",
        fields=MappingProxyType(
            {
                "a": FieldMappingPlan(
                    field_id="a",
                    source_path="a",
                    transforms=(MappingOpCall(op_id="to_str", on_missing="error"),),
                    presence=FieldPresencePlan(behavior="omit_missing"),
                ),
                "b": FieldMappingPlan(
                    field_id="b",
                    source_path="b",
                    transforms=(MappingOpCall(op_id="to_str", on_missing="default"),),
                    presence=FieldPresencePlan(behavior="omit_missing"),
                ),
            }
        ),
    )
    executor = MappingExecutor(catalog=build_builtin_catalog())

    result = executor.run_one(
        plan=plan,
        input_record={},
        artifact_profile="catalog_snapshot",
    )

    codes = {item.code for item in result.issues}
    assert "EXEC_MAPPING_MISSING_ERROR" in codes
    assert "EXEC_MAPPING_ON_MISSING_DEFAULT_REQUIRED" in codes


def test_mapping_executor_reports_unsupported_delete_tombstone() -> None:
    """Executor emits delete-unsupported issue when delete intent is present without support."""

    plan = MappingPlan(
        output_kind="csv_row",
        output_order=(),
        fields=MappingProxyType({}),
        delete_tombstone_enabled=False,
    )
    executor = MappingExecutor(catalog=build_builtin_catalog())

    result = executor.run_one(
        plan=plan,
        input_record={"delete": True},
        artifact_profile="catalog_snapshot",
    )

    assert any(issue.code == "CONTRACT.DELETE_UNSUPPORTED" for issue in result.issues)


def test_mapping_executor_reports_op_not_found_and_op_failed() -> None:
    """MappingExecutor reports missing operation and operation failure branches."""

    class _OpSpec:
        @staticmethod
        def call(value, args):
            _ = (value, args)
            raise RuntimeError("boom")

    class _Catalog:
        @staticmethod
        def get_mapping_op(op_id):
            if op_id == "explode":
                return _OpSpec()
            raise KeyError(op_id)

    plan = MappingPlan(
        output_kind="json_object",
        fields=MappingProxyType(
            {
                "a": FieldMappingPlan(
                    field_id="a",
                    source_path="a",
                    transforms=(MappingOpCall(op_id="unknown"),),
                    presence=FieldPresencePlan(behavior="omit_missing"),
                ),
                "b": FieldMappingPlan(
                    field_id="b",
                    source_path="b",
                    transforms=(MappingOpCall(op_id="explode"),),
                    presence=FieldPresencePlan(behavior="omit_missing"),
                ),
            }
        ),
    )
    executor = MappingExecutor(catalog=cast(ExtCatalog, _Catalog()))

    result = executor.run_one(
        plan=plan,
        input_record={"a": "x", "b": "y"},
        artifact_profile="catalog_snapshot",
    )

    codes = {item.code for item in result.issues}
    assert "EXEC_MAPPING_OP_NOT_FOUND" in codes
    assert "EXEC_MAPPING_OP_FAILED" in codes


def test_mapping_executor_presence_error_if_missing_branch() -> None:
    """MappingExecutor reports presence error when missing value meets error_if_missing."""

    plan = MappingPlan(
        output_kind="json_object",
        fields=MappingProxyType(
            {
                "a": FieldMappingPlan(
                    field_id="a",
                    source_path="a",
                    transforms=(),
                    presence=FieldPresencePlan(behavior="error_if_missing"),
                )
            }
        ),
    )
    executor = MappingExecutor(catalog=build_builtin_catalog())

    result = executor.run_one(
        plan=plan,
        input_record={},
        artifact_profile="catalog_snapshot",
    )

    assert len(result.issues) == 1
    assert result.issues[0].code == "EXEC_MAPPING_PRESENCE_ERROR"


def test_mapping_executor_on_missing_omit_and_pass_paths() -> None:
    """MappingExecutor covers on_missing omit and pass branches deterministically."""

    plan = MappingPlan(
        output_kind="json_object",
        fields=MappingProxyType(
            {
                "omit_field": FieldMappingPlan(
                    field_id="omit_field",
                    source_path="omit_field",
                    transforms=(MappingOpCall(op_id="to_str", on_missing="omit"),),
                    presence=FieldPresencePlan(behavior="omit_missing"),
                ),
                "pass_field": FieldMappingPlan(
                    field_id="pass_field",
                    source_path="pass_field",
                    transforms=(MappingOpCall(op_id="to_str", on_missing="pass"),),
                    presence=FieldPresencePlan(behavior="emit_null_if_missing"),
                ),
            }
        ),
    )
    executor = MappingExecutor(catalog=build_builtin_catalog())

    result = executor.run_one(
        plan=plan,
        input_record={},
        artifact_profile="catalog_snapshot",
    )

    assert result.issues == ()
    mapped_output = cast(Mapping[str, Emission], result.output)
    assert "omit_field" not in mapped_output
    assert mapped_output["pass_field"] == Emission(kind="NULL")


def test_mapping_executor_presence_and_path_edge_branches() -> None:
    """MappingExecutor covers emission passthrough, None/null and source-path edge cases."""

    plan = MappingPlan(
        output_kind="json_object",
        fields=MappingProxyType(
            {
                "none_value": FieldMappingPlan(
                    field_id="none_value",
                    source_path="none_value",
                    transforms=(),
                    presence=FieldPresencePlan(behavior="omit_missing"),
                ),
                "empty_path": FieldMappingPlan(
                    field_id="empty_path",
                    source_path="",
                    transforms=(),
                    presence=FieldPresencePlan(behavior="omit_missing"),
                ),
                "bad_list_index": FieldMappingPlan(
                    field_id="bad_list_index",
                    source_path="items.bad",
                    transforms=(),
                    presence=FieldPresencePlan(behavior="emit_null_if_missing"),
                ),
                "out_of_range": FieldMappingPlan(
                    field_id="out_of_range",
                    source_path="items.5",
                    transforms=(),
                    presence=FieldPresencePlan(behavior="emit_null_if_missing"),
                ),
                "valid_list_path": FieldMappingPlan(
                    field_id="valid_list_path",
                    source_path="items.0",
                    transforms=(),
                    presence=FieldPresencePlan(behavior="omit_missing"),
                ),
                "non_collection": FieldMappingPlan(
                    field_id="non_collection",
                    source_path="value.sub",
                    transforms=(),
                    presence=FieldPresencePlan(behavior="emit_null_if_missing"),
                ),
            }
        ),
    )
    executor = MappingExecutor(catalog=build_builtin_catalog())

    result = executor.run_one(
        plan=plan,
        input_record={"none_value": None, "items": ["x"], "value": "leaf"},
        artifact_profile="catalog_snapshot",
    )

    assert result.issues == ()
    mapped_output = cast(Mapping[str, Emission], result.output)
    assert mapped_output["none_value"] == Emission(kind="NULL")
    assert "empty_path" not in mapped_output
    assert mapped_output["bad_list_index"] == Emission(kind="NULL")
    assert mapped_output["out_of_range"] == Emission(kind="NULL")
    assert mapped_output["valid_list_path"] == Emission(kind="VALUE", value="x")
    assert mapped_output["non_collection"] == Emission(kind="NULL")


def test_mapping_executor_keeps_emission_from_transform() -> None:
    """MappingExecutor preserves Emission values returned by mapping op."""

    class _OpSpec:
        @staticmethod
        def call(value, args):
            _ = (value, args)
            return Emission(kind="NULL")

    class _Catalog:
        @staticmethod
        def get_mapping_op(op_id):
            assert op_id == "emit"
            return _OpSpec()

    plan = MappingPlan(
        output_kind="json_object",
        fields=MappingProxyType(
            {
                "a": FieldMappingPlan(
                    field_id="a",
                    source_path="a",
                    transforms=(MappingOpCall(op_id="emit"),),
                    presence=FieldPresencePlan(behavior="omit_missing"),
                )
            }
        ),
    )
    executor = MappingExecutor(catalog=cast(ExtCatalog, _Catalog()))

    result = executor.run_one(
        plan=plan,
        input_record={"a": "x"},
        artifact_profile="catalog_snapshot",
    )

    assert result.issues == ()
    mapped_output = cast(Mapping[str, Emission], result.output)
    assert mapped_output["a"] == Emission(kind="NULL")


def test_mapping_executor_csv_tombstone_omits_non_id_fields() -> None:
    """Ensure CSV tombstones keep only the configured identifier field."""

    plan = MappingPlan(
        output_kind="csv_row",
        output_order=("id", "title"),
        delete_tombstone_enabled=True,
        delete_tombstone_flag_path="delete",
        delete_tombstone_id_field="id",
        fields=MappingProxyType(
            {
                "id": FieldMappingPlan(
                    field_id="id",
                    source_path="id",
                    transforms=(),
                    presence=FieldPresencePlan(behavior="emit_null_if_missing"),
                ),
                "title": FieldMappingPlan(
                    field_id="title",
                    source_path="title",
                    transforms=(),
                    presence=FieldPresencePlan(behavior="emit_null_if_missing"),
                ),
            }
        ),
    )
    executor = MappingExecutor(catalog=build_builtin_catalog())

    result = executor.run_one(
        plan=plan,
        input_record={"id": 1, "title": "x", "delete": True},
        artifact_profile="catalog_delta",
    )

    assert result.issues == ()
    assert result.output == (
        Emission(kind="VALUE", value="1"),
        Emission(kind="OMIT"),
    )
