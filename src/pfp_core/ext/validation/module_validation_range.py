"""Validation module: range (numeric bounds check)."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Optional

from pfp_core.ext.ext_types import (
    MISSING,
    ParamFieldSpec,
    ParamSpec,
    TypeSpec,
    ValidationModuleSpec,
    ValidationResult,
)


def _to_decimal(value: Any) -> Decimal:
    """Convert an input into `Decimal` for numeric comparisons.

    Args:
        value: Value to convert into decimal.

    Returns:
        Converted decimal representation.

    Raises:
        ValueError: If the value is not numeric.
    """
    if isinstance(value, bool):
        raise ValueError("bool is not allowed for numeric range checks")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("value is not numeric") from exc


def _range_check(
    value: Any,
    config: Mapping[str, Any],
    record: Optional[Mapping[str, Any]] = None,
    artifact_profile: Optional[str] = None,
) -> ValidationResult:
    """Validate that a numeric value is within configured bounds.

    Args:
        value: Input value.
        config: Module config. Requires at least one of `min` or `max`.

    Returns:
        `ok=True` for `MISSING`/`None`. For non-numeric values, this module is
        typing-first and returns `ok=True` (type checking is handled separately).
        For numeric values, returns `ok=False` if outside the configured range.

    Raises:
        ValueError: If config is missing/invalid.
    """
    _ = (record, artifact_profile)

    min_raw = config.get("min")
    max_raw = config.get("max")

    if min_raw is None and max_raw is None:
        raise ValueError("range module requires at least one of 'min' or 'max'.")

    min_value = _to_decimal(min_raw) if min_raw is not None else None
    max_value = _to_decimal(max_raw) if max_raw is not None else None

    if min_value is not None and max_value is not None and min_value > max_value:
        raise ValueError("range module config is invalid: min > max")

    if value is MISSING or value is None:
        return ValidationResult(ok=True)

    try:
        current = _to_decimal(value)
    except ValueError:
        return ValidationResult(ok=True)
    if min_value is not None and current < min_value:
        return ValidationResult(ok=False, details="range mismatch: value below min")
    if max_value is not None and current > max_value:
        return ValidationResult(ok=False, details="range mismatch: value above max")
    return ValidationResult(ok=True)


def get_spec() -> ValidationModuleSpec:
    """Return the `ValidationModuleSpec` for the `range` module.

    Returns:
        Registered validation module specification.
    """
    return ValidationModuleSpec(
        module_id="range",
        value_type=TypeSpec("any", nullable=True, optional=True),
        config_spec=ParamSpec(
            fields=(
                ParamFieldSpec(
                    name="min",
                    type_spec=TypeSpec("any", nullable=True, optional=True),
                    required=False,
                ),
                ParamFieldSpec(
                    name="max",
                    type_spec=TypeSpec("any", nullable=True, optional=True),
                    required=False,
                ),
            ),
            allow_extra=False,
        ),
        call=_range_check,
    )
