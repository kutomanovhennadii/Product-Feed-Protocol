"""Schema constraints for mapping ops and validation modules."""

from __future__ import annotations

from typing import FrozenSet

MAPPING_OP_ALLOWLIST: FrozenSet[str] = frozenset(
    {
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
        "map_enum",
        "coalesce",
        "default_if_missing",
        "concat",
        "join",
        "emit_if_present",
        "emit_null_if_missing",
        "omit_if_missing",
        "default_value",
        "regex_extract",
        "strip_suffix",
        "truncate",
        "format_shipping",
        "bool_to_str_lower",
        "digits_only",
        "country_list_to_iso3166_alpha2",
        "url_list_to_comma_separated",
        "first_url",
        "validate_url",
        "date_to_iso",
        "price_to_string",
        "validate_iso8601_date_range",
        "disallow_newlines",
        "disallow_all_caps",
        "plain_text_only",
        "lowercase_required",
        "object_string_values_only",
        "normalize_category_path",
        "assert_max_len",
        "assert_min",
        "assert_len_exact",
        "assert_len_range",
        "strip_html",
        "bool_to_availability",
        "int_to_availability",
        "format_price",
        "map_tax_code",
    }
)


VALIDATION_MODULE_ALLOWLIST: FrozenSet[str] = frozenset(
    {
        "required",
        "type",
        "enum",
        "range",
        "regex",
        "min_length",
        "max_length",
        "required_if_profile",
        "forbid_if_mode",
        "mode_forbid",
        "require_if_present",
        "require_if_equals",
        "forbid_if_equals",
        "dependency_if_present",
        "dependency_if_equals",
        "dependency_if_any_present",
        "numeric_compare_money",
    }
)
