"""Tests for validation compile helpers."""

from pfp_core.engine.plan_types import CompileDiagItem
from pfp_core.engine.validation import (
    CANONICAL_ARTIFACT_PROFILES,
    check_validation_field_semantics,
    update_required_by_profile_sources,
)


def test_check_validation_field_semantics_reports_unknown_fields() -> None:
    """Unknown applies_to fields emit deterministic compiler diagnostics."""

    diagnostics: list[CompileDiagItem] = []

    check_validation_field_semantics(
        applies_field="title",
        known_fields={"sku"},
        field_final_types={},
        expected_value_type="string",
        module_id="required",
        rule_path="validation.rules[0]",
        diagnostics=diagnostics,
    )

    assert len(diagnostics) == 1
    assert diagnostics[0].code == "COMPILER_FIELD_UNDEFINED"
    assert diagnostics[0].path == "validation.rules[0].applies_to.field"


def test_check_validation_field_semantics_reports_type_mismatches() -> None:
    """Validation rules detect mismatch between field type and module contract."""

    diagnostics: list[CompileDiagItem] = []

    check_validation_field_semantics(
        applies_field="price",
        known_fields={"price"},
        field_final_types={"price": "decimal"},
        expected_value_type="string",
        module_id="enum",
        rule_path="validation.rules[1]",
        diagnostics=diagnostics,
    )

    assert len(diagnostics) == 1
    assert diagnostics[0].code == "SCHEMA_TYPE_VALIDATION_MISMATCH"
    assert diagnostics[0].path == "validation.rules[1].module_id"


def test_update_required_by_profile_sources_uses_defaults_and_explicit_filters() -> (
    None
):
    """required_if_profile rules record canonical and explicit profile sources."""

    required_by_profile_sources: dict[str, dict[str, str]] = {}

    update_required_by_profile_sources(
        applies_field="title",
        module_id="required_if_profile",
        rule_path="validation.rules[2]",
        required_by_profile_sources=required_by_profile_sources,
        artifact_profile_filters=None,
    )

    assert required_by_profile_sources["title"] == {
        profile: "validation.rules[2].module_id"
        for profile in CANONICAL_ARTIFACT_PROFILES
    }

    update_required_by_profile_sources(
        applies_field="title",
        module_id="required_if_profile",
        rule_path="validation.rules[3]",
        required_by_profile_sources=required_by_profile_sources,
        artifact_profile_filters=["catalog_snapshot"],
    )

    assert required_by_profile_sources["title"]["catalog_snapshot"] == (
        "validation.rules[3].module_id"
    )


def test_update_required_by_profile_sources_ignores_irrelevant_rules() -> None:
    """Rules without field scope or profile-aware modules do not mutate outputs."""

    required_by_profile_sources: dict[str, dict[str, str]] = {}

    update_required_by_profile_sources(
        applies_field=None,
        module_id="required_if_profile",
        rule_path="validation.rules[0]",
        required_by_profile_sources=required_by_profile_sources,
        artifact_profile_filters=None,
    )
    update_required_by_profile_sources(
        applies_field="title",
        module_id="required",
        rule_path="validation.rules[1]",
        required_by_profile_sources=required_by_profile_sources,
        artifact_profile_filters=None,
    )

    assert required_by_profile_sources == {}
