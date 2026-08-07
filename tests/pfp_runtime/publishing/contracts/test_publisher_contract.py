"""Contract tests for publisher_contract module (v2 stack)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List

import pytest

from pfp_core.contracts.artifact_metadata import ArtifactMetadata
from pfp_core.contracts.produced_artifact import ProducedArtifact
from pfp_runtime.publishing.archivers.archiver_contract import ArchiveResult
from pfp_runtime.publishing.clients.client_contract import DeliveryResult
from pfp_runtime.publishing.contracts.publish_metadata import PublishMetadata
from pfp_runtime.publishing.contracts.publisher_contract import Publisher

# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------


class _StubArchiver:
    """Minimal archiver stub that records calls and returns a fixed ArchiveResult."""

    def __init__(self) -> None:
        self.opened = False
        self.chunks: List[bytes] = []
        self.finalized = False

    def open(self) -> None:
        self.opened = True

    def write_chunk(self, chunk: bytes) -> None:
        self.chunks.append(chunk)

    def finalize(self) -> ArchiveResult:
        self.finalized = True
        return ArchiveResult(skipped=False, location="s3://test/key")


class _StubClient:
    """Minimal delivery client stub that records calls and returns a fixed DeliveryResult."""

    def __init__(self) -> None:
        self.opened = False
        self.chunks: List[bytes] = []
        self.finalized = False

    def open(self) -> None:
        self.opened = True

    def send_chunk(self, chunk: bytes) -> None:
        self.chunks.append(chunk)

    def finalize(self) -> DeliveryResult:
        self.finalized = True
        return DeliveryResult(skipped=False, status_code=200)


class _LogPipelineStub:
    """Minimal log pipeline stub for publisher contract tests."""

    def log_process(self, *_args: Any, **_kwargs: Any) -> None:
        return None


def _artifact(chunks: List[bytes]) -> ProducedArtifact:
    metadata = ArtifactMetadata(
        target="stripe.product",
        schema_version="1.0.0",
        generated_at=datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
        content_type="text/csv",
        encoding="utf-8",
    )
    return ProducedArtifact(payload=iter(chunks), metadata=metadata)


# ---------------------------------------------------------------------------
# Publisher.__init__()
# ---------------------------------------------------------------------------


def test_publisher_init_stores_archiver_and_client() -> None:
    """Verify Publisher.__init__ stores archiver and client as instance attributes."""
    archiver = _StubArchiver()
    client = _StubClient()
    publisher = Publisher(
        archiver=archiver,
        client=client,
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    )
    assert publisher.archiver is archiver
    assert publisher.client is client


# ---------------------------------------------------------------------------
# Publisher.publish() — call-order and streaming
# ---------------------------------------------------------------------------


def test_publisher_publish_calls_open_before_chunks() -> None:
    """Verify archiver.open() and client.open() are called before the chunk loop."""
    archiver = _StubArchiver()
    client = _StubClient()
    Publisher(
        archiver=archiver,
        client=client,
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    ).publish(_artifact([b"x"]))
    assert archiver.opened is True
    assert client.opened is True


def test_publisher_publish_forwards_chunks_to_archiver() -> None:
    """Verify write_chunk is called in order for each payload chunk."""
    archiver = _StubArchiver()
    client = _StubClient()
    Publisher(
        archiver=archiver,
        client=client,
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    ).publish(_artifact([b"a", b"b"]))
    assert archiver.chunks == [b"a", b"b"]


def test_publisher_publish_forwards_chunks_to_client() -> None:
    """Verify send_chunk is called in order with the same chunks as write_chunk."""
    archiver = _StubArchiver()
    client = _StubClient()
    Publisher(
        archiver=archiver,
        client=client,
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    ).publish(_artifact([b"a", b"b"]))
    assert client.chunks == [b"a", b"b"]


def test_publisher_publish_calls_finalize_after_loop() -> None:
    """Verify archiver.finalize() and client.finalize() are called after the chunk loop."""
    archiver = _StubArchiver()
    client = _StubClient()
    Publisher(
        archiver=archiver,
        client=client,
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    ).publish(_artifact([b"x"]))
    assert archiver.finalized is True
    assert client.finalized is True


# ---------------------------------------------------------------------------
# Publisher.publish() — return contract
# ---------------------------------------------------------------------------


def test_publisher_publish_returns_produced_artifact() -> None:
    """publish() returns a ProducedArtifact."""
    result = Publisher(
        archiver=_StubArchiver(),
        client=_StubClient(),
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    ).publish(_artifact([b"x"]))
    assert isinstance(result, ProducedArtifact)


def test_publisher_publish_payload_is_reiterable_tuple() -> None:
    """publish() materializes payload into a tuple (re-iterable)."""
    result = Publisher(
        archiver=_StubArchiver(),
        client=_StubClient(),
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    ).publish(_artifact([b"a", b"b"]))
    assert list(result.payload) == [b"a", b"b"]
    assert list(result.payload) == [b"a", b"b"]


def test_publisher_publish_metadata_is_publish_metadata() -> None:
    """publish() returns ProducedArtifact whose metadata is PublishMetadata."""
    result = Publisher(
        archiver=_StubArchiver(),
        client=_StubClient(),
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    ).publish(_artifact([b"x"]))
    assert isinstance(result.metadata, PublishMetadata)


def test_publisher_publish_metadata_location() -> None:
    """PublishMetadata.location matches archived.location from stub."""
    result = Publisher(
        archiver=_StubArchiver(),
        client=_StubClient(),
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    ).publish(_artifact([b"x"]))
    assert isinstance(result.metadata, PublishMetadata)
    assert result.metadata.location == "s3://test/key"


def test_publisher_publish_metadata_status_code() -> None:
    """PublishMetadata.delivery_status_code matches status_code from stub."""
    result = Publisher(
        archiver=_StubArchiver(),
        client=_StubClient(),
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    ).publish(_artifact([b"x"]))
    assert isinstance(result.metadata, PublishMetadata)
    assert result.metadata.delivery_status_code == 200


def test_publisher_publish_single_chunk() -> None:
    """Verify publish() processes a single-chunk payload correctly."""
    archiver = _StubArchiver()
    client = _StubClient()
    result = Publisher(
        archiver=archiver,
        client=client,
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    ).publish(_artifact([b"full_bytes"]))
    assert archiver.chunks == [b"full_bytes"]
    assert client.chunks == [b"full_bytes"]
    assert isinstance(result, ProducedArtifact)


def test_publisher_publish_empty_payload() -> None:
    """Verify publish() calls open()/finalize() even when payload is empty."""
    archiver = _StubArchiver()
    client = _StubClient()
    result = Publisher(
        archiver=archiver,
        client=client,
        log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
    ).publish(_artifact([]))
    assert archiver.opened is True
    assert client.opened is True
    assert archiver.chunks == []
    assert client.chunks == []
    assert archiver.finalized is True
    assert client.finalized is True
    assert isinstance(result, ProducedArtifact)


def test_publisher_publish_reraises_exception_from_archiver() -> None:
    """Verify publish() re-raises exceptions thrown by archiver."""

    class _FailingArchiver:
        def open(self) -> None:
            raise RuntimeError("archiver failed")

        def write_chunk(self, chunk: bytes) -> None:
            pass

        def finalize(self) -> ArchiveResult:
            return ArchiveResult(skipped=True)

    with pytest.raises(RuntimeError, match="archiver failed"):
        Publisher(
            archiver=_FailingArchiver(),
            client=_StubClient(),
            log_pipeline=_LogPipelineStub(),  # type: ignore[arg-type]
        ).publish(_artifact([b"x"]))
