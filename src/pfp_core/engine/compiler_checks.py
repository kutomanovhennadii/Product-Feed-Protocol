"""Cross-checks for compiled plans consistency."""

from __future__ import annotations

from typing import List, Mapping

from pfp_core.engine.compile_support.diagnostics import add_error
from pfp_core.engine.plan_types import CompileDiagItem, FieldPresencePlan


def check_presence_required_contradictions(
    *,
    field_presence: Mapping[str, FieldPresencePlan],
    required_by_profile_sources: Mapping[str, Mapping[str, str]],
    diagnostics: List[CompileDiagItem],
) -> None:
    """Validate contradictions between required-by-profile and omit semantics.

    Args:
        field_presence: Compiled per-field presence rules.
        required_by_profile_sources: Required-by-profile rule source paths.
        diagnostics: Mutable diagnostics accumulator.

    Returns:
        None.
    """

    for field_id in sorted(required_by_profile_sources.keys()):
        presence = field_presence.get(field_id)
        if presence is None:
            continue

        profile_sources = required_by_profile_sources[field_id]
        for profile in sorted(profile_sources.keys()):
            effective_presence = presence.behavior
            path = "mapping.fields." + field_id + ".presence.behavior"
            if effective_presence == "omit_missing":
                add_error(
                    diagnostics,
                    code="COMPILER_PRESENCE_REQUIRED_CONTRADICTION",
                    path=path,
                    message=(
                        "Field '"
                        + field_id
                        + "' is required in profile '"
                        + profile
                        + "' by "
                        + profile_sources[profile]
                        + ", but presence allows omit_missing."
                    ),
                )
