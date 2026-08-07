"""Mapping runtime helper for DELETE tombstone projection."""

from __future__ import annotations

from typing import Mapping, Optional, Tuple

from pfp_core.engine.mapping.runtime_values import _extract_by_source_path
from pfp_core.engine.plan_types import MappingPlan
from pfp_core.ext.ext_types import MISSING


def _should_project_delete_tombstone(
    *,
    plan: MappingPlan,
    input_record: Mapping[str, object],
    artifact_profile: str,
) -> bool:
    """Decide whether DELETE record must be projected as tombstone.

    Args:
        plan: Compiled mapping plan.
        input_record: Input record for current item.
        artifact_profile: Product profile for current compiled schema.

    Returns:
        True when non-id fields should be omitted for this record.
    """

    if not plan.delete_tombstone_enabled:
        return False
    value = _extract_by_source_path(input_record, plan.delete_tombstone_flag_path)
    if value is MISSING:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes", "y")
    return False


def detect_delete_unsupported(
    *,
    plan: MappingPlan,
    input_record: Mapping[str, object],
    artifact_profile: str,
) -> Optional[Tuple[str, str, str]]:
    """Detect delete intent that is unsupported for a profile.

    Returns:
        Tuple(code, path, message) when unsupported delete intent is present;
        otherwise None.
    """

    value = _extract_by_source_path(input_record, plan.delete_tombstone_flag_path)
    if not _is_delete_intent(value):
        return None

    if plan.delete_tombstone_enabled:
        return None

    return (
        "CONTRACT.DELETE_UNSUPPORTED",
        "build:contract",
        "Delete tombstone is unsupported for artifact_profile {0}.".format(
            artifact_profile
        ),
    )


def _is_delete_intent(value: object) -> bool:
    if value is MISSING:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes", "y")
    return False
