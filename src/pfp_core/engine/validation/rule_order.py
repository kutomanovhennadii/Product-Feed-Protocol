"""Deterministic ordering helpers for validation rules."""

from __future__ import annotations

from typing import List, Tuple

from pfp_core.engine.compile_support.shapes import as_mapping


def ordered_rules(rules: List[object]) -> List[Tuple[int, object]]:
    """Return deterministic rule order by id or stable fallback key.

    Args:
        rules: Raw validation rules list from schema.

    Returns:
        List of `(original_index, rule)` in deterministic order.
    """

    items: List[Tuple[int, object, Tuple[str, str, str, int]]] = []
    for index, rule in enumerate(rules):
        rule_map = as_mapping(rule)
        if rule_map is None:
            items.append((index, rule, ("2", "", "", index)))
            continue

        rule_id_obj = rule_map.get("id")
        module_obj = rule_map.get("module_id")
        applies_to_obj = as_mapping(rule_map.get("applies_to", {})) or {}
        field_obj = applies_to_obj.get("field")

        if isinstance(rule_id_obj, str) and rule_id_obj:
            key = ("0", rule_id_obj, "", index)
        else:
            module_key = module_obj if isinstance(module_obj, str) else ""
            field_key = field_obj if isinstance(field_obj, str) else ""
            key = ("1", module_key, field_key, index)
        items.append((index, rule, key))

    items.sort(key=lambda item: item[2])
    return [(index, rule) for index, rule, _ in items]
