"""Core-step guard and reason-code classifier.

Wraps producer invocation so orchestrators observe stable core-origin
exceptions with original causes attached. Ingestion-origin failures are
re-raised unchanged to preserve the correct failed-step attribution in
PipelineRunner.run.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Iterable, Optional, TypeVar

from pfp_core.contracts.artifact_production_result import ArtifactProductionResult
from pfp_runtime.pipeline.ingestion_guard import IngestionError

T = TypeVar("T")


class CoreError(RuntimeError):
    """Base exception for core-step failures."""

    def __init__(
        self,
        message: str,
        *,
        original_exc: Exception,
    ) -> None:
        """Initialize core failure with its original underlying exception.

        Args:
            message: Human-readable failure message propagated to callers.
            original_exc: Original exception raised by the producer path.

        Returns:
            None.
        """
        super().__init__(message)
        self.original_exc = original_exc


class CoreContractError(CoreError):
    """Raised when producer invocation violates the core contract."""


def guard_core(action: Callable[[], T]) -> T:
    """Run core action and normalize core-origin failures.

    Args:
        action: Zero-argument callable that invokes the producer.

    Returns:
        Whatever action() returns on success.

    Raises:
        IngestionError: Re-raised unchanged so ingestion attribution is preserved.
        CoreContractError: If action() raises ValueError.
        CoreError: If action() raises any other non-core exception.
    """
    try:
        return action()
    except (CoreError, IngestionError):
        raise
    except ValueError as exc:
        raise CoreContractError(str(exc), original_exc=exc) from exc
    except Exception as exc:
        raise CoreError(str(exc), original_exc=exc) from exc


def core_step(
    producer: Any,
    um_items: Iterable[Any],
    generated_at: Optional[datetime],
) -> ArtifactProductionResult:
    """Invoke producer.produce_artifacts through the core guard.

    Args:
        producer: Artifact producer exposing produce_artifacts.
        um_items: Unified-model items iterable consumed by the producer.
        generated_at: Optional explicit timestamp passed to the producer.

    Returns:
        Artifact production result returned by the producer.

    Raises:
        IngestionError: Re-raised unchanged if lazy ingestion iteration fails.
        CoreContractError: If the producer raises ValueError.
        CoreError: If the producer raises any other exception.
    """
    return guard_core(
        lambda: producer.produce_artifacts(
            um_items,
            generated_at=generated_at,
        )
    )


def resolve_core_reason_code(exc: Exception) -> str:
    """Map core failure type to deterministic reason code.

    Args:
        exc: Exception caught from the producer invocation.

    Returns:
        Stable reason code string used in ExecutionReport.
    """
    if isinstance(exc, ValueError):
        return "CORE.CONTRACT_ERROR"
    return "INTERNAL.ERROR"


__all__ = [
    "CoreContractError",
    "CoreError",
    "core_step",
    "guard_core",
    "resolve_core_reason_code",
]
