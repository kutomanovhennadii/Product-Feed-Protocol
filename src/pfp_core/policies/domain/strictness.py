from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, List, Mapping, Optional, Sequence, Union

from pfp_core.policies.utils.policy_utils import (
    _require_key,
    _require_mapping,
    _validate_keys,
)
from pfp_utils.diagnostics.diagnostic_models import Diagnostic, DiagnosticSeverity
from pfp_utils.telemetry import TelemetryHandler


class StrictnessMode(Enum):
    """Strictness strategy — determines reaction to validation errors."""

    FAIL_ON_ERROR = "fail_on_error"
    DROP_INVALID = "drop_invalid"
    WARN_ONLY = "warn_only"

    @classmethod
    def normalize(cls, value: Union["StrictnessMode", str]) -> "StrictnessMode":
        if isinstance(value, StrictnessMode):
            return value
        text = str(value).strip().lower()
        for member in cls:
            if member.value == text:
                return member
        raise ValueError(f"Unknown strictness strategy '{value}'")


@dataclass(frozen=True)
class StrictnessConfig:
    strategy: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "StrictnessConfig":
        data = _require_mapping(data, "core.strictness")
        _validate_keys(data, {"strategy"}, "core.strictness")
        raw_strategy = _require_key(data, "strategy", "core.strictness")
        if not isinstance(raw_strategy, str):
            raise ValueError("core.strictness.strategy must be a string")
        return cls(strategy=StrictnessMode.normalize(raw_strategy).value)


@dataclass(frozen=True)
class StrictnessDecision:
    diagnostics: List[Diagnostic]
    should_fail: bool
    drop_invalid: bool


def _has_errors(diagnostics: Sequence[Diagnostic]) -> bool:
    return any(
        DiagnosticSeverity.normalize(diag.severity) is DiagnosticSeverity.ERROR
        for diag in diagnostics
    )


def _with_severity(
    diag: Diagnostic, DiagnosticSeverity: DiagnosticSeverity
) -> Diagnostic:
    return Diagnostic(
        severity=DiagnosticSeverity,
        code=diag.code,
        message=diag.message,
        path=diag.path,
        item_ref=diag.item_ref,
        metadata=diag.metadata,
    )


def _downgrade_errors(diagnostics: Sequence[Diagnostic]) -> List[Diagnostic]:
    updated: List[Diagnostic] = []
    for diag in diagnostics:
        if DiagnosticSeverity.normalize(diag.severity) is DiagnosticSeverity.ERROR:
            updated.append(_with_severity(diag, DiagnosticSeverity.WARN))
        else:
            updated.append(diag)
    return updated


def _apply_fail_on_error(diagnostics: Sequence[Diagnostic]) -> StrictnessDecision:
    return StrictnessDecision(
        diagnostics=list(diagnostics),
        should_fail=_has_errors(diagnostics),
        drop_invalid=False,
    )


def _apply_drop_invalid(diagnostics: Sequence[Diagnostic]) -> StrictnessDecision:
    return StrictnessDecision(
        diagnostics=list(diagnostics),
        should_fail=False,
        drop_invalid=_has_errors(diagnostics),
    )


def _apply_warn_only(diagnostics: Sequence[Diagnostic]) -> StrictnessDecision:
    return StrictnessDecision(
        diagnostics=_downgrade_errors(diagnostics),
        should_fail=False,
        drop_invalid=False,
    )


class StrictnessPolicy:
    def __init__(self, strategy: Union[StrictnessMode, str]) -> None:
        self.strategy = StrictnessMode.normalize(strategy).value

    def apply(
        self,
        diagnostics: Iterable[Diagnostic],
        *,
        telemetry: Optional[TelemetryHandler] = None,
    ) -> StrictnessDecision:
        diag_list = list(diagnostics)
        if self.strategy == StrictnessMode.FAIL_ON_ERROR.value:
            decision = _apply_fail_on_error(diag_list)
        elif self.strategy == StrictnessMode.DROP_INVALID.value:
            decision = _apply_drop_invalid(diag_list)
        elif self.strategy == StrictnessMode.WARN_ONLY.value:
            decision = _apply_warn_only(diag_list)
        else:
            raise ValueError("Unknown strictness strategy: {0}".format(self.strategy))

        if telemetry:
            outcome = "pass"
            if decision.should_fail:
                outcome = "fail"
            elif decision.drop_invalid:
                outcome = "drop"

            telemetry.inc(
                "strictness_decision",
                1.0,
                labels={
                    "strategy": self.strategy,
                    "outcome": outcome,
                },
            )

        return decision
