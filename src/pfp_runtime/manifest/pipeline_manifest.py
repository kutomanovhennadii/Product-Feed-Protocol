"""Runtime pipeline manifest contracts for init-phase assembly."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Mapping, Optional

from pfp_core.artifact_production.artifact_producer import ArtifactProducer
from pfp_runtime.connectors.contracts.source_connector import SourceConnector
from pfp_runtime.publishing.contracts import Publisher
from pfp_utils.diagnostics import FeedUsageCollector
from pfp_utils.logging import LogPipeline
from pfp_utils.telemetry import NoOpTelemetryHandler, TelemetryHandler


@dataclass(frozen=True)
class ConnectorManifest:
    """Connector runtime input for one pipeline run.

    Args:
        connector: Ready-to-use source connector for the current run.
        raw_input: Optional raw input payload retained for runtime consumers.

    Returns:
        ConnectorManifest: Frozen connector section for one pipeline run.
    """

    connector: SourceConnector
    raw_input: Any = None


@dataclass(frozen=True)
class CoreManifest:
    """Core execution runtime input for one pipeline run.

    Args:
        producer: Ready-to-use artifact producer for the current run.
        generated_at: Optional timestamp describing manifest assembly time.
        fail_on_error_diagnostics: Whether runtime should fail on error diagnostics.

    Returns:
        CoreManifest: Frozen core execution section for one pipeline run.
    """

    producer: ArtifactProducer
    generated_at: Optional[datetime] = None
    fail_on_error_diagnostics: bool = False


@dataclass(frozen=True)
class PublishManifest:
    """Publishing runtime input with ready-to-use publisher instance.

    Args:
        publisher: Ready-to-use publisher selected during init-phase assembly.

    Returns:
        PublishManifest: Frozen publishing section for one pipeline run.
    """

    publisher: Publisher


@dataclass(frozen=True)
class RunContext:
    """Optional run identifiers and metadata.

    Args:
        run_id: Optional runtime identifier for the current run.
        correlation_id: Optional correlation identifier propagated across logs.
        generated_at: Optional timestamp associated with the current run.

    Returns:
        RunContext: Frozen runtime metadata container.
    """

    run_id: Optional[str] = None
    correlation_id: Optional[str] = None
    generated_at: Optional[datetime] = None


@dataclass(frozen=True)
class ObservabilityManifest:
    """Runtime observability configuration with ready-to-use instruments.

    Args:
        log_pipeline: Installed log pipeline prepared during init-phase assembly.
        telemetry_handler: Ready-to-use telemetry instrument for runtime metrics.
        usage_collector: Ready-to-use accounting instrument for feed usage.
        telemetry_enabled: Whether telemetry is active for the assembled runtime.
        telemetry_provider: Resolved telemetry provider name.
        labels: Informational telemetry labels retained in manifest data.
        emit_execution_report: Whether runtime should emit execution reports.
        include_diagnostics: Whether runtime should include diagnostics in reports.

    Returns:
        ObservabilityManifest: Frozen observability section with ready instruments.
    """

    log_pipeline: LogPipeline
    telemetry_handler: TelemetryHandler = field(default_factory=NoOpTelemetryHandler)
    usage_collector: FeedUsageCollector = field(default_factory=FeedUsageCollector)
    telemetry_enabled: bool = False
    telemetry_provider: str = "none"
    labels: Mapping[str, str] = field(default_factory=dict)
    emit_execution_report: bool = True
    include_diagnostics: bool = True


@dataclass(frozen=True)
class PipelineManifest:
    """Validated runtime manifest as a single output type of init pipeline.

    Args:
        ingestion: Connector section assembled for the current pipeline.
        core: Core execution section assembled for the current pipeline.
        publish: Publishing section assembled for the current pipeline.
        observability: Observability section with ready instruments.
        run_context: Optional run metadata.

    Returns:
        PipelineManifest: Frozen single output type of init-phase assembly.
    """

    ingestion: ConnectorManifest
    core: CoreManifest
    publish: PublishManifest
    observability: ObservabilityManifest
    run_context: Optional[RunContext] = None


class ManifestBuildError(ValueError):
    """Raised when manifest assembly fails at any stage.

    Args:
        *args: Standard exception arguments describing the assembly failure.

    Returns:
        ManifestBuildError: Exception describing manifest assembly failure.
    """


__all__: List[str] = [
    "ConnectorManifest",
    "CoreManifest",
    "ManifestBuildError",
    "ObservabilityManifest",
    "PipelineManifest",
    "PublishManifest",
    "RunContext",
]
