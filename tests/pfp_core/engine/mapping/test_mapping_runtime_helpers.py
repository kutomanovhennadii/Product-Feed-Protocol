"""Tests for mapping runtime helpers."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from pfp_core.engine.mapping import _apply_transform, _extract_by_source_path
from pfp_core.engine.plan_types import FieldMappingPlan, MappingOpCall
from pfp_core.ext.ext_catalog import ExtCatalog
from pfp_core.ext.ext_types import MISSING


class _CatalogStub(ExtCatalog):
    def __init__(self, specs: dict[str, Any]) -> None:
        self._specs = specs

    def get_mapping_op(self, op_id: str) -> Any:
        return self._specs[op_id]


def _issue(code: str, path: str, message: str) -> tuple[str, str, str]:
    return code, path, message


def test_extract_by_source_path_handles_nested_mappings_and_lists() -> None:
    """Extractor resolves nested mappings, list indexes, and missing paths."""

    payload = {"items": [{"sku": "SKU-1"}], "name": "Widget"}

    assert _extract_by_source_path(payload, "items.0.sku") == "SKU-1"
    assert _extract_by_source_path(payload, "name") == "Widget"
    assert _extract_by_source_path(payload, "") is MISSING
    assert _extract_by_source_path(payload, "items.1.sku") is MISSING
    assert _extract_by_source_path(payload, "items.bad.sku") is MISSING
    assert _extract_by_source_path(payload, "missing") is MISSING
    assert _extract_by_source_path(payload, "name.value") is MISSING


def test_apply_transform_honors_on_missing_modes() -> None:
    """Transform helper applies omit, pass, default, and error missing behaviors."""

    field_plan = FieldMappingPlan(field_id="title", source_path="title")
    catalog = _CatalogStub({})
    issues: list[tuple[str, str, str]] = []

    value, stop = _apply_transform(
        catalog=catalog,
        current=MISSING,
        op_call=MappingOpCall(op_id="noop", on_missing="omit"),
        field_plan=field_plan,
        transform_index=0,
        issues=issues,
        issue_factory=_issue,
    )
    assert value is MISSING
    assert stop is True

    value, stop = _apply_transform(
        catalog=catalog,
        current=MISSING,
        op_call=MappingOpCall(op_id="noop", on_missing="pass"),
        field_plan=field_plan,
        transform_index=1,
        issues=issues,
        issue_factory=_issue,
    )
    assert value is MISSING
    assert stop is False

    value, stop = _apply_transform(
        catalog=catalog,
        current=MISSING,
        op_call=MappingOpCall(
            op_id="noop",
            on_missing="default",
            args={"default": "fallback"},
        ),
        field_plan=field_plan,
        transform_index=2,
        issues=issues,
        issue_factory=_issue,
    )
    assert value == "fallback"
    assert stop is False

    value, stop = _apply_transform(
        catalog=catalog,
        current=MISSING,
        op_call=MappingOpCall(op_id="noop", on_missing="default"),
        field_plan=field_plan,
        transform_index=3,
        issues=issues,
        issue_factory=_issue,
    )
    assert value is MISSING
    assert stop is True
    assert issues[-1][0] == "EXEC_MAPPING_ON_MISSING_DEFAULT_REQUIRED"

    value, stop = _apply_transform(
        catalog=catalog,
        current=MISSING,
        op_call=MappingOpCall(op_id="noop", on_missing="error"),
        field_plan=field_plan,
        transform_index=4,
        issues=issues,
        issue_factory=_issue,
    )
    assert value is MISSING
    assert stop is True
    assert issues[-1][0] == "EXEC_MAPPING_MISSING_ERROR"


def test_apply_transform_reports_catalog_lookup_and_runtime_failures() -> None:
    """Transform helper reports missing ops and runtime execution failures."""

    field_plan = FieldMappingPlan(field_id="title", source_path="title")
    issues: list[tuple[str, str, str]] = []

    value, stop = _apply_transform(
        catalog=_CatalogStub({}),
        current="value",
        op_call=MappingOpCall(op_id="missing-op"),
        field_plan=field_plan,
        transform_index=0,
        issues=issues,
        issue_factory=_issue,
    )
    assert value is MISSING
    assert stop is True
    assert issues[-1][0] == "EXEC_MAPPING_OP_NOT_FOUND"

    failing_spec = SimpleNamespace(call=lambda current, args: 1 / 0)
    value, stop = _apply_transform(
        catalog=_CatalogStub({"explode": failing_spec}),
        current="value",
        op_call=MappingOpCall(op_id="explode"),
        field_plan=field_plan,
        transform_index=1,
        issues=issues,
        issue_factory=_issue,
    )
    assert value is MISSING
    assert stop is True
    assert issues[-1][0] == "EXEC_MAPPING_OP_FAILED"


def test_apply_transform_returns_operation_output_on_success() -> None:
    """Transform helper returns transformed value when op succeeds."""

    field_plan = FieldMappingPlan(field_id="title", source_path="title")
    issues: list[tuple[str, str, str]] = []
    spec = SimpleNamespace(call=lambda current, args: f"{current}:{args['suffix']}")

    value, stop = _apply_transform(
        catalog=_CatalogStub({"append": spec}),
        current="SKU",
        op_call=MappingOpCall(op_id="append", args={"suffix": "1"}),
        field_plan=field_plan,
        transform_index=0,
        issues=issues,
        issue_factory=_issue,
    )

    assert value == "SKU:1"
    assert stop is False
    assert issues == []
