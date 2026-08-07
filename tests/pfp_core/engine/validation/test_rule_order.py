from pfp_core.engine.validation.rule_order import ordered_rules


def test_ordered_rules_prioritizes_rules_with_id() -> None:
    rules = [
        {"module_id": "required", "applies_to": {"field": "b"}},
        {"id": "a_rule", "module_id": "required"},
        {"module_id": "required", "applies_to": {"field": "a"}},
    ]

    ordered = ordered_rules(rules)
    assert ordered[0][0] == 1
