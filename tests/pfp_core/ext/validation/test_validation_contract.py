"""Tests for validation contract registry."""

from __future__ import annotations

from typing import Any

import pytest

import pfp_core.ext.validation.validation_contract as contract_mod
from pfp_core.ext.ext_types import ParamSpec, TypeSpec, ValidationModuleSpec


def test_validation_contract_lists_and_builds_expected_specs() -> None:
    """Registry exposes deterministic ids and builders for known modules."""

    module_ids = contract_mod.list_validation_module_ids()

    assert module_ids == sorted(module_ids)
    assert "required_if_profile" in module_ids
    assert contract_mod.get_validation_module_spec("required_if_profile").module_id == (
        "required_if_profile"
    )


def test_validation_contract_rejects_unknown_module_id() -> None:
    """Getter fails fast when validation module id is not declared."""

    with pytest.raises(ValueError, match="Unknown validation module_id"):
        contract_mod.get_validation_module_spec("missing")


def test_validation_contract_validates_registry_builder_integrity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Registry validation rejects empty ids, mismatches, and non-callable specs."""

    def _valid_spec(
        module_id: str,
        *,
        call: Any = lambda *args: None,
    ) -> ValidationModuleSpec:
        return ValidationModuleSpec(
            module_id=module_id,
            value_type=TypeSpec("string"),
            config_spec=ParamSpec(),
            call=call,
        )

    monkeypatch.setattr(
        contract_mod,
        "VALIDATION_MODULE_REGISTRY",
        {"required": lambda: _valid_spec("")},
    )
    with pytest.raises(ValueError, match="spec.module_id is empty"):
        contract_mod._validate_validation_module_registry()

    monkeypatch.setattr(
        contract_mod,
        "VALIDATION_MODULE_REGISTRY",
        {"required": lambda: _valid_spec("range")},
    )
    with pytest.raises(ValueError, match="spec.module_id='range'"):
        contract_mod._validate_validation_module_registry()

    monkeypatch.setattr(
        contract_mod,
        "VALIDATION_MODULE_REGISTRY",
        {"required": lambda: _valid_spec("required", call=None)},
    )
    with pytest.raises(ValueError, match="spec.call is not callable"):
        contract_mod._validate_validation_module_registry()
