"""Integration tests for the pfp_core.policies block."""

from __future__ import annotations

from pfp_core.policies.policy_config_loader import load_policy_bundle_from_yaml_text
from pfp_utils.diagnostics.diagnostic_models import Diagnostic, DiagnosticSeverity
from pfp_utils.logging import build_log_pipeline


def test_policy_bundle_applies_fail_on_error_strictness() -> None:
    """Policy YAML builds a bundle whose strictness policy preserves failures."""

    bundle = load_policy_bundle_from_yaml_text(
        'version: "1.0"\n'
        "core:\n"
        "  strictness:\n"
        '    strategy: "fail_on_error"\n'
        "  fault_isolation:\n"
        '    strategy: "SKIP_ITEM"\n',
        log_pipeline=build_log_pipeline("INFO", "TEXT", {}),
    )

    decision = bundle.strictness.apply(
        [Diagnostic(DiagnosticSeverity.ERROR, code="RULE.FAIL", message="broken")]
    )

    assert decision.should_fail is True
    assert decision.drop_invalid is False
    assert decision.diagnostics[0].code == "RULE.FAIL"
    assert bundle.fault_isolation is not None


def test_policy_bundle_applies_warn_only_downgrade() -> None:
    """Policy integration downgrades strictness diagnostics under warn_only mode."""

    bundle = load_policy_bundle_from_yaml_text(
        'version: "1.0"\n' "core:\n" "  strictness:\n" '    strategy: "warn_only"\n',
        log_pipeline=build_log_pipeline("INFO", "TEXT", {}),
    )

    decision = bundle.strictness.apply(
        [Diagnostic(DiagnosticSeverity.ERROR, code="RULE.FAIL", message="broken")]
    )

    assert decision.should_fail is False
    assert decision.drop_invalid is False
    assert decision.diagnostics[0].severity is DiagnosticSeverity.WARN
