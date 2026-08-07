from pfp_core.engine.mapping.output import (
    compile_output_order,
    read_delete_tombstone_settings,
)
from pfp_core.engine.plan_types import CompileDiagItem


def test_compile_output_order_reports_duplicate_and_missing() -> None:
    diagnostics: list[CompileDiagItem] = []
    order = compile_output_order(
        output_kind="csv_row",
        mapping_section={"output_order": ["id", "id"]},
        known_fields={"id", "title"},
        diagnostics=diagnostics,
    )

    assert order == ("id", "id")
    assert any(
        item.code == "COMPILER_MAPPING_OUTPUT_ORDER_INVALID" for item in diagnostics
    )


def test_read_delete_tombstone_settings_defaults_on_missing() -> None:
    diagnostics: list[CompileDiagItem] = []
    assert read_delete_tombstone_settings(
        mapping_section={}, diagnostics=diagnostics
    ) == (
        False,
        "delete",
        "id",
    )


def test_compile_output_order_non_csv_returns_none_without_diagnostics() -> None:
    diagnostics: list[CompileDiagItem] = []
    order = compile_output_order(
        output_kind="json_object",
        mapping_section={"output_order": "bad"},
        known_fields={"id"},
        diagnostics=diagnostics,
    )

    assert order is None
    assert diagnostics == []


def test_read_delete_tombstone_settings_reports_invalid_structure_and_values() -> None:
    diagnostics: list[CompileDiagItem] = []
    settings = read_delete_tombstone_settings(
        mapping_section={
            "delete_tombstone": {
                "enabled": "yes",
                "flag_path": "",
                "id_field": 1,
            }
        },
        diagnostics=diagnostics,
    )

    assert settings == (False, "delete", "id")
    assert len(diagnostics) == 3
    assert all(
        item.code == "COMPILER_MAPPING_DELETE_TOMBSTONE_INVALID" for item in diagnostics
    )


def test_read_delete_tombstone_settings_reports_non_object_config() -> None:
    diagnostics: list[CompileDiagItem] = []
    settings = read_delete_tombstone_settings(
        mapping_section={"delete_tombstone": "bad"},
        diagnostics=diagnostics,
    )

    assert settings == (False, "delete", "id")
    assert len(diagnostics) == 1
    assert diagnostics[0].code == "COMPILER_MAPPING_DELETE_TOMBSTONE_INVALID"


def test_read_delete_tombstone_settings_reads_valid_custom_values() -> None:
    diagnostics: list[CompileDiagItem] = []
    settings = read_delete_tombstone_settings(
        mapping_section={
            "delete_tombstone": {
                "enabled": True,
                "flag_path": "meta.delete",
                "id_field": "sku",
            }
        },
        diagnostics=diagnostics,
    )

    assert settings == (True, "meta.delete", "sku")
    assert diagnostics == []
