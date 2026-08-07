"""Entrypoint tests for `pfp_core.engine.compiler_checks`."""

from typing import List

from pfp_core.engine.compiler_checks import check_presence_required_contradictions
from pfp_core.engine.plan_types import CompileDiagItem, FieldPresencePlan


def test_check_presence_required_contradictions_skips_missing_field_presence() -> None:
    """Ensure contradiction check skips fields absent in field_presence mapping."""

    diagnostics: List[CompileDiagItem] = []
    check_presence_required_contradictions(
        field_presence={},
        required_by_profile_sources={
            "id": {"catalog_snapshot": "validation.rules[0].module_id"}
        },
        diagnostics=diagnostics,
    )

    assert diagnostics == []


def test_check_presence_required_contradictions_reports_omit_missing() -> None:
    diagnostics: List[CompileDiagItem] = []
    check_presence_required_contradictions(
        field_presence={"id": FieldPresencePlan(behavior="omit_missing")},
        required_by_profile_sources={
            "id": {"catalog_snapshot": "validation.rules[0].module_id"}
        },
        diagnostics=diagnostics,
    )

    assert len(diagnostics) == 1
    assert diagnostics[0].code == "COMPILER_PRESENCE_REQUIRED_CONTRADICTION"
