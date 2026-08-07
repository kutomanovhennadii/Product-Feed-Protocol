"""Catalog resolution helpers with deterministic link diagnostics."""

from __future__ import annotations

from typing import Any, List, Optional

from pfp_core.engine.compile_support.diagnostics import add_error
from pfp_core.engine.plan_types import CompileDiagItem
from pfp_core.ext.ext_catalog import ExtCatalog


def try_get_mapping_op(
    catalog: ExtCatalog,
    op_id: str,
    path: str,
    diagnostics: List[CompileDiagItem],
) -> Optional[Any]:
    """Resolve mapping op spec by id, collecting link diagnostics.

    Args:
        catalog: Ext-modules catalog instance.
        op_id: Mapping operation identifier.
        path: Diagnostic path for operation id.
        diagnostics: Mutable diagnostics accumulator.

    Returns:
        Mapping op specification or None if missing in catalog.
    """

    try:
        return catalog.get_mapping_op(op_id)
    except KeyError:
        add_error(
            diagnostics,
            code="SCHEMA_LINK_OP_NOT_FOUND",
            path=path,
            message="Mapping op '" + op_id + "' is allowed but not found in catalog.",
        )
        return None


def try_get_validation_module(
    catalog: ExtCatalog,
    module_id: str,
    path: str,
    diagnostics: List[CompileDiagItem],
) -> Optional[Any]:
    """Resolve validation module spec by id, collecting link diagnostics.

    Args:
        catalog: Ext-modules catalog instance.
        module_id: Validation module identifier.
        path: Diagnostic path for module id.
        diagnostics: Mutable diagnostics accumulator.

    Returns:
        Validation module specification or None if missing in catalog.
    """

    try:
        return catalog.get_validation_module(module_id)
    except KeyError:
        add_error(
            diagnostics,
            code="SCHEMA_LINK_MODULE_NOT_FOUND",
            path=path,
            message=(
                "Validation module '"
                + module_id
                + "' is allowed but not found in catalog."
            ),
        )
        return None
