"""Mutable pipeline run context accumulated across step functions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from pfp_core.contracts.produced_artifact import ProducedArtifact
from pfp_utils.diagnostics import Diagnostic, FeedUsageCollector, ValidationReport


@dataclass
class RunReport:
    """Accumulate pipeline-run state before final report assembly.

    Attributes:
        started_at: perf_counter timestamp captured at run start.
        collector: Mutable usage collector for the current run.
        timings: Per-step elapsed durations accumulated by the runner.
        run_id: Optional runtime run identifier.
        correlation_id: Optional cross-system correlation identifier.
        ingestion_diagnostics: Diagnostics emitted by ingestion.
        validation_report: Raw validation report emitted by core.
        artifact: Published artifact produced by the run.
        failed_step: Failed pipeline step token, or empty on success.
        reason_code: Stable machine-readable failure code.
        message: Human-readable failure message.
        error_type: Optional exception class name for failed runs.
    """

    started_at: float
    collector: FeedUsageCollector
    timings: Dict[str, float] = field(default_factory=dict)
    run_id: Optional[str] = None
    correlation_id: Optional[str] = None
    ingestion_diagnostics: Tuple[Diagnostic, ...] = ()
    validation_report: Optional[ValidationReport] = None
    artifact: Optional[ProducedArtifact] = None
    failed_step: str = ""
    reason_code: str = ""
    message: str = ""
    error_type: Optional[str] = None

    def fail(
        self,
        *,
        failed_step: str,
        reason_code: str,
        exc: Exception,
    ) -> "RunReport":
        """Populate failure fields from ``exc`` and return ``self``.

        Args:
            failed_step: Failed pipeline step token.
            reason_code: Stable machine-readable failure code.
            exc: Wrapper or original exception for the failure path.

        Returns:
            The same RunReport instance for fluent failure handling.
        """
        original = getattr(exc, "original_exc", exc)
        self.failed_step = failed_step
        self.reason_code = reason_code
        self.message = str(original)
        self.error_type = type(original).__name__
        return self


__all__ = ["RunReport"]
