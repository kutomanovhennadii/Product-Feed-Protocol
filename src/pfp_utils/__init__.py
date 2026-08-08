"""PFP shared utilities: diagnostics, logging, telemetry, security, sanitization."""

from typing import List

from pfp_utils.diagnostics import (
    Diagnostic,
    DiagnosticSeverity,
    FeedUsage,
    FeedUsageCollector,
    ValidationReport,
)
from pfp_utils.diagnostics.diagnostic_sanitizer import (
    sanitize_diagnostic,
    sanitize_validation_report,
)
from pfp_utils.logging import (
    LogContext,
    LogPipeline,
    build_log_pipeline,
    get_context,
    profile_stage,
)
from pfp_utils.sanitization import sanitize_mapping, sanitize_text
from pfp_utils.security import (
    ResolvedSecret,
    SecretRef,
    SecretResolutionError,
    resolve_secret,
)
from pfp_utils.telemetry import (
    ConsoleTelemetryHandler,
    NoOpTelemetryHandler,
    PrometheusTelemetryHandler,
    TelemetryHandler,
    build_metrics_router,
    create_telemetry_handler,
)

__all__: List[str] = [
    "ConsoleTelemetryHandler",
    "Diagnostic",
    "DiagnosticSeverity",
    "FeedUsage",
    "FeedUsageCollector",
    "LogContext",
    "LogPipeline",
    "NoOpTelemetryHandler",
    "PrometheusTelemetryHandler",
    "ResolvedSecret",
    "SecretRef",
    "SecretResolutionError",
    "TelemetryHandler",
    "ValidationReport",
    "build_metrics_router",
    "build_log_pipeline",
    "create_telemetry_handler",
    "get_context",
    "profile_stage",
    "resolve_secret",
    "sanitize_diagnostic",
    "sanitize_mapping",
    "sanitize_text",
    "sanitize_validation_report",
]
