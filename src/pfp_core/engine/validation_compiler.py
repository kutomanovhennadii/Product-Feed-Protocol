"""Compilation of schema validation section into `ValidationPlan`."""

from __future__ import annotations

from types import MappingProxyType
from typing import Dict, Iterable, List, Mapping, Optional, Set, Tuple, cast

from pfp_core.engine.compile_support.diagnostics import add_error
from pfp_core.engine.compile_support.shapes import as_mapping
from pfp_core.engine.plan_types import (
    CompileDiagItem,
    TypeId,
    ValidationPlan,
    ValidationRulePlan,
)
from pfp_core.engine.validation import linking as _validation_linking
from pfp_core.engine.validation import rule_order as _validation_rule_order
from pfp_core.engine.validation import semantics as _validation_semantics
from pfp_core.ext.ext_catalog import ExtCatalog
from pfp_core.schema.schema_types import SchemaDoc


def compile_validation(
    *,
    schema_doc: SchemaDoc,
    known_fields: Set[str],
    field_final_types: Mapping[str, Optional[TypeId]],
    catalog: ExtCatalog,
    diagnostics: List[CompileDiagItem],
) -> Tuple[ValidationPlan, Mapping[str, Mapping[str, str]]]:
    """Compile `validation.rules` section into `ValidationPlan`.

    Args:
        schema_doc: Source schema document.
        known_fields: Known mapping fields.
        field_final_types: Final inferred field types from mapping plan.
        catalog: Ext-modules catalog used for module resolution.
        diagnostics: Mutable diagnostics accumulator.

    Returns:
        Validation plan and required-by-profile rule sources per field.
    """
    empty_required_sources = cast(
        Mapping[str, Mapping[str, str]],
        MappingProxyType({}),
    )

    validation_obj = as_mapping(schema_doc.get("validation"))
    if validation_obj is None:
        add_error(
            diagnostics,
            code="COMPILER_VALIDATION_INVALID",
            path="validation",
            message="validation must be an object.",
        )
        return ValidationPlan(rules=()), empty_required_sources

    rules_obj = validation_obj.get("rules", [])
    if not isinstance(rules_obj, list):
        add_error(
            diagnostics,
            code="COMPILER_VALIDATION_INVALID",
            path="validation.rules",
            message="validation.rules must be a list.",
        )
        return ValidationPlan(rules=()), empty_required_sources

    rules_plan: List[ValidationRulePlan] = []
    required_by_profile_sources: Dict[str, Dict[str, str]] = {}

    for index, rule_obj in _validation_rule_order.ordered_rules(
        cast(List[object], rules_obj)
    ):
        rule_path = "validation.rules[" + str(index) + "]"
        rule = as_mapping(rule_obj)
        if rule is None:
            add_error(
                diagnostics,
                code="COMPILER_VALIDATION_INVALID",
                path=rule_path,
                message=rule_path + " must be an object.",
            )
            continue

        module_obj = rule.get("module_id")
        module_id = module_obj if isinstance(module_obj, str) else ""
        if not module_id:
            add_error(
                diagnostics,
                code="SCHEMA_LINK_MODULE_INVALID",
                path=rule_path + ".module_id",
                message="validation rule module_id must be a non-empty string.",
            )
            continue

        linked, expected_value_type = _validation_linking.link_validation_module(
            catalog=catalog,
            module_id=module_id,
            rule_path=rule_path,
            diagnostics=diagnostics,
        )
        if not linked:
            continue

        applies_to_obj = as_mapping(rule.get("applies_to", {})) or {}
        applies_field_obj = applies_to_obj.get("field")
        applies_field = (
            applies_field_obj if isinstance(applies_field_obj, str) else None
        )

        _validation_semantics.check_validation_field_semantics(
            applies_field=applies_field,
            known_fields=known_fields,
            field_final_types=field_final_types,
            expected_value_type=expected_value_type,
            module_id=module_id,
            rule_path=rule_path,
            diagnostics=diagnostics,
        )

        config_obj = rule.get("config", {})
        config_map = as_mapping(config_obj)
        if config_map is None:
            add_error(
                diagnostics,
                code="COMPILER_VALIDATION_INVALID",
                path=rule_path + ".config",
                message=rule_path + ".config must be an object.",
            )
            config_map = {}

        artifact_profile_filters = _read_rule_artifact_profile_filters(
            module_id=module_id,
            config=cast(Mapping[str, object], config_map),
        )

        _validation_semantics.update_required_by_profile_sources(
            applies_field=applies_field,
            module_id=module_id,
            rule_path=rule_path,
            required_by_profile_sources=required_by_profile_sources,
            artifact_profile_filters=artifact_profile_filters,
        )

        on_fail_obj = as_mapping(rule.get("on_fail", {})) or {}
        on_fail_code = on_fail_obj.get("code")
        on_fail_message = on_fail_obj.get("message")
        severity_hint = on_fail_obj.get("severity_hint")
        rule_id_obj = rule.get("id")

        rules_plan.append(
            ValidationRulePlan(
                rule_id=rule_id_obj if isinstance(rule_id_obj, str) else None,
                module_id=module_id,
                applies_to_field=applies_field,
                config=cast(
                    Mapping[str, object],
                    MappingProxyType(dict(cast(Mapping[str, object], config_map))),
                ),
                on_fail_code=on_fail_code if isinstance(on_fail_code, str) else None,
                on_fail_message=(
                    on_fail_message if isinstance(on_fail_message, str) else None
                ),
                severity_hint=(
                    severity_hint if isinstance(severity_hint, str) else None
                ),
                expected_value_type=expected_value_type,
            )
        )

    required_by_profile_sources_frozen: Dict[str, Mapping[str, str]] = {}
    for field_id, profile_sources in required_by_profile_sources.items():
        required_by_profile_sources_frozen[field_id] = cast(
            Mapping[str, str],
            MappingProxyType(dict(profile_sources)),
        )

    return ValidationPlan(rules=tuple(rules_plan)), cast(
        Mapping[str, Mapping[str, str]],
        MappingProxyType(dict(required_by_profile_sources_frozen)),
    )


def _read_rule_artifact_profile_filters(
    *,
    module_id: str,
    config: Mapping[str, object],
) -> Optional[Tuple[str, ...]]:
    if module_id == "required_if_profile":
        return _extract_profile_filters_from_config(config)
    return None


def _extract_profile_filters_from_config(
    config: Mapping[str, object],
) -> Optional[Tuple[str, ...]]:
    if "artifact_profiles" in config:
        profiles_obj = config.get("artifact_profiles")
        if isinstance(profiles_obj, Iterable) and not isinstance(
            profiles_obj, (str, bytes)
        ):
            normalized = []
            for item in profiles_obj:
                if isinstance(item, str) and item.strip():
                    normalized.append(item.strip().lower())
            if normalized:
                return tuple(sorted(set(normalized)))
    profile_obj = config.get("artifact_profile")
    if isinstance(profile_obj, str) and profile_obj.strip():
        return (profile_obj.strip().lower(),)
    return None
