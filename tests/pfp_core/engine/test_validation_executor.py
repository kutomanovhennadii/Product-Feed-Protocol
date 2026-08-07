"""Unit tests for Story 6b.5 validation and mapping executors."""

from types import MappingProxyType
from typing import Mapping, cast

import pytest

from pfp_core.engine.plan_types import ValidationPlan, ValidationRulePlan
from pfp_core.engine.validation_executor import ValidationExecutor, ValidationReportItem
from pfp_core.ext import ExtCatalog, build_builtin_catalog
from pfp_core.policies import PolicyBundle, StrictnessPolicy
from pfp_utils.diagnostics.diagnostic_models import Diagnostic, DiagnosticSeverity


def test_validation_executor_pass_for_valid_required_field() -> None:
    """ValidationExecutor returns PASS when required field is present."""

    plan = ValidationPlan(
        rules=(
            ValidationRulePlan(
                rule_id="req_id",
                module_id="required",
                applies_to_field="id",
                config=MappingProxyType({}),
                on_fail_code="REQ_ID",
                on_fail_message="id is required",
            ),
        )
    )
    executor = ValidationExecutor(
        catalog=build_builtin_catalog(),
        policy_bundle=PolicyBundle(strictness=StrictnessPolicy("fail_on_error")),
    )

    result = executor.run_one(
        plan=plan,
        input_record={"id": "p1"},
        artifact_profile="catalog_snapshot",
    )

    assert result.decision == "PASS"
    assert result.is_valid is True
    assert result.items == ()


def test_validation_executor_drop_by_policy_for_missing_required() -> None:
    """ValidationExecutor applies DROP decision through strictness policy."""

    plan = ValidationPlan(
        rules=(
            ValidationRulePlan(
                rule_id="req_id",
                module_id="required",
                applies_to_field="id",
                config=MappingProxyType({}),
                on_fail_code="REQ_ID",
                on_fail_message="id is required",
            ),
        )
    )
    executor = ValidationExecutor(
        catalog=build_builtin_catalog(),
        policy_bundle=PolicyBundle(strictness=StrictnessPolicy("drop_invalid")),
    )

    result = executor.run_one(
        plan=plan,
        input_record={},
        artifact_profile="catalog_delta",
    )

    assert result.decision == "DROP"
    assert len(result.items) == 1
    assert result.items[0].code == "REQ_ID"
    assert result.items[0].path == "fields.id"


def test_validation_executor_warn_only_downgrades_failures() -> None:
    """ValidationExecutor downgrades failures to WARN via policy result."""

    plan = ValidationPlan(
        rules=(
            ValidationRulePlan(
                rule_id="req_title",
                module_id="required",
                applies_to_field="title",
                config=MappingProxyType({}),
                on_fail_code="REQ_TITLE",
            ),
        )
    )

    class _StrictnessResult:
        def __init__(self):
            self.diagnostics = [
                Diagnostic(
                    severity=DiagnosticSeverity.WARN,
                    code="REQ_TITLE",
                    message="id is required",
                    path="fields.title",
                )
            ]
            self.should_fail = False
            self.drop_invalid = False

    class _Strictness:
        @staticmethod
        def apply(diagnostics):
            _ = diagnostics
            return _StrictnessResult()

    class _Bundle:
        strictness = _Strictness()

    executor = ValidationExecutor(
        catalog=build_builtin_catalog(),
        policy_bundle=cast(PolicyBundle, _Bundle()),
    )

    result = executor.run_one(
        plan=plan,
        input_record={},
        artifact_profile="catalog_snapshot",
    )

    assert result.decision == "WARN"
    assert len(result.items) == 1
    assert result.items[0].DiagnosticSeverity == "WARN"


def test_validation_executor_reports_module_not_found_and_module_failed() -> None:
    """ValidationExecutor reports deterministic runtime diagnostics for missing and failed modules."""

    class _Module:
        @staticmethod
        def call(value, config, record=None, artifact_profile=None):
            _ = (value, config, record, artifact_profile)
            raise RuntimeError("boom")

    class _Catalog:
        @staticmethod
        def get_validation_module(module_id):
            if module_id == "explode":
                return _Module()
            raise KeyError(module_id)

    plan = ValidationPlan(
        rules=(
            ValidationRulePlan(
                rule_id="r1",
                module_id="missing",
                applies_to_field="id",
                config=MappingProxyType({}),
            ),
            ValidationRulePlan(
                rule_id="r2",
                module_id="explode",
                applies_to_field="id",
                config=MappingProxyType({}),
            ),
        )
    )
    executor = ValidationExecutor(catalog=cast(ExtCatalog, _Catalog()))

    result = executor.run_one(
        plan=plan,
        input_record={},
        artifact_profile="catalog_snapshot",
    )

    codes = {item.code for item in result.items}
    assert "EXEC_VALIDATION_MODULE_NOT_FOUND" in codes
    assert "EXEC_VALIDATION_MODULE_FAILED" in codes


def test_validation_executor_uses_result_code_message_and_path() -> None:
    """ValidationExecutor honors result code/message/path when rule overrides are absent."""

    class _Result:
        ok = False
        code = "MOD_CODE"
        message = "module message"
        path = "fields.title.value"

    class _Module:
        @staticmethod
        def call(value, config, record=None, artifact_profile=None):
            _ = (value, config, record, artifact_profile)
            return _Result()

    class _Catalog:
        @staticmethod
        def get_validation_module(module_id):
            assert module_id == "required"
            return _Module()

    plan = ValidationPlan(
        rules=(
            ValidationRulePlan(
                rule_id="r1",
                module_id="required",
                applies_to_field="title",
                config=MappingProxyType({}),
            ),
        )
    )
    executor = ValidationExecutor(catalog=cast(ExtCatalog, _Catalog()))

    result = executor.run_one(
        plan=plan,
        input_record={},
        artifact_profile="catalog_snapshot",
    )

    assert len(result.items) == 1
    assert result.items[0].code == "MOD_CODE"
    assert result.items[0].message == "module message"
    assert result.items[0].path == "fields.title.value"


def test_validation_executor_handles_bad_module_result_shape() -> None:
    """ValidationExecutor reports EXEC_VALIDATION_BAD_RESULT on invalid module payload."""

    class _Module:
        @staticmethod
        def call(value, config, record=None, artifact_profile=None):
            _ = (value, config, record, artifact_profile)
            return {"unexpected": True}

    class _Catalog:
        @staticmethod
        def get_validation_module(module_id):
            assert module_id == "required"
            return _Module()

    plan = ValidationPlan(
        rules=(
            ValidationRulePlan(
                rule_id="r1",
                module_id="required",
                applies_to_field="title",
                config=MappingProxyType({}),
            ),
        )
    )
    executor = ValidationExecutor(catalog=cast(ExtCatalog, _Catalog()))

    result = executor.run_one(
        plan=plan,
        input_record={},
        artifact_profile="catalog_snapshot",
    )

    assert result.decision == "FAIL"
    assert len(result.items) == 1
    assert result.items[0].code == "EXEC_VALIDATION_BAD_RESULT"


def test_validation_executor_strictness_length_mismatch_is_reported() -> None:
    """ValidationExecutor reports strictness result length mismatch deterministically."""

    class _StrictnessResult:
        def __init__(self):
            self.diagnostics = [
                Diagnostic(
                    severity=DiagnosticSeverity.ERROR,
                    code="X",
                    message="x",
                    path="$",
                )
            ]
            self.should_fail = False
            self.drop_invalid = False

    class _Strictness:
        @staticmethod
        def apply(diagnostics):
            _ = diagnostics
            return _StrictnessResult()

    class _Bundle:
        strictness = _Strictness()

    plan = ValidationPlan(
        rules=(
            ValidationRulePlan(
                rule_id="r1",
                module_id="required",
                applies_to_field="id",
                config=MappingProxyType({}),
                on_fail_code="REQ_ID",
            ),
            ValidationRulePlan(
                rule_id="r2",
                module_id="required",
                applies_to_field="title",
                config=MappingProxyType({}),
                on_fail_code="REQ_TITLE",
            ),
        )
    )
    executor = ValidationExecutor(
        catalog=build_builtin_catalog(),
        policy_bundle=cast(PolicyBundle, _Bundle()),
    )

    result = executor.run_one(
        plan=plan,
        input_record={},
        artifact_profile="catalog_snapshot",
    )

    assert any(
        item.code == "EXEC_STRICTNESS_RESULT_LENGTH_MISMATCH" for item in result.items
    )


def test_validation_executor_uses_record_scope_defaults() -> None:
    """ValidationExecutor resolves full record and default path for record-level rule."""

    class _Module:
        @staticmethod
        def call(value, config, record=None, artifact_profile=None):
            _ = (config, record, artifact_profile)
            assert isinstance(value, Mapping)
            return {"ok": False, "details": "record invalid"}

    class _Catalog:
        @staticmethod
        def get_validation_module(module_id):
            assert module_id == "record_check"
            return _Module()

    plan = ValidationPlan(
        rules=(
            ValidationRulePlan(
                rule_id="r1",
                module_id="record_check",
                applies_to_field=None,
                config=MappingProxyType({}),
            ),
        )
    )
    executor = ValidationExecutor(catalog=cast(ExtCatalog, _Catalog()))

    result = executor.run_one(
        plan=plan,
        input_record={"id": "p1"},
        artifact_profile="catalog_snapshot",
    )

    assert len(result.items) == 1
    assert result.items[0].path == "$"
    assert result.items[0].message == "record invalid"


def test_validation_report_item_requires_severity() -> None:
    """Validation report item constructor requires an explicit severity source."""

    with pytest.raises(TypeError, match="severity is required"):
        ValidationReportItem(
            code="CODE",
            message="message",
            path="fields.id",
            rule_id="rule",
            module_id="required",
        )


def test_validation_executor_skips_rules_when_mode_gate_disables_them(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Executor skips rules entirely when applicability gate returns false."""

    monkeypatch.setattr(
        "pfp_core.engine.validation_executor._rule_applies_to_mode",
        lambda rule, artifact_profile: False,
    )

    plan = ValidationPlan(
        rules=(
            ValidationRulePlan(
                rule_id="r1",
                module_id="required",
                applies_to_field="id",
                config=MappingProxyType({}),
            ),
        )
    )
    executor = ValidationExecutor(catalog=build_builtin_catalog())

    result = executor.run_one(
        plan=plan,
        input_record={},
        artifact_profile="catalog_snapshot",
    )

    assert result.items == ()
    assert result.decision == "PASS"


def test_validation_executor_normalizes_mapping_result_optional_fields() -> None:
    """ValidationExecutor normalizes mapping result with non-string optionals."""

    class _Module:
        @staticmethod
        def call(value, config, record=None, artifact_profile=None):
            _ = (value, config, record, artifact_profile)
            return {
                "ok": False,
                "code": 10,
                "message": {"x": 1},
                "details": 5,
                "path": ["bad"],
            }

    class _Catalog:
        @staticmethod
        def get_validation_module(module_id):
            assert module_id == "required"
            return _Module()

    plan = ValidationPlan(
        rules=(
            ValidationRulePlan(
                rule_id="r1",
                module_id="required",
                applies_to_field="id",
                config=MappingProxyType({}),
            ),
        )
    )
    executor = ValidationExecutor(catalog=cast(ExtCatalog, _Catalog()))

    result = executor.run_one(
        plan=plan,
        input_record={},
        artifact_profile="catalog_snapshot",
    )

    assert len(result.items) == 1
    assert result.items[0].code == "VALIDATION_FAILED"
    assert result.items[0].message == "Validation failed: required"
    assert result.items[0].path == "fields.id"


def test_validation_executor_rejects_object_result_without_ok_bool() -> None:
    """ValidationExecutor marks object result invalid when ok is absent or not bool."""

    class _NoOkResult:
        code = "X"

    class _BadOkResult:
        ok = "yes"
        code = "X"

    class _ModuleNoOk:
        @staticmethod
        def call(value, config, record=None, artifact_profile=None):
            _ = (value, config, record, artifact_profile)
            return _NoOkResult()

    class _ModuleBadOk:
        @staticmethod
        def call(value, config, record=None, artifact_profile=None):
            _ = (value, config, record, artifact_profile)
            return _BadOkResult()

    class _CatalogNoOk:
        @staticmethod
        def get_validation_module(module_id):
            assert module_id == "required"
            return _ModuleNoOk()

    class _CatalogBadOk:
        @staticmethod
        def get_validation_module(module_id):
            assert module_id == "required"
            return _ModuleBadOk()

    plan = ValidationPlan(
        rules=(
            ValidationRulePlan(
                rule_id="r1",
                module_id="required",
                applies_to_field="id",
                config=MappingProxyType({}),
            ),
        )
    )

    no_ok_result = ValidationExecutor(catalog=cast(ExtCatalog, _CatalogNoOk())).run_one(
        plan=plan,
        input_record={},
        artifact_profile="catalog_snapshot",
    )
    bad_ok_result = ValidationExecutor(
        catalog=cast(ExtCatalog, _CatalogBadOk())
    ).run_one(
        plan=plan,
        input_record={},
        artifact_profile="catalog_snapshot",
    )

    assert len(no_ok_result.items) == 1
    assert no_ok_result.items[0].code == "EXEC_VALIDATION_BAD_RESULT"
    assert len(bad_ok_result.items) == 1
    assert bad_ok_result.items[0].code == "EXEC_VALIDATION_BAD_RESULT"


def test_validation_executor_severity_and_decision_via_run_one() -> None:
    """ValidationExecutor keeps DiagnosticSeverity/decision semantics through run_one contract."""

    class _Module:
        @staticmethod
        def call(value, config, record=None, artifact_profile=None):
            _ = (value, config, record, artifact_profile)
            return {"ok": False, "details": "fail"}

    class _Catalog:
        @staticmethod
        def get_validation_module(module_id):
            assert module_id == "required"
            return _Module()

    warn_plan = ValidationPlan(
        rules=(
            ValidationRulePlan(
                rule_id="r_warn",
                module_id="required",
                applies_to_field="id",
                config=MappingProxyType({}),
                severity_hint="WARN",
            ),
        )
    )
    warn_result = ValidationExecutor(catalog=cast(ExtCatalog, _Catalog())).run_one(
        plan=warn_plan,
        input_record={"id": "x"},
        artifact_profile="catalog_snapshot",
    )
    assert warn_result.decision == "WARN"
    assert warn_result.items[0].DiagnosticSeverity == "WARN"

    drop_plan = ValidationPlan(
        rules=(
            ValidationRulePlan(
                rule_id="r_drop",
                module_id="required",
                applies_to_field="id",
                config=MappingProxyType({}),
                severity_hint="DROP",
            ),
        )
    )
    drop_result = ValidationExecutor(catalog=cast(ExtCatalog, _Catalog())).run_one(
        plan=drop_plan,
        input_record={"id": "x"},
        artifact_profile="catalog_snapshot",
    )
    assert drop_result.decision == "DROP"
    assert drop_result.items[0].DiagnosticSeverity == "DROP"

    fail_plan = ValidationPlan(
        rules=(
            ValidationRulePlan(
                rule_id="r_fail",
                module_id="required",
                applies_to_field="id",
                config=MappingProxyType({}),
                severity_hint="UNKNOWN",
            ),
        )
    )
    fail_result = ValidationExecutor(catalog=cast(ExtCatalog, _Catalog())).run_one(
        plan=fail_plan,
        input_record={"id": "x"},
        artifact_profile="catalog_snapshot",
    )
    assert fail_result.decision == "FAIL"
    assert fail_result.items[0].DiagnosticSeverity == "FAIL"
