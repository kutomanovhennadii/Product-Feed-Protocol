from __future__ import annotations

from pfp_core.schema.schema_constraints import (
    MAPPING_OP_ALLOWLIST,
    VALIDATION_MODULE_ALLOWLIST,
)


def test_mapping_op_allowlist_contains_canonical_ops() -> None:
    """Ensure mapping operation allowlist keeps canonical operation identifiers."""

    assert "get_path" in MAPPING_OP_ALLOWLIST
    assert "assert_len_range" in MAPPING_OP_ALLOWLIST
    assert "map_tax_code" in MAPPING_OP_ALLOWLIST
    assert "missing_op" not in MAPPING_OP_ALLOWLIST


def test_validation_module_allowlist_contains_canonical_modules() -> None:
    """Ensure validation module allowlist keeps canonical module identifiers."""
    legacy_alias = "mode" + "_required"

    assert "required" in VALIDATION_MODULE_ALLOWLIST
    assert "numeric_compare_money" in VALIDATION_MODULE_ALLOWLIST
    assert legacy_alias not in VALIDATION_MODULE_ALLOWLIST
    assert "missing_module" not in VALIDATION_MODULE_ALLOWLIST
