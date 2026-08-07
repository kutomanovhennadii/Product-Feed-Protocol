"""Publisher call guard and reason-code classifier.

Wraps the publisher invocation so downstream consumers observe a
PublishError with the original exception attached, regardless of the
concrete failure type raised by Publisher.publish. Pairs with a
classifier that maps caught exceptions to stable reason codes used
in ExecutionReport.

Secret sanitation is NOT performed here: it is handled centrally by
SecretRedactionFilter (for logs) and report_step (for the execution
report). This file is a structural boundary, not a sanitizer.
"""

from __future__ import annotations

from typing import Callable, TypeVar

from pfp_core.contracts.produced_artifact import ProducedArtifact
from pfp_runtime.manifest.pipeline_manifest import PublishManifest

T = TypeVar("T")


class PublishError(RuntimeError):
    """Raised when artifact publishing fails."""

    def __init__(
        self,
        message: str,
        *,
        original_exc: Exception,
    ) -> None:
        """Initialize publish failure with the original underlying exception.

        Args:
            message: Human-readable failure message propagated to callers.
            original_exc: Original exception raised by the publisher.

        Returns:
            None.
        """
        super().__init__(message)
        self.original_exc = original_exc


def guard_publish(action: Callable[[], T]) -> T:
    """Run publisher action, re-raising any failure as PublishError.

    Args:
        action: Zero-arg callable that invokes Publisher.publish.

    Returns:
        Whatever action() returns on success.

    Raises:
        PublishError: If action() raises any exception. original_exc is
            populated; message is str(exc) without sanitation.
    """
    try:
        return action()
    except PublishError:
        raise
    except Exception as exc:
        raise PublishError(str(exc), original_exc=exc) from exc


def publish_step(
    artifact: ProducedArtifact,
    publish: PublishManifest,
) -> ProducedArtifact:
    """Publish a single produced artifact through the configured publisher.

    Args:
        artifact: Produced artifact passed to the runtime publisher.
        publish: Publish manifest with a ready-to-use publisher instance.

    Returns:
        Produced artifact returned by publisher.publish.

    Raises:
        PublishError: If publisher.publish raises any exception.
    """
    publisher = publish.publisher
    return guard_publish(lambda: publisher.publish(artifact))


def resolve_publish_reason_code(exc: Exception) -> str:
    """Map publish failure type to deterministic reason code.

    Args:
        exc: Exception caught from publisher invocation.

    Returns:
        Stable reason code string used in ExecutionReport.
    """
    if isinstance(exc, TimeoutError):
        return "PUBLISH.TIMEOUT"
    return "PUBLISH.ERROR"


__all__ = [
    "PublishError",
    "guard_publish",
    "publish_step",
    "resolve_publish_reason_code",
]
