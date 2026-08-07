"""Validation module: type (runtime type check)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Mapping, Optional, Tuple, cast, get_args

from pfp_core.ext.ext_types import (
    MISSING,
    ParamFieldSpec,
    ParamSpec,
    TypeId,
    TypeSpec,
    ValidationModuleSpec,
    ValidationResult,
)

_ALLOWED_TYPE_IDS: Tuple[str, ...] = tuple(cast(Tuple[str, ...], get_args(TypeId)))


def _matches_type(value: Any, type_id: str) -> bool:
    """Return whether value matches a schema type id.

    Args:
        value: Value to validate.
        type_id: Schema type identifier.

    Returns:
        True when value matches type contract, otherwise False.
    """
    if type_id == "any":
        return True
    if type_id == "string":
        return isinstance(value, str)
    if type_id == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    if type_id == "decimal":
        return isinstance(value, Decimal)
    if type_id == "bool":
        return isinstance(value, bool)
    if type_id == "date":
        return isinstance(value, date) and not isinstance(value, datetime)
    if type_id == "datetime":
        return isinstance(value, datetime)
    if type_id == "array[string]":
        return isinstance(value, list) and all(isinstance(item, str) for item in value)
    if type_id == "object":
        return isinstance(value, Mapping)
    return False


def _type_check(
    value: Any,
    config: Mapping[str, Any],
    record: Optional[Mapping[str, Any]] = None,
    artifact_profile: Optional[str] = None,
) -> ValidationResult:
    """Validate the runtime type of `value` according to `type_id`.

    Args:
        value: Input value.
        config: Module config. Requires `type_id`.

    Returns:
        `ok=True` for `MISSING`/`None` or matching types; `ok=False` otherwise.

    Raises:
        ValueError: If config is missing/invalid.
    """
    _ = (record, artifact_profile)

    type_id = config.get("type_id")
    if not isinstance(type_id, str) or type_id not in _ALLOWED_TYPE_IDS:
        raise ValueError("type module requires valid 'type_id' config.")

    if value is MISSING or value is None:
        return ValidationResult(ok=True)

    if _matches_type(value, type_id):
        return ValidationResult(ok=True)
    return ValidationResult(ok=False, details=f"type mismatch: expected {type_id}")


def get_spec() -> ValidationModuleSpec:
    """Return the `ValidationModuleSpec` for the `type` module.

    Returns:
        Registered validation module specification.
    """
    return ValidationModuleSpec(
        module_id="type",
        value_type=TypeSpec("any", nullable=True, optional=True),
        config_spec=ParamSpec(
            fields=(
                ParamFieldSpec(
                    name="type_id",
                    type_spec=TypeSpec("string", nullable=False, optional=False),
                    required=True,
                ),
            ),
            allow_extra=False,
        ),
        call=_type_check,
    )
