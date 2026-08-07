"""Entrypoint tests for `pfp_core.engine.validation_compiler.compile_validation`."""

from typing import List, Mapping, Optional, Tuple, cast

import pytest

from pfp_core.engine.plan_types import CompileDiagItem
from pfp_core.engine.validation_compiler import compile_validation
from pfp_core.ext import ExtCatalog, build_builtin_catalog
from pfp_core.ext.ext_types import (
    ParamSpec,
    TypeSpec,
    ValidationModuleSpec,
    ValidationResult,
)


def _diag_codes(items: Tuple[CompileDiagItem, ...]) -> List[str]:
    """Return diagnostic codes list."""

    return [item.code for item in items]


def test_compile_validation_missing_and_invalid_rules_shapes() -> None:
    """Ensure validation section shape errors are reported deterministically."""

    diagnostics_missing: List[CompileDiagItem] = []
    plan_missing, links_missing = compile_validation(
        schema_doc={},
        known_fields=set(),
        field_final_types={},
        catalog=build_builtin_catalog(),
        diagnostics=diagnostics_missing,
    )
    assert plan_missing.rules == ()
    assert links_missing == {}
    assert _diag_codes(tuple(diagnostics_missing)) == ["COMPILER_VALIDATION_INVALID"]

    diagnostics_rules: List[CompileDiagItem] = []
    plan_rules, links_rules = compile_validation(
        schema_doc={"validation": {"rules": "bad"}},
        known_fields=set(),
        field_final_types={},
        catalog=build_builtin_catalog(),
        diagnostics=diagnostics_rules,
    )
    assert plan_rules.rules == ()
    assert links_rules == {}
    assert _diag_codes(tuple(diagnostics_rules)) == ["COMPILER_VALIDATION_INVALID"]


def test_compile_validation_invalid_rule_payloads() -> None:
    """Ensure malformed rule objects are rejected by entrypoint parser."""

    diagnostics: List[CompileDiagItem] = []
    plan, links = compile_validation(
        schema_doc={
            "validation": {
                "rules": [
                    "bad",
                    {"module_id": ""},
                ]
            }
        },
        known_fields={"known"},
        field_final_types={"known": "string"},
        catalog=build_builtin_catalog(),
        diagnostics=diagnostics,
    )

    codes = _diag_codes(tuple(diagnostics))
    assert "SCHEMA_LINK_MODULE_INVALID" in codes
    assert plan.rules == ()
    assert links == {}


def test_compile_validation_invalid_config_uses_validation_code() -> None:
    """Ensure non-object validation rule config emits COMPILER_VALIDATION_INVALID."""

    diagnostics: List[CompileDiagItem] = []
    plan, _ = compile_validation(
        schema_doc={
            "validation": {
                "rules": [
                    {
                        "module_id": "required",
                        "applies_to": {"field": "known"},
                        "config": "bad",
                    }
                ]
            }
        },
        known_fields={"known"},
        field_final_types={"known": "string"},
        catalog=build_builtin_catalog(),
        diagnostics=diagnostics,
    )

    assert len(plan.rules) == 1
    assert any(
        item.code == "COMPILER_VALIDATION_INVALID"
        and item.path == "validation.rules[0].config"
        for item in diagnostics
    )


def test_compile_validation_required_if_profile_links_default_profiles() -> None:
    """Ensure required_if_profile populates profile links with canonical defaults."""

    diagnostics: List[CompileDiagItem] = []
    catalog = ExtCatalog()

    def _ok_module_call(
        value: object,
        config: Mapping[str, object],
        record: Optional[Mapping[str, object]] = None,
        artifact_profile: Optional[str] = None,
    ) -> ValidationResult:
        _ = (value, config, record, artifact_profile)
        return ValidationResult(ok=True)

    catalog.register_validation_module(
        ValidationModuleSpec(
            module_id="required_if_profile",
            value_type=TypeSpec(type_id="string"),
            config_spec=ParamSpec(),
            call=_ok_module_call,
        )
    )
    plan, links = compile_validation(
        schema_doc={
            "validation": {
                "rules": [
                    {
                        "module_id": "required_if_profile",
                        "applies_to": {"field": "id"},
                    }
                ]
            }
        },
        known_fields={"id"},
        field_final_types={"id": "string"},
        catalog=catalog,
        diagnostics=diagnostics,
    )

    assert diagnostics == []
    assert len(plan.rules) == 1
    assert plan.rules[0].module_id == "required_if_profile"
    assert links == {
        "id": {
            "catalog_snapshot": "validation.rules[0].module_id",
            "catalog_delta": "validation.rules[0].module_id",
            "inventory_price_delta": "validation.rules[0].module_id",
        }
    }


def test_compile_validation_required_by_profile_sources_are_immutable() -> None:
    """Ensure returned required-by-profile links mapping is immutable at both levels."""

    diagnostics: List[CompileDiagItem] = []
    catalog = ExtCatalog()

    def _ok_module_call(
        value: object,
        config: Mapping[str, object],
        record: Optional[Mapping[str, object]] = None,
        artifact_profile: Optional[str] = None,
    ) -> ValidationResult:
        _ = (value, config, record, artifact_profile)
        return ValidationResult(ok=True)

    catalog.register_validation_module(
        ValidationModuleSpec(
            module_id="required_if_profile",
            value_type=TypeSpec(type_id="string"),
            config_spec=ParamSpec(),
            call=_ok_module_call,
        )
    )
    _, links = compile_validation(
        schema_doc={
            "validation": {
                "rules": [
                    {
                        "module_id": "required_if_profile",
                        "applies_to": {"field": "id"},
                        "config": {"artifact_profiles": ["catalog_snapshot"]},
                    }
                ]
            }
        },
        known_fields={"id"},
        field_final_types={"id": "string"},
        catalog=catalog,
        diagnostics=diagnostics,
    )

    assert diagnostics == []

    from typing import Any

    with pytest.raises(TypeError):
        cast(Any, links)["x"] = {"catalog_snapshot": "validation.rules[0].module_id"}

    with pytest.raises(TypeError):
        cast(Any, links["id"])["catalog_delta"] = "validation.rules[0].module_id"


def test_compile_validation_reads_profile_filters_from_config() -> None:
    diagnostics: List[CompileDiagItem] = []
    plan, _ = compile_validation(
        schema_doc={
            "validation": {
                "rules": [
                    {
                        "module_id": "required_if_profile",
                        "applies_to": {"field": "id"},
                        "config": {
                            "artifact_profiles": ["catalog_delta", "catalog_snapshot"]
                        },
                    }
                ]
            }
        },
        known_fields={"id"},
        field_final_types={"id": "string"},
        catalog=build_builtin_catalog(),
        diagnostics=diagnostics,
    )

    assert diagnostics == []
    assert plan.rules[0].module_id == "required_if_profile"


def test_compile_validation_skips_rule_when_module_linking_fails() -> None:
    diagnostics: List[CompileDiagItem] = []
    plan, links = compile_validation(
        schema_doc={"validation": {"rules": [{"module_id": "not_allowlisted"}]}},
        known_fields={"id"},
        field_final_types={"id": "string"},
        catalog=build_builtin_catalog(),
        diagnostics=diagnostics,
    )

    assert plan.rules == ()
    assert links == {}
    assert any(item.code == "SCHEMA_LINK_MODULE_NOT_ALLOWED" for item in diagnostics)
