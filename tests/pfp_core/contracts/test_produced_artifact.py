from datetime import datetime, timezone

from pfp_core.contracts.artifact_metadata import ArtifactMetadata
from pfp_core.contracts.produced_artifact import ProducedArtifact


def _metadata() -> ArtifactMetadata:
    return ArtifactMetadata(
        target="stripe.product",
        schema_version="1.0.0",
        generated_at=datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        content_type="text/csv",
        encoding="utf-8",
    )


def test_produced_artifact_stores_payload_and_metadata() -> None:
    """ProducedArtifact stores payload and metadata fields."""
    artifact = ProducedArtifact(payload=[b"row"], metadata=_metadata())
    assert list(artifact.payload) == [b"row"]
    assert artifact.metadata.target == "stripe.product"


def test_produced_artifact_two_fields_only() -> None:
    """ProducedArtifact has exactly payload and metadata — no other fields."""
    artifact = ProducedArtifact(payload=iter([b"x"]), metadata=_metadata())
    field_names = {f.name for f in artifact.__dataclass_fields__.values()}  # type: ignore[attr-defined]
    assert field_names == {"payload", "metadata"}


def test_produced_artifact_no_diagnostics_field() -> None:
    """ProducedArtifact does not have a diagnostics field."""
    artifact = ProducedArtifact(payload=[b"x"], metadata=_metadata())
    assert not hasattr(artifact, "diagnostics")


def test_produced_artifact_metadata_is_artifact_metadata() -> None:
    """metadata field holds an ArtifactMetadata instance."""
    m = _metadata()
    artifact = ProducedArtifact(payload=[], metadata=m)
    assert isinstance(artifact.metadata, ArtifactMetadata)
    assert artifact.metadata is m


def test_produced_artifact_payload_tuple_is_reiterable() -> None:
    """When payload is a tuple, it can be iterated multiple times."""
    artifact = ProducedArtifact(payload=tuple([b"a", b"b"]), metadata=_metadata())
    assert list(artifact.payload) == [b"a", b"b"]
    assert list(artifact.payload) == [b"a", b"b"]
