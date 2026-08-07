from pfp_core.engine.validation.decision import (
    _decision_from_strictness,
    _decision_without_policies,
)


def test_validation_decision_helpers() -> None:
    warn_item = type("Item", (), {"DiagnosticSeverity": "WARN"})()
    assert _decision_without_policies((warn_item,)) == "WARN"

    strictness = type("Strictness", (), {"should_fail": False, "drop_invalid": True})()
    assert _decision_from_strictness(strictness, (warn_item,)) == "DROP"


def test_decision_without_policies_fail_drop_and_pass() -> None:
    fail_item = type("Item", (), {"DiagnosticSeverity": "FAIL"})()
    drop_item = type("Item", (), {"DiagnosticSeverity": "DROP"})()
    pass_item = type("Item", (), {"DiagnosticSeverity": "PASS"})()

    assert _decision_without_policies((fail_item,)) == "FAIL"
    assert _decision_without_policies((drop_item,)) == "DROP"
    assert _decision_without_policies((pass_item,)) == "PASS"


def test_decision_from_strictness_covers_all_paths() -> None:
    warn_item = type("Item", (), {"DiagnosticSeverity": "WARN"})()
    drop_item = type("Item", (), {"DiagnosticSeverity": "DROP"})()

    should_fail = type("Strictness", (), {"should_fail": True, "drop_invalid": False})()
    assert _decision_from_strictness(should_fail, (warn_item,)) == "FAIL"

    no_policy = type("Strictness", (), {"should_fail": False, "drop_invalid": False})()
    assert _decision_from_strictness(no_policy, (drop_item,)) == "DROP"
    assert _decision_from_strictness(no_policy, (warn_item,)) == "WARN"
    assert _decision_from_strictness(no_policy, ()) == "PASS"
