"""Validation compile helpers for field semantics and required-by-profile mapping."""

from __future__ import annotations

from typing import Dict, List, Mapping, Optional, Sequence, Set

from pfp_core.engine.compile_support.diagnostics import add_error
from pfp_core.engine.compile_support.types import is_validation_type_mismatch
from pfp_core.engine.plan_types import CompileDiagItem, TypeId

REQUIRED_BY_PROFILE_MODULE_IDS = frozenset(("required_if_profile",))
CANONICAL_ARTIFACT_PROFILES = (
    "catalog_snapshot",
    "catalog_delta",
    "inventory_price_delta",
)


def check_validation_field_semantics(
    *,
    applies_field: Optional[str],
    known_fields: Set[str],
    field_final_types: Mapping[str, Optional[TypeId]],
    expected_value_type: Optional[TypeId],
    module_id: str,
    rule_path: str,
    diagnostics: List[CompileDiagItem],
) -> None:
    """Validate known-field and field-type compatibility semantics.

    Args:
        applies_field: Optional field scope.
        known_fields: Known mapping fields.
        field_final_types: Final inferred field types.
        expected_value_type: Validation module expected value type.
        module_id: Validation module id.
        rule_path: Absolute schema path to current rule.
        diagnostics: Mutable diagnostics accumulator.

    Returns:
        None.
    """

    if applies_field is not None and applies_field not in known_fields:
        add_error(
            diagnostics,
            code="COMPILER_FIELD_UNDEFINED",
            path=rule_path + ".applies_to.field",
            message="Unknown field in validation rule: '" + applies_field + "'.",
        )

    if (
        applies_field is not None
        and applies_field in field_final_types
        and expected_value_type is not None
    ):
        field_type = field_final_types[applies_field]
        if is_validation_type_mismatch(
            field_type=field_type,
            expected_value_type=expected_value_type,
        ):
            add_error(
                diagnostics,
                code="SCHEMA_TYPE_VALIDATION_MISMATCH",
                path=rule_path + ".module_id",
                message=(
                    "Validation module '"
                    + module_id
                    + "' expects '"
                    + str(expected_value_type)
                    + "', but field '"
                    + applies_field
                    + "' has '"
                    + str(field_type)
                    + "'."
                ),
            )


def update_required_by_profile_sources(
    *,
    applies_field: Optional[str],
    module_id: str,
    rule_path: str,
    required_by_profile_sources: Dict[str, Dict[str, str]],
    artifact_profile_filters: Optional[Sequence[str]],
) -> None:
    """Update required-by-profile source map for profile-required rules.

    Args:
        applies_field: Optional field scope.
        module_id: Validation module id.
        rule_path: Absolute schema path to current rule.
        required_by_profile_sources: Mutable output map.
        artifact_profile_filters: Optional profile filters declared by a rule.

    Returns:
        None.
    """

    if applies_field is None or module_id not in REQUIRED_BY_PROFILE_MODULE_IDS:
        return

    profile_sources = required_by_profile_sources.setdefault(applies_field, {})
    effective_profiles = artifact_profile_filters or CANONICAL_ARTIFACT_PROFILES
    for profile in effective_profiles:
        profile_sources[profile] = rule_path + ".module_id"
