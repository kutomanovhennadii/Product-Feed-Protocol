"""Validation module: required_if_profile."""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Optional, Set, cast

from pfp_core.ext.ext_types import (
    MISSING,
    ParamFieldSpec,
    ParamSpec,
    TypeSpec,
    ValidationModuleSpec,
    ValidationResult,
)


def _normalize_profiles(config: Mapping[str, Any]) -> Optional[Set[str]]:
    """Normalize optional artifact profile filter from module config."""

    profiles_obj = config.get("artifact_profiles")
    if profiles_obj is None:
        profile_obj = config.get("artifact_profile")
        if profile_obj is None:
            return None
        if isinstance(profile_obj, str) and profile_obj.strip():
            return {profile_obj.strip().lower()}
        return None

    if not isinstance(profiles_obj, Iterable) or isinstance(profiles_obj, (str, bytes)):
        return None

    normalized: Set[str] = set()
    for item in cast(Iterable[Any], profiles_obj):
        if isinstance(item, str) and item.strip():
            normalized.add(item.strip().lower())
    return normalized or None


def _required_if_profile(
    value: Any,
    config: Mapping[str, Any],
    record: Optional[Mapping[str, Any]] = None,
    artifact_profile: Optional[str] = None,
) -> ValidationResult:
    """Require value presence when artifact profile matches configured filters."""

    _ = record

    active_profiles = _normalize_profiles(config)
    current_profile = (
        artifact_profile.strip().lower() if isinstance(artifact_profile, str) else ""
    )

    if active_profiles is not None and current_profile not in active_profiles:
        return ValidationResult(ok=True)

    if value is MISSING:
        return ValidationResult(
            ok=False, details="required_if_profile: value is missing"
        )
    if value is None:
        return ValidationResult(ok=False, details="required_if_profile: value is null")
    return ValidationResult(ok=True)


def get_spec() -> ValidationModuleSpec:
    """Return the ValidationModuleSpec for the required_if_profile module."""

    return ValidationModuleSpec(
        module_id="required_if_profile",
        value_type=TypeSpec("any", nullable=True, optional=True),
        config_spec=ParamSpec(
            fields=(
                ParamFieldSpec(
                    name="artifact_profile",
                    type_spec=TypeSpec("string", nullable=False, optional=False),
                    required=False,
                ),
                ParamFieldSpec(
                    name="artifact_profiles",
                    type_spec=TypeSpec("array[string]", nullable=False, optional=False),
                    required=False,
                ),
            ),
            allow_extra=False,
        ),
        call=_required_if_profile,
    )
