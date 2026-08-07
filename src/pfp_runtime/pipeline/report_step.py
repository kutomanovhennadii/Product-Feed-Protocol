"""Final pipeline-run assembly: RunReport(ctx) -> ExecutionReport."""

from __future__ import annotations

from time import perf_counter
from typing import Tuple

from pfp_core.contracts.produced_artifact import ProducedArtifact
from pfp_runtime.pipeline.execution_report import ExecutionReport
from pfp_runtime.pipeline.run_report import RunReport
from pfp_utils.diagnostics import DiagnosticSeverity
from pfp_utils.diagnostics.diagnostic_sanitizer import (
    sanitize_diagnostic,
    sanitize_validation_report,
)
from pfp_utils.diagnostics.validation_report import ValidationReport
from pfp_utils.sanitization import sanitize_text


def report_step(ctx: RunReport) -> ExecutionReport:
    """Finalize pipeline run into a single execution report.

    Args:
        ctx: Mutable run context accumulated by the orchestrator.

    Returns:
        ExecutionReport with sanitized diagnostics, finalized usage, and timings.
    """
    is_failed = bool(ctx.failed_step)

    if ctx.validation_report is not None:
        safe_report = sanitize_validation_report(ctx.validation_report)
    else:
        safe_report = ValidationReport(target=None, artifact_profile=None)

    for diagnostic in ctx.ingestion_diagnostics:
        safe_report.add(sanitize_diagnostic(diagnostic))

    if is_failed:
        ctx.collector.inc_error()
    else:
        if ctx.artifact is not None:
            ctx.collector.inc_artifacts(1)
        ctx.collector.inc_processed(ctx.collector.build().input_items_count)

    for diagnostic in safe_report.diagnostics:
        ctx.collector.inc_diagnostic(
            str(DiagnosticSeverity.normalize(diagnostic.severity))
        )

    ctx.timings["total"] = perf_counter() - ctx.started_at

    artifacts: Tuple[ProducedArtifact, ...] = (
        (ctx.artifact,) if ctx.artifact is not None else ()
    )
    return ExecutionReport(
        status="FAILED" if is_failed else "SUCCESS",
        failed_step=ctx.failed_step,
        reason_code=ctx.reason_code,
        message=(
            sanitize_text(ctx.message)
            if is_failed
            else "Pipeline completed successfully"
        ),
        validation_report=safe_report,
        artifacts=artifacts,
        timings=ctx.timings,
        usage=ctx.collector.build(),
        run_id=ctx.run_id,
        correlation_id=ctx.correlation_id,
        error_type=ctx.error_type,
    )


__all__ = ["report_step"]
