"""Tests for mapping_contract registry integrity."""

import pytest

import pfp_core.ext.mapping.mapping_contract as contract_mod
from pfp_core.ext.ext_types import MappingOpSpec, ParamSpec, TypeSpec
from pfp_core.ext.mapping.mapping_contract import (
    MAPPING_OP_REGISTRY,
    get_mapping_op_spec,
    list_mapping_op_ids,
)

_BLOCK_B_OPS = [
    "default_value",
    "regex_extract",
    "strip_suffix",
    "truncate",
    "format_shipping",
    "strip_html",
    "bool_to_availability",
    "int_to_availability",
    "format_price",
    "map_tax_code",
]


@pytest.mark.parametrize("op_id", _BLOCK_B_OPS)
def test_registry_contains_block_b_op(op_id: str) -> None:
    """Block B op is registered in MAPPING_OP_REGISTRY."""
    assert op_id in MAPPING_OP_REGISTRY


def test_registry_total_count() -> None:
    """Registry contains expected number of operations."""
    assert len(MAPPING_OP_REGISTRY) == 27


def test_registry_op_id_matches_key() -> None:
    """Every registry key matches its spec op_id."""
    for key, builder in MAPPING_OP_REGISTRY.items():
        spec = builder()
        assert spec.op_id == key, f"Key {key!r} != spec.op_id {spec.op_id!r}"


def test_list_mapping_op_ids_returns_sorted() -> None:
    """list_mapping_op_ids returns sorted list including Block B ops."""
    ids = list_mapping_op_ids()
    assert ids == sorted(ids)
    for op_id in _BLOCK_B_OPS:
        assert op_id in ids


def test_get_mapping_op_spec_unknown_raises() -> None:
    """Unknown op_id raises ValueError."""
    with pytest.raises(ValueError):
        get_mapping_op_spec("nonexistent_op")


def test_get_mapping_op_spec_returns_known_builder_output() -> None:
    """Known registry ids resolve to their built MappingOpSpec."""

    assert get_mapping_op_spec("trim").op_id == "trim"


def test_mapping_contract_validates_registry_builder_integrity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Registry validation rejects empty ids and mismatched builder outputs."""

    def _build_spec(op_id: str) -> MappingOpSpec:
        return MappingOpSpec(
            op_id=op_id,
            input_type=TypeSpec("string"),
            output_type=TypeSpec("string"),
            args_spec=ParamSpec(),
            call=lambda value, args: value,
        )

    monkeypatch.setattr(
        contract_mod,
        "MAPPING_OP_REGISTRY",
        {"trim": lambda: _build_spec("")},
    )
    with pytest.raises(ValueError, match="spec.op_id is empty"):
        contract_mod._validate_mapping_op_registry()

    monkeypatch.setattr(
        contract_mod,
        "MAPPING_OP_REGISTRY",
        {"trim": lambda: _build_spec("lower")},
    )
    with pytest.raises(ValueError, match="spec.op_id='lower'"):
        contract_mod._validate_mapping_op_registry()
