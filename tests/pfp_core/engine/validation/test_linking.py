from typing import Mapping, Optional, cast

from pfp_core.engine.plan_types import CompileDiagItem
from pfp_core.engine.validation.linking import link_validation_module
from pfp_core.ext import ExtCatalog, build_builtin_catalog
from pfp_core.ext.ext_types import (
    ParamSpec,
    TypeSpec,
    ValidationModuleSpec,
    ValidationResult,
)


def test_link_validation_module_rejects_non_allowlisted_module() -> None:
    diagnostics: list[CompileDiagItem] = []
    linked, expected = link_validation_module(
        catalog=build_builtin_catalog(),
        module_id="not_allowlisted",
        rule_path="validation.rules[0]",
        diagnostics=diagnostics,
    )

    assert linked is False
    assert expected is None
    assert diagnostics[0].code == "SCHEMA_LINK_MODULE_NOT_ALLOWED"


def test_link_validation_module_rejects_legacy_required_by_mode_alias() -> None:
    """Legacy required-by-mode alias is rejected by allowlist linking guard."""
    diagnostics: list[CompileDiagItem] = []
    legacy_alias = "mode" + "_required"
    linked, expected = link_validation_module(
        catalog=build_builtin_catalog(),
        module_id=legacy_alias,
        rule_path="validation.rules[0]",
        diagnostics=diagnostics,
    )

    assert linked is False
    assert expected is None
    assert diagnostics[0].code == "SCHEMA_LINK_MODULE_NOT_ALLOWED"


def test_link_validation_module_reports_missing_in_catalog() -> None:
    diagnostics: list[CompileDiagItem] = []
    linked, expected = link_validation_module(
        catalog=ExtCatalog(),
        module_id="required",
        rule_path="validation.rules[0]",
        diagnostics=diagnostics,
    )

    assert linked is False
    assert expected is None
    assert diagnostics[0].code == "SCHEMA_LINK_MODULE_NOT_FOUND"


def test_link_validation_module_reports_invalid_value_type_id() -> None:
    diagnostics: list[CompileDiagItem] = []
    catalog = ExtCatalog()

    class _UnsupportedTypeSpec:
        type_id = "unsupported"

    def _ok_module_call(
        value: object,
        config: Mapping[str, object],
        record: Optional[Mapping[str, object]] = None,
        mode: Optional[str] = None,
    ) -> ValidationResult:
        _ = (value, config, mode, record)
        return ValidationResult(ok=True)

    catalog.register_validation_module(
        ValidationModuleSpec(
            module_id="required",
            value_type=cast(TypeSpec, _UnsupportedTypeSpec()),
            config_spec=ParamSpec(),
            call=_ok_module_call,
        )
    )

    linked, expected = link_validation_module(
        catalog=catalog,
        module_id="required",
        rule_path="validation.rules[0]",
        diagnostics=diagnostics,
    )

    assert linked is False
    assert expected is None
    assert diagnostics[0].code == "SCHEMA_TYPE_INVALID_TYPE_ID"
