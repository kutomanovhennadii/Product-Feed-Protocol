"""Root-level contract tests for `pfp_core.engine.catalog_resolver`."""

from __future__ import annotations

from typing import Tuple

from pfp_core.engine.catalog_resolver import (
    try_get_mapping_op,
    try_get_validation_module,
)
from pfp_core.engine.plan_types import CompileDiagItem
from pfp_core.ext import ExtCatalog, build_builtin_catalog


def _diag_tuples(
    diagnostics: list[CompileDiagItem],
) -> Tuple[Tuple[str, str, str, str], ...]:
    return tuple(
        (item.DiagnosticSeverity, item.code, item.path, item.message)
        for item in diagnostics
    )


def test_try_get_mapping_op_success_from_builtin_catalog() -> None:
    diagnostics: list[CompileDiagItem] = []
    op_spec = try_get_mapping_op(
        catalog=build_builtin_catalog(),
        op_id="to_str",
        path="mapping.fields.id.transforms[0].op",
        diagnostics=diagnostics,
    )

    assert op_spec is not None
    assert diagnostics == []


def test_try_get_mapping_op_missing_adds_diagnostic() -> None:
    diagnostics: list[CompileDiagItem] = []
    op_spec = try_get_mapping_op(
        catalog=ExtCatalog(),
        op_id="to_str",
        path="mapping.fields.id.transforms[0].op",
        diagnostics=diagnostics,
    )

    assert op_spec is None
    assert len(diagnostics) == 1
    assert diagnostics[0].code == "SCHEMA_LINK_OP_NOT_FOUND"
    assert diagnostics[0].path == "mapping.fields.id.transforms[0].op"


def test_try_get_validation_module_success_from_builtin_catalog() -> None:
    diagnostics: list[CompileDiagItem] = []
    module_spec = try_get_validation_module(
        catalog=build_builtin_catalog(),
        module_id="required",
        path="validation.rules[0].module_id",
        diagnostics=diagnostics,
    )

    assert module_spec is not None
    assert diagnostics == []


def test_try_get_validation_module_missing_adds_diagnostic_deterministically() -> None:
    diagnostics_first: list[CompileDiagItem] = []
    diagnostics_second: list[CompileDiagItem] = []

    first = try_get_validation_module(
        catalog=ExtCatalog(),
        module_id="required",
        path="validation.rules[0].module_id",
        diagnostics=diagnostics_first,
    )
    second = try_get_validation_module(
        catalog=ExtCatalog(),
        module_id="required",
        path="validation.rules[0].module_id",
        diagnostics=diagnostics_second,
    )

    assert first is None
    assert second is None
    assert _diag_tuples(diagnostics_first) == _diag_tuples(diagnostics_second)
    assert diagnostics_first[0].code == "SCHEMA_LINK_MODULE_NOT_FOUND"
    assert diagnostics_first[0].path == "validation.rules[0].module_id"
