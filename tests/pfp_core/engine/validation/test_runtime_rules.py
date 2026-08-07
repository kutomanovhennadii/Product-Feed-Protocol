from pfp_core.engine.plan_types import ValidationRulePlan
from pfp_core.engine.validation.runtime_rules import (
    _default_path,
    _resolve_rule_value,
    _rule_applies_to_mode,
    _runtime_item,
)


def test_validation_runtime_rule_helpers() -> None:
    rule = ValidationRulePlan(module_id="required", applies_to_field="id")
    assert _rule_applies_to_mode(rule, "catalog_delta") is True
    assert _rule_applies_to_mode(rule, "inventory_price_delta") is True
    assert _rule_applies_to_mode(rule, "catalog_snapshot") is True
    assert _resolve_rule_value(rule, {"id": "p1"}) == "p1"
    assert _default_path(rule) == "fields.id"

    item = _runtime_item(
        code="X",
        message="m",
        path="p",
        rule=rule,
        DiagnosticSeverity="FAIL",
        item_factory=lambda **kwargs: kwargs,
    )
    assert item["module_id"] == "required"
