"""Validation executor for per-item execution of compiled `ValidationPlan`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal, Mapping, Optional, Tuple

from pfp_core.engine.plan_types import ValidationPlan
from pfp_core.engine.validation.decision import (
    _decision_from_strictness,
    _decision_without_policies,
)
from pfp_core.engine.validation.runtime_results import (
    _from_strictness_diagnostic,
    _normalize_module_result,
    _normalize_rule_severity,
    _to_diagnostic_severity,
)
from pfp_core.engine.validation.runtime_rules import (
    _default_path,
    _resolve_rule_value,
    _rule_applies_to_mode,
    _runtime_item,
)
from pfp_core.ext.ext_catalog import ExtCatalog
from pfp_core.policies import PolicyBundle
from pfp_utils.diagnostics.diagnostic_models import Diagnostic

ValidationDecision = Literal["PASS", "WARN", "DROP", "FAIL"]
ValidationSeverity = Literal["FAIL", "WARN", "DROP"]


@dataclass(frozen=True)
class NormalizedModuleResult:
    """Normalized view of raw validation module output.

    Args:
        ok: Validation pass flag.
        code: Optional module-provided error code.
        message: Optional module-provided message.
        details: Optional module-provided details fallback.
        path: Optional module-provided path.
        valid_shape: Whether raw module output had expected shape.

    Returns:
        None.
    """

    ok: bool
    code: Optional[str]
    message: Optional[str]
    details: Optional[str]
    path: Optional[str]
    valid_shape: bool


@dataclass(frozen=True, init=False)
class ValidationReportItem:
    """Validation report item produced by executor."""

    code: str
    message: str
    path: str
    rule_id: Optional[str]
    module_id: str
    severity: ValidationSeverity
    severity_hint: Optional[str] = None

    def __init__(
        self,
        code: str,
        message: str,
        path: str,
        rule_id: Optional[str],
        module_id: str,
        severity: Optional[ValidationSeverity] = None,
        severity_hint: Optional[str] = None,
        DiagnosticSeverity: Optional[ValidationSeverity] = None,
    ) -> None:
        resolved = severity if severity is not None else DiagnosticSeverity
        if resolved is None:
            raise TypeError("severity is required")
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "message", message)
        object.__setattr__(self, "path", path)
        object.__setattr__(self, "rule_id", rule_id)
        object.__setattr__(self, "module_id", module_id)
        object.__setattr__(self, "severity", resolved)
        object.__setattr__(self, "severity_hint", severity_hint)

    @property
    def DiagnosticSeverity(self) -> ValidationSeverity:
        """Compatibility alias for legacy tests using DiagnosticSeverity field."""
        return self.severity


@dataclass(frozen=True)
class ValidationExecutionResult:
    """Per-item validation result."""

    items: Tuple[ValidationReportItem, ...]
    decision: ValidationDecision
    is_valid: bool


class ValidationExecutor:
    """Execute compiled validation rules for a single record."""

    def __init__(
        self,
        *,
        catalog: ExtCatalog,
        policy_bundle: Optional[PolicyBundle] = None,
        target: Optional[str] = None,
    ) -> None:
        self._catalog = catalog
        self._policy_bundle = policy_bundle
        self._target = target

    def run_one(
        self,
        *,
        plan: ValidationPlan,
        input_record: Mapping[str, object],
        artifact_profile: str,
    ) -> ValidationExecutionResult:
        """Execute validation plan for a single input record."""

        raw_items: List[ValidationReportItem] = []

        for rule in plan.rules:
            if not _rule_applies_to_mode(rule, artifact_profile):
                continue

            value = _resolve_rule_value(rule, input_record)

            try:
                module = self._catalog.get_validation_module(rule.module_id)
            except KeyError:
                raw_items.append(
                    _runtime_item(
                        code="EXEC_VALIDATION_MODULE_NOT_FOUND",
                        message=(
                            "Validation module '"
                            + rule.module_id
                            + "' was not found in catalog."
                        ),
                        path=_default_path(rule),
                        rule=rule,
                        severity="FAIL",
                        item_factory=ValidationReportItem,
                    )
                )
                continue

            try:
                result = module.call(
                    value,
                    rule.config,
                    input_record,
                    artifact_profile,
                )
            except Exception:
                raw_items.append(
                    _runtime_item(
                        code="EXEC_VALIDATION_MODULE_FAILED",
                        message=(
                            "Validation module '"
                            + rule.module_id
                            + "' failed during execution."
                        ),
                        path=_default_path(rule),
                        rule=rule,
                        severity="FAIL",
                        item_factory=ValidationReportItem,
                    )
                )
                continue

            normalized = _normalize_module_result(result, NormalizedModuleResult)
            if not normalized.valid_shape:
                raw_items.append(
                    _runtime_item(
                        code="EXEC_VALIDATION_BAD_RESULT",
                        message=(
                            "Validation module '"
                            + rule.module_id
                            + "' returned invalid result shape."
                        ),
                        path=_default_path(rule),
                        rule=rule,
                        severity="FAIL",
                        item_factory=ValidationReportItem,
                    )
                )
                continue

            if normalized.ok:
                continue

            code = rule.on_fail_code or normalized.code or "VALIDATION_FAILED"
            message = (
                rule.on_fail_message
                or normalized.message
                or normalized.details
                or ("Validation failed: " + rule.module_id)
            )
            path = normalized.path or _default_path(rule)
            raw_items.append(
                ValidationReportItem(
                    code=code,
                    message=message,
                    path=path,
                    rule_id=rule.rule_id,
                    module_id=rule.module_id,
                    severity=_normalize_rule_severity(rule.severity_hint),
                    severity_hint=rule.severity_hint,
                )
            )

        ordered_items = tuple(
            sorted(
                raw_items,
                key=lambda item: (
                    item.module_id,
                    item.rule_id or "",
                    item.path,
                    item.code,
                    item.message,
                ),
            )
        )

        if not ordered_items:
            return ValidationExecutionResult(
                items=ordered_items, decision="PASS", is_valid=True
            )

        effective_items = ordered_items
        decision = _decision_without_policies(ordered_items)

        if self._policy_bundle is not None:
            strictness = self._policy_bundle.strictness
            strictness_input = [
                Diagnostic(
                    severity=_to_diagnostic_severity(item),
                    code=item.code,
                    message=item.message,
                    path=item.path,
                )
                for item in ordered_items
            ]
            strictness_result = strictness.apply(strictness_input)
            strictness_diagnostics = strictness_result.diagnostics

            if len(strictness_diagnostics) != len(ordered_items):
                mismatch_item = ValidationReportItem(
                    code="EXEC_STRICTNESS_RESULT_LENGTH_MISMATCH",
                    message="Strictness diagnostics length mismatch, policy result ignored.",
                    path="$",
                    rule_id=None,
                    module_id="strictness",
                    severity="FAIL",
                    severity_hint=None,
                )
                effective_items = tuple(list(ordered_items) + [mismatch_item])
                decision = _decision_without_policies(effective_items)
                return ValidationExecutionResult(
                    items=effective_items,
                    decision=decision,
                    is_valid=decision != "FAIL",
                )

            effective_items = tuple(
                ValidationReportItem(
                    code=item.code,
                    message=item.message,
                    path=item.path,
                    rule_id=item.rule_id,
                    module_id=item.module_id,
                    severity=_from_strictness_diagnostic(
                        severity=diag.severity,
                        drop_invalid=bool(
                            getattr(strictness_result, "drop_invalid", False)
                        ),
                    ),
                    severity_hint=item.severity_hint,
                )
                for item, diag in zip(ordered_items, strictness_diagnostics)
            )
            decision = _decision_from_strictness(strictness_result, effective_items)

        return ValidationExecutionResult(
            items=effective_items,
            decision=decision,
            is_valid=decision != "FAIL",
        )
