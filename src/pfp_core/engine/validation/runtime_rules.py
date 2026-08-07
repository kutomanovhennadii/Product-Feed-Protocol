"""Validation runtime helpers for applicability and item construction."""

from __future__ import annotations

from typing import Callable, Literal, Mapping, TypeVar

from pfp_core.engine.plan_types import ValidationRulePlan
from pfp_core.ext.ext_types import MISSING

ValidationSeverity = Literal["FAIL", "WARN", "DROP"]
TValidationItem = TypeVar("TValidationItem")


def _rule_applies_to_mode(
    rule: ValidationRulePlan,
    artifact_profile: str,
) -> bool:
    """Check whether validation rule is enabled for execution.

    Args:
        rule: Compiled validation rule plan.
        artifact_profile: Current artifact profile.

    Returns:
        True when rule must be applied, otherwise False.
    """

    # Legacy gating is disabled in validation engine.
    _ = rule
    _ = artifact_profile
    return True


def _resolve_rule_value(
    rule: ValidationRulePlan, input_record: Mapping[str, object]
) -> object:
    """Resolve value passed to validation module for a rule.

    Args:
        rule: Compiled validation rule plan.
        input_record: Source record for current item.

    Returns:
        Field value for field-scoped rules or entire input record otherwise.
    """

    if rule.applies_to_field is None:
        return input_record
    return input_record.get(rule.applies_to_field, MISSING)


def _default_path(rule: ValidationRulePlan) -> str:
    """Build default diagnostics path for a validation rule.

    Args:
        rule: Compiled validation rule plan.

    Returns:
        Record-level path `$` or field-level path `fields.<name>`.
    """

    if rule.applies_to_field is None:
        return "$"
    return "fields." + rule.applies_to_field


def _runtime_item(
    *,
    code: str,
    message: str,
    path: str,
    rule: ValidationRulePlan,
    severity: ValidationSeverity = "FAIL",
    DiagnosticSeverity: ValidationSeverity = "FAIL",
    item_factory: Callable[..., TValidationItem],
) -> TValidationItem:
    """Create deterministic runtime validation report item.

    Args:
        code: Stable issue code.
        message: Deterministic issue message.
        path: Issue path.
        rule: Rule that produced runtime issue.
        severity: Effective runtime severity.
        DiagnosticSeverity: Compatibility severity keyword.
        item_factory: ValidationReportItem constructor.

    Returns:
        Validation report item instance.
    """

    effective_severity = severity if severity != "FAIL" else DiagnosticSeverity

    return item_factory(
        code=code,
        message=message,
        path=path,
        rule_id=rule.rule_id,
        module_id=rule.module_id,
        severity=effective_severity,
        severity_hint=rule.severity_hint,
    )
