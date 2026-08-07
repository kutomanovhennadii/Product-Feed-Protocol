from pfp_core.engine.mapping.compile_presence import (
    compile_field_presence,
    read_global_presence,
)
from pfp_core.engine.plan_types import CompileDiagItem


def test_read_global_presence_reports_invalid_entries() -> None:
    diagnostics: list[CompileDiagItem] = []
    default = read_global_presence(
        {"presence": {"default": 10, "per_mode": "bad"}},
        diagnostics,
    )

    assert default == "omit_missing"
    assert len(diagnostics) == 1


def test_compile_field_presence_overrides_default() -> None:
    diagnostics: list[CompileDiagItem] = []
    presence = compile_field_presence(
        field_mapping={"presence": {"default": "error_if_missing"}},
        field_path="mapping.fields.id",
        global_default="omit_missing",
        diagnostics=diagnostics,
    )

    assert presence.behavior == "error_if_missing"
    assert diagnostics == []


def test_compile_field_presence_ignores_legacy_per_mode_payload() -> None:
    diagnostics: list[CompileDiagItem] = []
    presence = compile_field_presence(
        field_mapping={
            "presence": {
                "default": "omit_missing",
                "per_mode": {"UNKNOWN": "omit_missing", "FULL": "bad"},
            }
        },
        field_path="mapping.fields.id",
        global_default="omit_missing",
        diagnostics=diagnostics,
    )

    assert presence.behavior == "omit_missing"
    assert diagnostics == []


def test_compile_field_presence_global_default_fallback_branch() -> None:
    diagnostics: list[CompileDiagItem] = []
    presence = compile_field_presence(
        field_mapping={},
        field_path="mapping.fields.id",
        global_default="invalid",
        diagnostics=diagnostics,
    )

    assert presence.behavior == "omit_missing"
    assert diagnostics == []


def test_compile_field_presence_reports_non_object_per_mode() -> None:
    diagnostics: list[CompileDiagItem] = []
    presence = compile_field_presence(
        field_mapping={
            "presence": {
                "default": "emit_null_if_missing",
                "per_mode": "bad",
            }
        },
        field_path="mapping.fields.id",
        global_default="omit_missing",
        diagnostics=diagnostics,
    )

    assert presence.behavior == "emit_null_if_missing"
    assert diagnostics == []


def test_read_global_presence_valid_default_value() -> None:
    diagnostics: list[CompileDiagItem] = []
    default = read_global_presence(
        {
            "presence": {
                "default": "emit_null_if_missing",
                "per_mode": {
                    "FULL": "error_if_missing",
                    "DIFF": "omit_missing",
                },
            }
        },
        diagnostics,
    )

    assert default == "emit_null_if_missing"
    assert diagnostics == []


def test_compile_field_presence_invalid_default_reports_error() -> None:
    diagnostics: list[CompileDiagItem] = []
    presence = compile_field_presence(
        field_mapping={"presence": {"default": "bad"}},
        field_path="mapping.fields.id",
        global_default="omit_missing",
        diagnostics=diagnostics,
    )

    assert presence.behavior == "omit_missing"
    assert len(diagnostics) == 1
    assert diagnostics[0].code == "COMPILER_PRESENCE_DEFAULT_INVALID"


def test_read_global_presence_ignores_legacy_per_mode_entry() -> None:
    diagnostics: list[CompileDiagItem] = []
    default = read_global_presence(
        {
            "presence": {
                "default": "omit_missing",
                "per_mode": {"BAD": "omit_missing"},
            }
        },
        diagnostics,
    )

    assert default == "omit_missing"
    assert diagnostics == []
