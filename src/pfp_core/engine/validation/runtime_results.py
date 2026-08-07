"""Validation runtime helpers for result and DiagnosticSeverity normalization."""

from __future__ import annotations

from typing import Callable, Literal, Mapping, Optional, TypeVar, Union, cast

from pfp_utils.diagnostics.diagnostic_models import DiagnosticSeverity

ValidationSeverity = Literal["FAIL", "WARN", "DROP"]
TNormalizedResult = TypeVar("TNormalizedResult")


def _normalize_module_result(
    raw_result: object,
    result_factory: Callable[..., TNormalizedResult],
) -> TNormalizedResult:
    """Normalize raw validation module output into stable structure.

    Args:
        raw_result: Raw module return value.
        result_factory: `NormalizedModuleResult` constructor.

    Returns:
        Normalized module result with shape-validity marker.
    """

    if isinstance(raw_result, Mapping):
        result_map = cast(Mapping[str, object], raw_result)
        ok_obj = result_map.get("ok")
        if not isinstance(ok_obj, bool):
            return result_factory(
                ok=False,
                code=None,
                message=None,
                details=None,
                path=None,
                valid_shape=False,
            )
        code_obj = result_map.get("code")
        message_obj = result_map.get("message")
        details_obj = result_map.get("details")
        path_obj = result_map.get("path")
        return result_factory(
            ok=ok_obj,
            code=code_obj if isinstance(code_obj, str) else None,
            message=message_obj if isinstance(message_obj, str) else None,
            details=details_obj if isinstance(details_obj, str) else None,
            path=path_obj if isinstance(path_obj, str) else None,
            valid_shape=True,
        )

    if not hasattr(raw_result, "ok"):
        return result_factory(
            ok=False,
            code=None,
            message=None,
            details=None,
            path=None,
            valid_shape=False,
        )

    ok_obj = getattr(raw_result, "ok", None)
    if not isinstance(ok_obj, bool):
        return result_factory(
            ok=False,
            code=None,
            message=None,
            details=None,
            path=None,
            valid_shape=False,
        )

    code_obj = getattr(raw_result, "code", None)
    message_obj = getattr(raw_result, "message", None)
    details_obj = getattr(raw_result, "details", None)
    path_obj = getattr(raw_result, "path", None)
    return result_factory(
        ok=ok_obj,
        code=code_obj if isinstance(code_obj, str) else None,
        message=message_obj if isinstance(message_obj, str) else None,
        details=details_obj if isinstance(details_obj, str) else None,
        path=path_obj if isinstance(path_obj, str) else None,
        valid_shape=True,
    )


def _normalize_rule_severity(severity_hint: Optional[str]) -> ValidationSeverity:
    """Normalize schema DiagnosticSeverity hint into executor DiagnosticSeverity enum."""

    if severity_hint is None:
        return "FAIL"
    text = severity_hint.strip().upper()
    if text == "WARN":
        return "WARN"
    if text == "DROP":
        return "DROP"
    if text == "FAIL":
        return "FAIL"
    if text == "ERROR":
        return "FAIL"
    return "FAIL"


def _to_diagnostic_severity(item: object) -> DiagnosticSeverity:
    """Map validation item DiagnosticSeverity to diagnostics DiagnosticSeverity."""

    level = getattr(item, "severity", getattr(item, "DiagnosticSeverity", None))
    if level == "WARN":
        return DiagnosticSeverity.WARN
    return DiagnosticSeverity.ERROR


def _from_strictness_diagnostic(
    *,
    severity: Optional[Union[DiagnosticSeverity, str]] = None,
    DiagnosticSeverity: Optional[Union[DiagnosticSeverity, str]] = None,
    drop_invalid: bool,
) -> ValidationSeverity:
    """Map strictness diagnostics DiagnosticSeverity back to validation DiagnosticSeverity."""

    value = severity if severity is not None else DiagnosticSeverity
    if value is None:
        raise TypeError("severity is required")
    normalized = globals()["DiagnosticSeverity"].normalize(value)
    if normalized is globals()["DiagnosticSeverity"].WARN:
        return "WARN"
    if drop_invalid:
        return "DROP"
    return "FAIL"
