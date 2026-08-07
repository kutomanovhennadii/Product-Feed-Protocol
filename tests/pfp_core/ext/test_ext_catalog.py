import pytest

from pfp_core.ext import ExtCatalog, build_builtin_catalog
from pfp_core.ext.mapping.module_mapping_to_str import get_spec as to_str_spec
from pfp_core.ext.validation.module_validation_required import get_spec as required_spec


def test_duplicate_mapping_registration_is_forbidden() -> None:
    """Registering the same mapping op id twice fails fast."""
    catalog = ExtCatalog()
    spec = to_str_spec()

    catalog.register_mapping_op(spec)

    with pytest.raises(ValueError):
        catalog.register_mapping_op(spec)


def test_get_mapping_op_returns_registered_spec() -> None:
    """Registered mapping op can be retrieved by op_id."""
    catalog = ExtCatalog()
    spec = to_str_spec()

    catalog.register_mapping_op(spec)

    assert catalog.get_mapping_op(spec.op_id) == spec


def test_duplicate_validation_registration_is_forbidden() -> None:
    """Registering the same validation module id twice fails fast."""
    catalog = ExtCatalog()
    spec = required_spec()

    catalog.register_validation_module(spec)

    with pytest.raises(ValueError):
        catalog.register_validation_module(spec)


def test_get_validation_module_returns_registered_spec() -> None:
    """Registered validation module can be retrieved by module_id."""
    catalog = ExtCatalog()
    spec = required_spec()

    catalog.register_validation_module(spec)

    assert catalog.get_validation_module(spec.module_id) == spec


def test_catalog_listing_is_sorted_and_deterministic() -> None:
    """Catalog listing order is stable and sorted for determinism."""
    catalog = build_builtin_catalog()

    assert catalog.list_mapping_ops() == sorted(catalog.list_mapping_ops())
    assert catalog.list_validation_modules() == sorted(
        catalog.list_validation_modules()
    )
