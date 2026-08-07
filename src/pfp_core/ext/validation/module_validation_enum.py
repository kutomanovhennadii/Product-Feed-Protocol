"""Validation module: enum (membership check for string values)."""

from __future__ import annotations

from typing import Any, List, Mapping, Optional, cast

from pfp_core.ext.ext_types import (
    MISSING,
    ParamFieldSpec,
    ParamSpec,
    TypeSpec,
    ValidationModuleSpec,
    ValidationResult,
)


def _enum_check(
    value: Any,
    config: Mapping[str, Any],
    record: Optional[Mapping[str, Any]] = None,
    artifact_profile: Optional[str] = None,
) -> ValidationResult:
    """Validate that a string value is within the allowed set.

    Args:
        value: Input value.
        config: Module config. Requires `allowed` as a non-empty list of strings.

    Returns:
        `ok=True` for `MISSING`/`None`. For non-string values, this module is
        typing-first and returns `ok=True` (type checking is handled separately).
        For string values, returns `ok=True` only if the value is in `allowed`.

    Raises:
        ValueError: If config is missing/invalid.
    """
    _ = (record, artifact_profile)

    allowed = config.get("allowed")
    if (
        not isinstance(allowed, list)
        or not allowed
        or any(not isinstance(item, str) for item in allowed)
    ):
        raise ValueError(
            "enum module requires non-empty list of strings config 'allowed'."
        )

    allowed_values = cast(List[str], allowed)

    if value is MISSING or value is None:
        return ValidationResult(ok=True)
    if not isinstance(value, str):
        return ValidationResult(ok=True)
    if value in allowed_values:
        return ValidationResult(ok=True)
    return ValidationResult(ok=False, details="enum mismatch: value not in allowed set")


def get_spec() -> ValidationModuleSpec:
    """Return the `ValidationModuleSpec` for the `enum` module.

    Returns:
        Registered validation module specification.
    """
    return ValidationModuleSpec(
        module_id="enum",
        value_type=TypeSpec("string", nullable=True, optional=True),
        config_spec=ParamSpec(
            fields=(
                ParamFieldSpec(
                    name="allowed",
                    type_spec=TypeSpec("array[string]", nullable=False, optional=False),
                    required=True,
                    constraints={"min_items": 1},
                ),
            ),
            allow_extra=False,
        ),
        call=_enum_check,
    )
