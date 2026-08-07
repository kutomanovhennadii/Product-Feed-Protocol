from pfp_core.engine.plan_types import CompileDiagItem
from pfp_core.engine.validation.semantics import (
    check_validation_field_semantics,
    update_required_by_profile_sources,
)


def test_check_validation_field_semantics_reports_unknown_field() -> None:
    diagnostics: list[CompileDiagItem] = []
    check_validation_field_semantics(
        applies_field="missing",
        known_fields={"id"},
        field_final_types={"id": "string"},
        expected_value_type="string",
        module_id="required",
        rule_path="validation.rules[0]",
        diagnostics=diagnostics,
    )

    assert diagnostics[0].code == "COMPILER_FIELD_UNDEFINED"


def test_update_required_by_profile_sources_fills_profiles() -> None:
    sources: dict[str, dict[str, str]] = {}
    update_required_by_profile_sources(
        applies_field="id",
        module_id="required_if_profile",
        rule_path="validation.rules[0]",
        required_by_profile_sources=sources,
        artifact_profile_filters=("catalog_snapshot",),
    )

    assert sources["id"]["catalog_snapshot"].endswith(".module_id")


def test_check_validation_field_semantics_reports_type_mismatch() -> None:
    diagnostics: list[CompileDiagItem] = []
    check_validation_field_semantics(
        applies_field="id",
        known_fields={"id"},
        field_final_types={"id": "string"},
        expected_value_type="int",
        module_id="required",
        rule_path="validation.rules[0]",
        diagnostics=diagnostics,
    )

    assert len(diagnostics) == 1
    assert diagnostics[0].code == "SCHEMA_TYPE_VALIDATION_MISMATCH"


def test_update_required_by_mode_sources_ignores_non_required_modules() -> None:
    sources: dict[str, dict[str, str]] = {}
    update_required_by_profile_sources(
        applies_field="id",
        module_id="required",
        rule_path="validation.rules[0]",
        required_by_profile_sources=sources,
        artifact_profile_filters=("catalog_snapshot",),
    )

    assert sources == {}
