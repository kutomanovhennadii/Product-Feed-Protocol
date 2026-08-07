"""Execution report models for pipeline orchestration outcomes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional, Tuple

from pfp_core.contracts.produced_artifact import ProducedArtifact
from pfp_utils.diagnostics import FeedUsage
from pfp_utils.diagnostics.validation_report import ValidationReport


@dataclass
class ExecutionReport:
    """Machine-readable run report for monitoring and retries.

    Args:
        status: Final execution status token.
        failed_step: Pipeline step where execution failed, or empty on success.
        reason_code: Stable machine-readable failure code.
        message: Human-readable outcome summary.
        validation_report: Sanitized validation report for the run.
        artifacts: Published artifacts produced by the pipeline.
        timings: Execution timings grouped by pipeline step.
        usage: Typed feed usage snapshot for the run.
        run_id: Optional runtime run identifier.
        correlation_id: Optional cross-system correlation identifier.
        error_type: Optional exception class name for failed runs.

    Returns:
        ExecutionReport instance containing the normalized runtime outcome.
    """

    status: str
    failed_step: str
    reason_code: str
    message: str
    validation_report: ValidationReport
    artifacts: Tuple[ProducedArtifact, ...] = ()
    timings: Dict[str, float] = field(default_factory=dict)
    usage: FeedUsage = field(default_factory=FeedUsage)
    run_id: Optional[str] = None
    correlation_id: Optional[str] = None
    error_type: Optional[str] = None

    @property
    def counters(self) -> Mapping[str, object]:
        """Return a legacy counters view derived from typed usage data.

        Args:
            None.

        Returns:
            Mapping with the historical counters keys expected by legacy readers.
        """
        return {
            "input_items_count": self.usage.input_items_count,
            "artifacts_count": self.usage.artifacts_count,
            "diagnostics_count_by_severity": dict(
                self.usage.diagnostics_count_by_severity
            ),
            "processed": self.usage.processed,
            "dropped": self.usage.dropped,
            "error": self.usage.errors,
        }


__all__: List[str] = ["ExecutionReport"]
