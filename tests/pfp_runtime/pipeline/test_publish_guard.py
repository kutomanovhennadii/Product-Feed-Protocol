"""Tests for the publish_guard module."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import pytest

from pfp_core.contracts.artifact_metadata import ArtifactMetadata
from pfp_core.contracts.produced_artifact import ProducedArtifact
from pfp_runtime.manifest.pipeline_manifest import PublishManifest
from pfp_runtime.pipeline.publish_guard import (
    PublishError,
    guard_publish,
    publish_step,
    resolve_publish_reason_code,
)
from pfp_runtime.publishing.contracts.publisher_contract import Publisher


class _PublisherStub(Publisher):
    """Test double exposing publish for publish_step scenarios."""

    def __init__(
        self,
        result: Optional[Any] = None,
        error: Optional[Exception] = None,
    ) -> None:
        """Configure publisher success or failure behavior.

        Args:
            result: Value returned by publish on success.
            error: Optional exception raised by publish.

        Returns:
            None.
        """
        self._result = result
        self._error = error
        self.received_artifact: Optional[Any] = None

    def publish(self, artifact: Any) -> Any:
        """Return configured result or raise configured publish error.

        Args:
            artifact: Artifact forwarded by publish_step.

        Returns:
            Configured publish result.

        Raises:
            Exception: Configured publish error for failure-path tests.
        """
        self.received_artifact = artifact
        if self._error is not None:
            raise self._error
        return self._result


def test_guard_publish_returns_action_result() -> None:
    """guard_publish must return the action result when no exception is raised.

    Returns:
        None.
    """
    assert guard_publish(lambda: 42) == 42


def test_guard_publish_wraps_runtime_error_without_sanitation() -> None:
    """guard_publish must wrap runtime failures in PublishError verbatim.

    Returns:
        None.
    """
    with pytest.raises(PublishError) as exc_info:
        guard_publish(lambda: (_ for _ in ()).throw(RuntimeError("boom")))

    assert str(exc_info.value) == "boom"
    assert isinstance(exc_info.value.original_exc, RuntimeError)
    assert exc_info.value.original_exc is not exc_info.value


def test_guard_publish_re_raises_existing_publish_error() -> None:
    """guard_publish must not wrap an exception that is already PublishError.

    Returns:
        None.
    """
    original_error = PublishError("boom", original_exc=RuntimeError("boom"))

    with pytest.raises(PublishError) as exc_info:
        guard_publish(lambda: (_ for _ in ()).throw(original_error))

    assert exc_info.value is original_error


def test_publish_error_stores_message_and_original_exc() -> None:
    """Store error message and original exception reference."""
    exc = ValueError("boom")

    err = PublishError("msg", original_exc=exc)

    assert str(err) == "msg"
    assert err.original_exc is exc


def test_publish_error_has_no_published_artifacts_attribute() -> None:
    """PublishError no longer exposes published_artifacts."""
    err = PublishError("msg", original_exc=RuntimeError("boom"))

    assert not hasattr(err, "published_artifacts")


def test_publish_error_requires_original_exc_keyword_only() -> None:
    """Reject positional passing for keyword-only original_exc argument."""
    with pytest.raises(TypeError):
        PublishError("m", RuntimeError("boom"))  # type: ignore[misc]


def test_guard_publish_wraps_timeout_error() -> None:
    """guard_publish must wrap TimeoutError and preserve it as original_exc.

    Returns:
        None.
    """
    with pytest.raises(PublishError) as exc_info:
        guard_publish(lambda: (_ for _ in ()).throw(TimeoutError("slow")))

    assert str(exc_info.value) == "slow"
    assert isinstance(exc_info.value.original_exc, TimeoutError)


def _make_artifact() -> ProducedArtifact:
    """Build a minimal produced artifact for publish-step tests.

    Returns:
        ProducedArtifact instance with minimal valid metadata.
    """
    return ProducedArtifact(
        payload=(b"chunk",),
        metadata=ArtifactMetadata(
            target="target",
            schema_version="1.0",
            generated_at=datetime(2026, 4, 29, tzinfo=timezone.utc),
            content_type="application/octet-stream",
            encoding="utf-8",
        ),
    )


def test_publish_step_happy_path() -> None:
    """publish_step must call publisher.publish and return its artifact.

    Returns:
        None.
    """
    artifact = _make_artifact()
    publisher = _PublisherStub(result=artifact)
    publish = PublishManifest(publisher=publisher)

    result = publish_step(artifact, publish)

    assert result is artifact
    assert publisher.received_artifact is artifact


def test_publish_step_failure_wraps_in_publish_error() -> None:
    """publish_step must wrap publisher failures in PublishError.

    Returns:
        None.
    """
    artifact = _make_artifact()
    publisher = _PublisherStub(error=RuntimeError("boom"))
    publish = PublishManifest(publisher=publisher)

    with pytest.raises(PublishError) as exc_info:
        publish_step(artifact, publish)

    assert str(exc_info.value) == "boom"
    assert isinstance(exc_info.value.original_exc, RuntimeError)
    assert exc_info.value.__cause__ is exc_info.value.original_exc


def test_resolve_publish_reason_code_returns_timeout_code() -> None:
    """TimeoutError must map to the publish timeout reason code.

    Returns:
        None.
    """
    assert resolve_publish_reason_code(TimeoutError()) == "PUBLISH.TIMEOUT"


def test_resolve_publish_reason_code_returns_generic_runtime_code() -> None:
    """RuntimeError must map to the generic publish error code.

    Returns:
        None.
    """
    assert resolve_publish_reason_code(RuntimeError()) == "PUBLISH.ERROR"


def test_resolve_publish_reason_code_falls_back_for_oserror() -> None:
    """Unhandled exception types must fall back to the generic publish code.

    Returns:
        None.
    """
    assert resolve_publish_reason_code(OSError()) == "PUBLISH.ERROR"
