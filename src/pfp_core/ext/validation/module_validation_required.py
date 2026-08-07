"""Validation module: required (presence check)."""

from __future__ import annotations

from typing import Any, Mapping, Optional

from pfp_core.ext.ext_types import (
    MISSING,
    ParamSpec,
    TypeSpec,
    ValidationModuleSpec,
    ValidationResult,
)


def _required(
    value: Any,
    config: Mapping[str, Any],
    record: Optional[Mapping[str, Any]] = None,
    artifact_profile: Optional[str] = None,
) -> ValidationResult:
    """Validate that a value is present and not null.

    Args:
        value: Input value.
        config: Module config (unused).

    Returns:
        `ValidationResult(ok=True)` for present values, otherwise `ok=False`.
    """
    _ = (config, record, artifact_profile)
    if value is MISSING:
        return ValidationResult(ok=False, details="required: value is missing")
    if value is None:
        return ValidationResult(ok=False, details="required: value is null")
    return ValidationResult(ok=True)


def get_spec() -> ValidationModuleSpec:
    """Return the `ValidationModuleSpec` for the `required` module.

    Returns:
        Registered validation module specification.
    """
    return ValidationModuleSpec(
        module_id="required",
        value_type=TypeSpec("any", nullable=True, optional=True),
        config_spec=ParamSpec(),
        call=_required,
    )
