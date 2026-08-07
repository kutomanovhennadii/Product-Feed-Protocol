"""Explicit validation-modules contract registry.

The contract is a mapping from ``module_id`` to lazy ``ValidationModuleSpec``
builders. It defines the allowed set of validation modules.
"""

from typing import Callable, Dict, List

from pfp_core.ext.ext_types import ValidationModuleSpec
from pfp_core.ext.validation.module_validation_enum import get_spec as enum_check_spec
from pfp_core.ext.validation.module_validation_range import get_spec as range_check_spec
from pfp_core.ext.validation.module_validation_required import get_spec as required_spec
from pfp_core.ext.validation.module_validation_required_if_profile import (
    get_spec as required_if_profile_spec,
)
from pfp_core.ext.validation.module_validation_type import get_spec as type_check_spec

VALIDATION_MODULE_REGISTRY: Dict[str, Callable[[], ValidationModuleSpec]] = {
    "required": required_spec,
    "required_if_profile": required_if_profile_spec,
    "type": type_check_spec,
    "enum": enum_check_spec,
    "range": range_check_spec,
}


def get_validation_module_spec(module_id: str) -> ValidationModuleSpec:
    """Return validation module spec by contract module id."""
    builder = VALIDATION_MODULE_REGISTRY.get(module_id)
    if builder is None:
        raise ValueError(f"Unknown validation module_id: {module_id}")
    return builder()


def list_validation_module_ids() -> List[str]:
    """Return sorted validation module ids declared by the contract."""
    return sorted(VALIDATION_MODULE_REGISTRY.keys())


def _validate_validation_module_registry() -> None:
    """Validate module-id mapping integrity between keys and built specs."""
    for module_id, builder in VALIDATION_MODULE_REGISTRY.items():
        spec = builder()
        if not spec.module_id:
            raise ValueError(
                f"Validation registry mismatch: key={module_id!r}, spec.module_id is empty"
            )
        if spec.module_id != module_id:
            raise ValueError(
                f"Validation registry mismatch: key={module_id!r}, spec.module_id={spec.module_id!r}"
            )
        if not callable(spec.call):
            raise ValueError(
                f"Validation registry mismatch: key={module_id!r}, spec.call is not callable"
            )


_validate_validation_module_registry()
