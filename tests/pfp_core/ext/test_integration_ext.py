"""Integration tests for the pfp_core.ext block."""

from __future__ import annotations

import copy
from collections.abc import Iterable
from typing import Any, Dict, List, Mapping, Set, cast

from pfp_core.engine.compiler import SchemaCompiler
from pfp_core.engine.mapping_executor import MappingExecutor
from pfp_core.engine.validation_executor import ValidationExecutor
from pfp_core.ext.ext_builtin_catalog import build_builtin_catalog
from pfp_core.ext.ext_types import Emission, ProducerContext

_HEADER = {
    "protocol_id": "test.integration",
    "schema_version": "1.0.0",
    "artifact_profile": "test_profile",
    "title": "Integration test schema - all mapping ops",
    "source_protocol": {
        "provider": "test",
        "url": "N/A",
        "revision": "snapshot",
        "retrieved_at": "2026-03-01",
    },
}

_OUTPUT = {
    "output_kind": "json_object",
    "writer_id": "jsonl",
    "writer_config": {
        "ensure_ascii": False,
        "sort_keys": True,
        "omit_nulls": False,
        "line_terminator": "\n",
    },
    "artifact": {
        "content_type": "application/x-ndjson",
        "file_ext": ".jsonl",
        "file_extension": ".jsonl",
        "encoding": "utf-8",
    },
}


def _field(
    source_path: str, transforms: List[Dict[str, Any]], **extra: Any
) -> Dict[str, Any]:
    """Build a minimal field mapping definition.

    Args:
        source_path: Source path referenced by the field mapping.
        transforms: Ordered transform chain for the field.
        **extra: Additional mapping attributes merged into the field definition.

    Returns:
        Mapping definition ready for insertion into the schema document.
    """

    field: Dict[str, Any] = {
        "source": {"path": source_path, "required": False},
        "transforms": transforms,
    }
    field.update(extra)
    return field


_FIELDS = {
    "f_to_str_trim": _field("f_to_str_trim", [{"op": "to_str"}, {"op": "trim"}]),
    "f_lower": _field(
        "f_lower",
        [{"op": "to_str"}, {"op": "lower"}],
        presence={"default": "error_if_missing"},
    ),
    "f_upper": _field("f_upper", [{"op": "to_str"}, {"op": "upper"}]),
    "f_normalize_ws": _field(
        "f_normalize_ws",
        [{"op": "to_str"}, {"op": "normalize_whitespace"}],
    ),
    "f_to_int": _field("f_to_int", [{"op": "to_int"}]),
    "f_to_decimal_round": _field(
        "f_to_decimal_round",
        [{"op": "to_decimal"}, {"op": "round_decimal", "args": {"decimals": 2}}],
    ),
    "f_to_bool": _field("f_to_bool", [{"op": "to_bool"}]),
    "f_parse_format_date": _field(
        "f_parse_format_date",
        [{"op": "parse_date"}, {"op": "format_date"}],
    ),
    "f_format_datetime": _field("f_format_datetime", [{"op": "format_datetime_utc"}]),
    "f_format_money": _field(
        "f_format_money",
        [
            {
                "op": "format_money",
                "args": {
                    "decimals": 2,
                    "pattern": "{amount} {currency}",
                    "currency": "USD",
                },
            }
        ],
    ),
    "f_truncate": _field(
        "f_truncate", [{"op": "to_str"}, {"op": "truncate", "args": {"max_length": 5}}]
    ),
    "f_default_value": _field(
        "f_default_value",
        [{"op": "default_value", "args": {"value": "N/A"}}, {"op": "to_str"}],
    ),
    "f_regex_extract": _field(
        "f_regex_extract",
        [
            {"op": "to_str"},
            {"op": "regex_extract", "args": {"pattern": "(\\d+)", "group": 1}},
        ],
    ),
    "f_strip_suffix": _field(
        "f_strip_suffix",
        [{"op": "to_str"}, {"op": "strip_suffix", "args": {"delimiters": ["-"]}}],
    ),
    "f_format_shipping": _field(
        "f_format_shipping",
        [{"op": "format_shipping", "args": {"pattern": "{country}={price}"}}],
    ),
    "f_get_path": _field(
        "f_get_path_src",
        [{"op": "get_path", "args": {"path": "nested_key"}}, {"op": "to_str"}],
    ),
    "f_strip_html": _field("f_strip_html", [{"op": "strip_html"}]),
    "f_bool_to_avail": _field("f_bool_to_avail", [{"op": "bool_to_availability"}]),
    "f_int_to_avail": _field("f_int_to_avail", [{"op": "int_to_availability"}]),
    "f_format_price": _field(
        "f_format_price", [{"op": "format_price", "args": {"currency": "USD"}}]
    ),
    "f_map_tax_code": _field("f_map_tax_code", [{"op": "map_tax_code", "args": {}}]),
    "f_emit_if_present": _field(
        "f_emit_if_present", [{"op": "to_str"}, {"op": "emit_if_present"}]
    ),
    "f_emit_null": _field("f_emit_null", [{"op": "emit_null_if_missing"}]),
    "f_omit": _field("f_omit", [{"op": "omit_if_missing"}]),
}

_VALIDATION_RULES = [
    {
        "id": "v_required",
        "applies_to": {"field": "f_to_str_trim"},
        "module_id": "required",
        "config": {},
        "on_fail": {
            "code": "V_REQUIRED",
            "message": "f_to_str_trim is required",
            "severity_hint": "ERROR",
        },
    },
    {
        "id": "v_required_if_profile",
        "applies_to": {"field": "f_lower"},
        "module_id": "required_if_profile",
        "config": {"artifact_profile": "catalog_snapshot"},
        "on_fail": {
            "code": "V_REQUIRED_IF_PROFILE",
            "message": "f_lower required for test_profile",
            "severity_hint": "ERROR",
        },
    },
    {
        "id": "v_type_check",
        "applies_to": {"field": "f_to_str_trim"},
        "module_id": "type",
        "config": {"type_id": "string"},
        "on_fail": {
            "code": "V_TYPE_CHECK",
            "message": "f_to_str_trim must be string",
            "severity_hint": "ERROR",
        },
    },
    {
        "id": "v_enum_check",
        "applies_to": {"field": "f_upper"},
        "module_id": "enum",
        "config": {"allowed": ["hello", "world", "test"]},
        "on_fail": {
            "code": "V_ENUM_CHECK",
            "message": "f_upper not in allowed set",
            "severity_hint": "ERROR",
        },
    },
    {
        "id": "v_range_check",
        "applies_to": {"field": "f_to_int"},
        "module_id": "range",
        "config": {"min": 0, "max": 100},
        "on_fail": {
            "code": "V_RANGE_CHECK",
            "message": "f_to_int out of range",
            "severity_hint": "ERROR",
        },
    },
]

_SCHEMA_DOC: Dict[str, Any] = {
    "header": _HEADER,
    "input": {"um_contract": "Unified Model items as dict-like objects."},
    "modes": {},
    "output": _OUTPUT,
    "mapping": {
        "output_kind": "json_object",
        "presence": {"default": "omit_missing"},
        "fields": _FIELDS,
    },
    "validation": {"rules": _VALIDATION_RULES},
}

_INPUT_RECORD: Dict[str, Any] = {
    "f_to_str_trim": "  hello  ",
    "f_lower": "Hello World",
    "f_upper": "hello",
    "f_normalize_ws": "  too   many   spaces  ",
    "f_to_int": "42",
    "f_to_decimal_round": "3.14159",
    "f_to_bool": "true",
    "f_parse_format_date": "2026-03-15",
    "f_format_datetime": "2026-03-15T10:30:00Z",
    "f_format_money": 19.99,
    "f_truncate": "abcdefghij",
    "f_regex_extract": "item-123-suffix",
    "f_strip_suffix": "SKU-VAR",
    "f_format_shipping": {"country": "US", "price": "5.00"},
    "f_get_path_src": {"nested_key": "deep_value"},
    "f_strip_html": "<p>Hi&nbsp;&nbsp;<b>there</b></p>",
    "f_bool_to_avail": "yes",
    "f_int_to_avail": 0,
    "f_format_price": "29.99",
    "f_map_tax_code": {
        "tax_category": "Apparel & Accessories > Clothing > Activewear",
        "taxable": True,
    },
    "f_emit_if_present": "exists",
}


def _compile_diagnostics_message(diagnostics: Iterable[Any]) -> str:
    """Format compilation diagnostics for assertion messages.

    Args:
        diagnostics: Diagnostic sequence returned by schema compilation.

    Returns:
        Joined assertion message string for failed compilations.
    """

    return "; ".join(f"[{d.code}] {d.path}: {d.message}" for d in diagnostics)


def _producer_context() -> ProducerContext:
    """Return compile-time lookup context for the tax mapping integration slice.

    Returns:
        Producer context populated with tax mapping defaults and mappings.
    """

    return ProducerContext(
        tax_mapping={
            "mappings": {"Apparel & Accessories > Clothing": "txcd_20031000"},
            "default_taxable": "txcd_99999999",
            "default_exempt": "txcd_00000000",
        }
    )


def test_ext_schema_compiles_successfully() -> None:
    """Extension catalog compiles a schema that references every builtin op and module."""

    compiler = SchemaCompiler(catalog=build_builtin_catalog())
    compiled = compiler.compile(copy.deepcopy(_SCHEMA_DOC), context=_producer_context())
    compile_message = _compile_diagnostics_message(compiled.diagnostics)

    assert compiled.is_valid, "Schema compilation failed: " + compile_message
    assert compiled.diagnostics == ()


def test_ext_full_pipeline_validate_then_map() -> None:
    """Builtin ext modules execute end to end through validation and mapping."""

    catalog = build_builtin_catalog()
    compiled = SchemaCompiler(catalog=catalog).compile(
        copy.deepcopy(_SCHEMA_DOC), context=_producer_context()
    )
    compile_message = _compile_diagnostics_message(compiled.diagnostics)

    assert compiled.is_valid, "Schema compilation failed: " + compile_message

    val_result = ValidationExecutor(catalog=catalog).run_one(
        plan=compiled.validation_plan,
        input_record=_INPUT_RECORD,
        artifact_profile="catalog_snapshot",
    )
    assert val_result.decision == "PASS"

    result = MappingExecutor(catalog=catalog).run_one(
        plan=compiled.mapping_plan,
        input_record=_INPUT_RECORD,
        artifact_profile="catalog_snapshot",
    )

    assert not result.issues
    output = cast(Mapping[str, Emission], result.output)
    assert output["f_to_str_trim"] == Emission(kind="VALUE", value="hello")
    assert output["f_lower"] == Emission(kind="VALUE", value="hello world")
    assert output["f_upper"] == Emission(kind="VALUE", value="HELLO")
    assert output["f_normalize_ws"] == Emission(kind="VALUE", value="too many spaces")
    assert output["f_to_int"] == Emission(kind="VALUE", value="42")
    assert output["f_to_decimal_round"] == Emission(kind="VALUE", value="3.14")
    assert output["f_to_bool"] == Emission(kind="VALUE", value="True")
    assert output["f_parse_format_date"] == Emission(kind="VALUE", value="2026-03-15")
    assert output["f_format_datetime"] == Emission(
        kind="VALUE", value="2026-03-15T10:30:00Z"
    )
    assert output["f_format_money"] == Emission(kind="VALUE", value="19.99 USD")
    assert output["f_truncate"] == Emission(kind="VALUE", value="abcde")
    assert output["f_default_value"] == Emission(kind="VALUE", value="N/A")
    assert output["f_regex_extract"] == Emission(kind="VALUE", value="123")
    assert output["f_strip_suffix"] == Emission(kind="VALUE", value="SKU")
    assert output["f_format_shipping"] == Emission(kind="VALUE", value="US=5.00")
    assert output["f_get_path"] == Emission(kind="VALUE", value="deep_value")
    assert output["f_strip_html"] == Emission(kind="VALUE", value="Hi there")
    assert output["f_bool_to_avail"] == Emission(kind="VALUE", value="in_stock")
    assert output["f_int_to_avail"] == Emission(kind="VALUE", value="out_of_stock")
    assert output["f_format_price"] == Emission(kind="VALUE", value="29.99 USD")
    assert output["f_map_tax_code"] == Emission(kind="VALUE", value="txcd_20031000")
    assert output["f_emit_if_present"] == Emission(kind="VALUE", value="exists")
    assert output["f_emit_null"] == Emission(kind="NULL")
    assert "f_omit" not in output


def test_ext_all_registered_mapping_ops_covered() -> None:
    """Integration schema covers every registered builtin mapping operation."""

    from pfp_core.ext.mapping.mapping_contract import MAPPING_OP_REGISTRY

    used_ops: Set[str] = set()
    for field_def in _FIELDS.values():
        for transform in field_def["transforms"]:
            op_id = transform.get("op")
            assert isinstance(op_id, str)
            used_ops.add(op_id)

    assert not (set(MAPPING_OP_REGISTRY.keys()) - used_ops)


def test_ext_all_registered_validation_modules_covered() -> None:
    """Integration schema covers every registered builtin validation module."""

    from pfp_core.ext.validation.validation_contract import VALIDATION_MODULE_REGISTRY

    used_modules: Set[str] = set()
    for rule in _VALIDATION_RULES:
        module_id = rule.get("module_id")
        assert isinstance(module_id, str)
        used_modules.add(module_id)

    assert not (set(VALIDATION_MODULE_REGISTRY.keys()) - used_modules)
