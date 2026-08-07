import pytest

from pfp_core.engine.validation.runtime_results import (
    _from_strictness_diagnostic,
    _normalize_module_result,
    _normalize_rule_severity,
    _to_diagnostic_severity,
)
from pfp_utils.diagnostics.diagnostic_models import DiagnosticSeverity


def test_validation_runtime_result_helpers() -> None:
    """Cover runtime-result normalization helpers for the standard success path."""

    result = _normalize_module_result(
        {"ok": False, "code": "C", "message": "M", "path": "p"},
        lambda **kwargs: kwargs,
    )
    assert result["ok"] is False
    assert _normalize_rule_severity("warn") == "WARN"
    item = type("Item", (), {"DiagnosticSeverity": "WARN"})()
    assert _to_diagnostic_severity(item) is DiagnosticSeverity.WARN
    assert (
        _from_strictness_diagnostic(
            DiagnosticSeverity=DiagnosticSeverity.ERROR, drop_invalid=True
        )
        == "DROP"
    )


def test_normalize_module_result_invalid_shapes() -> None:
    """Ensure invalid runtime-result shapes are normalized into failure diagnostics."""

    non_mapping = _normalize_module_result(10, lambda **kwargs: kwargs)
    assert non_mapping["ok"] is False
    assert non_mapping["valid_shape"] is False

    missing_ok = _normalize_module_result({"code": "X"}, lambda **kwargs: kwargs)
    assert missing_ok["ok"] is False
    assert missing_ok["valid_shape"] is False

    class _Obj:
        ok = False
        code = 1
        message = 2
        details = 3
        path = 4

    normalized_obj = _normalize_module_result(_Obj(), lambda **kwargs: kwargs)
    assert normalized_obj["ok"] is False
    assert normalized_obj["valid_shape"] is True
    assert normalized_obj["code"] is None


def test_runtime_result_severity_helpers_cover_remaining_paths() -> None:
    """Cover fallback severity mappings for strictness diagnostics and runtime items."""

    assert _normalize_rule_severity("DROP") == "DROP"
    assert _normalize_rule_severity("FAIL") == "FAIL"
    assert _normalize_rule_severity("ERROR") == "FAIL"
    assert _normalize_rule_severity("unknown") == "FAIL"
    assert _normalize_rule_severity(None) == "FAIL"

    item = type("Item", (), {"DiagnosticSeverity": "FAIL"})()
    assert _to_diagnostic_severity(item) is DiagnosticSeverity.ERROR
    assert (
        _from_strictness_diagnostic(
            DiagnosticSeverity=DiagnosticSeverity.WARN, drop_invalid=False
        )
        == "WARN"
    )
    assert (
        _from_strictness_diagnostic(
            DiagnosticSeverity=DiagnosticSeverity.ERROR, drop_invalid=False
        )
        == "FAIL"
    )


def test_from_strictness_diagnostic_requires_severity() -> None:
    """Strictness severity mapper raises when no severity source is supplied."""

    with pytest.raises(TypeError, match="severity is required"):
        _from_strictness_diagnostic(drop_invalid=False)
