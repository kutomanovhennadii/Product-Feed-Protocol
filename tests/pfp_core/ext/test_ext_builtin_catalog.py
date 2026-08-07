"""Tests for built-in extension catalog assembly."""

from pfp_core.ext.ext_builtin_catalog import build_builtin_catalog


def test_build_builtin_catalog_registers_mapping_and_validation_specs() -> None:
    """Builtin catalog exposes expected mapping ops and validation modules."""

    catalog = build_builtin_catalog()

    assert "to_str" in catalog.list_mapping_ops()
    assert catalog.get_mapping_op("to_str").op_id == "to_str"
    assert "required_if_profile" in catalog.list_validation_modules()
    assert (
        catalog.get_validation_module("required_if_profile").module_id
        == "required_if_profile"
    )
