"""Validation compile helpers for allowlist and catalog linking."""

from __future__ import annotations

from typing import List, Optional, Tuple

from pfp_core.engine.catalog_resolver import try_get_validation_module
from pfp_core.engine.compile_support.diagnostics import add_error
from pfp_core.engine.compile_support.types import to_plan_type_id
from pfp_core.engine.plan_types import CompileDiagItem, TypeId
from pfp_core.ext.ext_catalog import ExtCatalog
from pfp_core.schema.schema_constraints import VALIDATION_MODULE_ALLOWLIST


def link_validation_module(
    *,
    catalog: ExtCatalog,
    module_id: str,
    rule_path: str,
    diagnostics: List[CompileDiagItem],
) -> Tuple[bool, Optional[TypeId]]:
    """Validate allowlist, resolve module spec and infer expected value type.

    Args:
        catalog: Ext-modules catalog used for module resolution.
        module_id: Validation module id.
        rule_path: Absolute schema path to current rule.
        diagnostics: Mutable diagnostics accumulator.

    Returns:
        Tuple of success flag and expected value type for the module.
    """

    if module_id not in VALIDATION_MODULE_ALLOWLIST:
        add_error(
            diagnostics,
            code="SCHEMA_LINK_MODULE_NOT_ALLOWED",
            path=rule_path + ".module_id",
            message=("Validation module '" + module_id + "' is not in allowlist."),
        )
        return False, None

    module_spec = try_get_validation_module(
        catalog=catalog,
        module_id=module_id,
        path=rule_path + ".module_id",
        diagnostics=diagnostics,
    )
    if module_spec is None:
        return False, None

    raw_value_type_id = module_spec.value_type.type_id
    expected_value_type = to_plan_type_id(raw_value_type_id)
    if expected_value_type is None and raw_value_type_id != "any":
        add_error(
            diagnostics,
            code="SCHEMA_TYPE_INVALID_TYPE_ID",
            path=rule_path + ".module_id",
            message=(
                "Validation module value_type is not a supported TypeId: "
                + str(raw_value_type_id)
            ),
        )
        return False, None

    return True, expected_value_type
