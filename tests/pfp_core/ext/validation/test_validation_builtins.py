from pfp_core.ext.validation.validation_builtins import VALIDATION_BUILTINS


def test_validation_builtins_is_tuple_of_callables() -> None:
    """Allowlist is a tuple and every entry is a callable spec builder."""
    assert isinstance(VALIDATION_BUILTINS, tuple)
    assert all(callable(builder) for builder in VALIDATION_BUILTINS)


def test_validation_builtins_module_ids_are_complete_and_unique() -> None:
    """Allowlist builds the expected set of unique validation module ids."""
    specs = [builder() for builder in VALIDATION_BUILTINS]
    module_ids = [spec.module_id for spec in specs]
    expected_module_ids = {
        "required",
        "required_if_profile",
        "type",
        "enum",
        "range",
    }

    assert len(module_ids) == len(expected_module_ids)
    assert len(module_ids) == len(set(module_ids))
    assert set(module_ids) == expected_module_ids
    assert all(callable(spec.call) for spec in specs)
