from pfp_core.ext.mapping.mapping_builtins import MAPPING_BUILTINS


def test_mapping_builtins_is_tuple_of_callables() -> None:
    """Allowlist is a tuple and every entry is a callable spec builder."""
    assert isinstance(MAPPING_BUILTINS, tuple)
    assert all(callable(builder) for builder in MAPPING_BUILTINS)


def test_mapping_builtins_op_ids_are_complete_and_unique() -> None:
    """Allowlist builds the expected set of unique mapping operation ids."""
    op_ids = [builder().op_id for builder in MAPPING_BUILTINS]
    expected_op_ids = {
        "get_path",
        "to_str",
        "to_int",
        "to_decimal",
        "to_bool",
        "trim",
        "lower",
        "upper",
        "normalize_whitespace",
        "parse_date",
        "format_date",
        "format_datetime_utc",
        "round_decimal",
        "format_money",
        "format_price",
        "bool_to_availability",
        "int_to_availability",
        "emit_if_present",
        "emit_null_if_missing",
        "omit_if_missing",
        "default_value",
        "regex_extract",
        "strip_suffix",
        "strip_html",
        "truncate",
        "format_shipping",
        "map_tax_code",
    }
    assert len(op_ids) == len(expected_op_ids)
    assert len(set(op_ids)) == len(expected_op_ids)
    assert set(op_ids) == expected_op_ids
