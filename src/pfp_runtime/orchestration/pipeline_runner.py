"""Runtime orchestrator for ingestion -> core API -> publish flow."""

from __future__ import annotations

import logging
from time import perf_counter
from typing import Any, Dict, Mapping, Optional

from pfp_core.artifact_production.artifact_producer import ArtifactProducer
from pfp_runtime.manifest.pipeline_manifest import CoreManifest, PipelineManifest
from pfp_runtime.pipeline.core_guard import (
    CoreContractError,
    CoreError,
    core_step,
    resolve_core_reason_code,
)
from pfp_runtime.pipeline.execution_report import ExecutionReport
from pfp_runtime.pipeline.ingestion_guard import (
    IngestionExtractCallError,
    IngestionExtractIterationError,
    ingestion_step,
    resolve_ingestion_reason_code,
)
from pfp_runtime.pipeline.log_filters import log_validation_diagnostics
from pfp_runtime.pipeline.observability_wrappers import (
    emit_step_telemetry,
    record_timing,
)
from pfp_runtime.pipeline.publish_guard import (
    PublishError,
    publish_step,
    resolve_publish_reason_code,
)
from pfp_runtime.pipeline.report_step import report_step
from pfp_runtime.pipeline.run_report import RunReport
from pfp_utils.diagnostics.diagnostic_models import DiagnosticSeverity
from pfp_utils.diagnostics.validation_report import ValidationReport
from pfp_utils.logging import LogContext, LogPipeline


class PipelineRunner:
    """External orchestrator for manifest -> ingestion -> core -> publish -> report.

    Args:
        manifest: Validated runtime manifest used for the full pipeline execution.

    Returns:
        PipelineRunner instance bound to the supplied manifest.
    """

    def __init__(self, manifest: PipelineManifest) -> None:
        """Create a pipeline runner with a validated manifest.

        Args:
            manifest: Validated PipelineManifest from the init pipeline.

        Raises:
            ValueError: If manifest contract invariants are violated.
        """
        if manifest is None:
            raise ValueError("manifest is required")
        if manifest.ingestion is None:
            raise ValueError("manifest.ingestion is required")
        if manifest.ingestion.connector is None:
            raise ValueError("manifest.ingestion.connector is required")
        if manifest.core is None:
            raise ValueError("manifest.core is required")
        if not isinstance(manifest.core.producer, ArtifactProducer):
            raise ValueError("core.producer is required")
        if manifest.publish is None:
            raise ValueError("manifest.publish is required")
        if manifest.publish.publisher is None:
            raise ValueError("manifest.publish.publisher is required")
        if manifest.observability is None:
            raise ValueError("manifest.observability is required")
        self._log_pipeline: LogPipeline = manifest.observability.log_pipeline
        self._manifest = manifest

    def run(
        self,
        input_data: bytes,
    ) -> ExecutionReport:
        """Execute the full runtime pipeline and return a machine-readable report.

        Args:
            input_data: Raw input payload forwarded to the ingestion connector.

        Returns:
            ExecutionReport describing the final runtime outcome.
        """
        runner_manifest = self._manifest
        observability = runner_manifest.observability
        telemetry = observability.telemetry_handler
        ctx = RunReport(
            started_at=perf_counter(),
            collector=observability.usage_collector,
            timings={},
            run_id=(
                runner_manifest.run_context.run_id
                if runner_manifest.run_context
                else None
            ),
            correlation_id=(
                runner_manifest.run_context.correlation_id
                if runner_manifest.run_context
                else None
            ),
        )
        ctx.collector.reset()
        metric_labels = self._build_metric_labels(runner_manifest)

        try:
            um_items, ctx.ingestion_diagnostics = record_timing(
                ctx.timings,
                "ingestion_extract",
                lambda: emit_step_telemetry(
                    telemetry,
                    metric_labels,
                    "ingestion_extract",
                    lambda: ingestion_step(
                        runner_manifest.ingestion.connector,
                        input_data,
                    ),
                ),
            )
        except IngestionExtractCallError as exc:
            self._log(logging.ERROR, "Ingestion extract failed", exc_info=exc)
            return report_step(
                ctx.fail(
                    failed_step="INGESTION_EXTRACT",
                    reason_code=resolve_ingestion_reason_code(exc.original_exc),
                    exc=exc,
                )
            )

        um_items = ctx.collector.attach_input_counter(um_items)

        generated_at = runner_manifest.core.generated_at
        if generated_at is None and runner_manifest.run_context is not None:
            generated_at = runner_manifest.run_context.generated_at

        try:
            with LogContext(
                target=_resolve_target_label(runner_manifest.core),
            ):
                core_result = record_timing(
                    ctx.timings,
                    "core",
                    lambda: emit_step_telemetry(
                        telemetry,
                        metric_labels,
                        "core",
                        lambda: core_step(
                            producer=runner_manifest.core.producer,
                            um_items=um_items,
                            generated_at=generated_at,
                        ),
                    ),
                )
        except IngestionExtractIterationError as exc:
            self._log(logging.ERROR, "Ingestion iteration failed", exc_info=exc)
            return report_step(
                ctx.fail(
                    failed_step="INGESTION_EXTRACT",
                    reason_code=resolve_ingestion_reason_code(exc.original_exc),
                    exc=exc,
                )
            )
        except CoreError as exc:
            failed_step = (
                "CORE_BUILD" if isinstance(exc, CoreContractError) else "INTERNAL"
            )
            log_message = (
                "Core contract error"
                if isinstance(exc, CoreContractError)
                else "Core execution failed"
            )
            self._log(logging.ERROR, log_message, exc_info=exc)
            return report_step(
                ctx.fail(
                    failed_step=failed_step,
                    reason_code=resolve_core_reason_code(exc.original_exc),
                    exc=exc,
                )
            )

        validation_report = core_result.validation_report
        ctx.validation_report = log_validation_diagnostics(
            validation_report,
            logger=self._log_pipeline,
            metric_labels=metric_labels,
            run_id=ctx.run_id,
            correlation_id=ctx.correlation_id,
        )

        if runner_manifest.core.fail_on_error_diagnostics and _has_error_diagnostics(
            ctx.validation_report
        ):
            ctx.failed_step = "CORE_BUILD"
            ctx.reason_code = "CORE.VALIDATION_FAILED"
            ctx.message = "Validation report contains ERROR diagnostics"
            return report_step(ctx)

        try:
            ctx.artifact = record_timing(
                ctx.timings,
                "publish",
                lambda: emit_step_telemetry(
                    telemetry,
                    metric_labels,
                    "publish",
                    lambda: publish_step(
                        core_result.artifacts[0],
                        runner_manifest.publish,
                    ),
                ),
            )
        except PublishError as exc:
            self._log(logging.ERROR, "Publish failed", exc_info=exc)
            return report_step(
                ctx.fail(
                    failed_step="PUBLISH",
                    reason_code=resolve_publish_reason_code(exc.original_exc),
                    exc=exc,
                )
            )

        return report_step(ctx)

    def _build_metric_labels(
        self,
        manifest: PipelineManifest,
    ) -> Dict[str, str]:
        """Build stable metric labels for runtime telemetry.

        Args:
            manifest: Normalized runner manifest.

        Returns:
            Dict with low-cardinality metric labels.
        """
        return {
            "target": _resolve_target_label(manifest.core),
            "mode": "runtime",
            "stage": "total",
        }

    def _log(
        self,
        level: int,
        message: str,
        *args: Any,
        exc_info: Optional[Exception] = None,
        extra: Optional[Mapping[str, Any]] = None,
    ) -> None:
        """Emit a runtime log through the manifest-owned LogPipeline."""
        self._log_pipeline.log_process(
            level,
            __name__,
            message,
            *args,
            exc_info=exc_info,
            extra=extra,
        )


def _has_error_diagnostics(report: ValidationReport) -> bool:
    """Check whether a validation report contains any ERROR diagnostics.

    Args:
        report: Validation report.

    Returns:
        True if report contains at least one ERROR diagnostic.
    """
    for diagnostic in report.diagnostics:
        if (
            DiagnosticSeverity.normalize(diagnostic.severity)
            is DiagnosticSeverity.ERROR
        ):
            return True
    return False


def _resolve_target_label(core_manifest: CoreManifest) -> str:
    """Resolve a stable target label for logs and metrics."""
    return core_manifest.producer.target_label
