from datetime import datetime, timezone

import pytest

from pfp_core.contracts.artifact_metadata import ArtifactMetadata
from pfp_runtime.publishing.archivers.archiver_contract import ArchiveResult
from pfp_runtime.publishing.clients.client_contract import DeliveryResult
from pfp_runtime.publishing.contracts.publish_metadata import PublishMetadata


def _base_metadata() -> ArtifactMetadata:
    return ArtifactMetadata(
        target="stripe.product",
        schema_version="1.0.0",
        generated_at=datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        content_type="text/csv",
        encoding="utf-8",
        artifact_profile="catalog_snapshot",
        filename_hint="stripe.product__FULL__v1.0.0.csv",
    )


# ---------------------------------------------------------------------------
# from_publish_results — field mapping
# ---------------------------------------------------------------------------


def test_from_publish_results_inherits_base_fields() -> None:
    """All ArtifactMetadata fields are copied into PublishMetadata."""
    base = _base_metadata()
    archived = ArchiveResult(skipped=False, location="s3://bucket/key")
    delivered = DeliveryResult(skipped=False, status_code=200)
    pm = PublishMetadata.from_publish_results(base, archived, delivered)

    assert pm.target == base.target
    assert pm.schema_version == base.schema_version
    assert pm.generated_at == base.generated_at
    assert pm.content_type == base.content_type
    assert pm.encoding == base.encoding
    assert pm.artifact_profile == base.artifact_profile
    assert pm.filename_hint == base.filename_hint


def test_from_publish_results_location() -> None:
    """location is taken from archived.location."""
    base = _base_metadata()
    archived = ArchiveResult(skipped=False, location="s3://bucket/key")
    delivered = DeliveryResult(skipped=False, status_code=200)
    pm = PublishMetadata.from_publish_results(base, archived, delivered)
    assert pm.location == "s3://bucket/key"


def test_from_publish_results_location_none_when_skipped() -> None:
    """location is None when archiver is skipped."""
    base = _base_metadata()
    archived = ArchiveResult(skipped=True, location=None)
    delivered = DeliveryResult(skipped=True)
    pm = PublishMetadata.from_publish_results(base, archived, delivered)
    assert pm.location is None


def test_from_publish_results_archive_skipped() -> None:
    """archive_skipped reflects archived.skipped."""
    base = _base_metadata()
    pm_skipped = PublishMetadata.from_publish_results(
        base, ArchiveResult(skipped=True), DeliveryResult(skipped=False)
    )
    pm_not_skipped = PublishMetadata.from_publish_results(
        base,
        ArchiveResult(skipped=False, location="s3://x"),
        DeliveryResult(skipped=False),
    )
    assert pm_skipped.archive_skipped is True
    assert pm_not_skipped.archive_skipped is False


def test_from_publish_results_delivery_skipped() -> None:
    """delivery_skipped reflects delivered.skipped."""
    base = _base_metadata()
    pm_skipped = PublishMetadata.from_publish_results(
        base, ArchiveResult(skipped=True), DeliveryResult(skipped=True)
    )
    pm_not_skipped = PublishMetadata.from_publish_results(
        base,
        ArchiveResult(skipped=True),
        DeliveryResult(skipped=False, status_code=200),
    )
    assert pm_skipped.delivery_skipped is True
    assert pm_not_skipped.delivery_skipped is False


def test_from_publish_results_delivery_status_code() -> None:
    """delivery_status_code reflects delivered.status_code."""
    base = _base_metadata()
    pm = PublishMetadata.from_publish_results(
        base,
        ArchiveResult(skipped=False, location="s3://x"),
        DeliveryResult(skipped=False, status_code=201),
    )
    assert pm.delivery_status_code == 201


def test_from_publish_results_status_code_none_when_skipped() -> None:
    """delivery_status_code is None when delivery is skipped."""
    base = _base_metadata()
    pm = PublishMetadata.from_publish_results(
        base, ArchiveResult(skipped=True), DeliveryResult(skipped=True)
    )
    assert pm.delivery_status_code is None


# ---------------------------------------------------------------------------
# Inheritance
# ---------------------------------------------------------------------------


def test_publish_metadata_is_subclass_of_artifact_metadata() -> None:
    """PublishMetadata is a subclass of ArtifactMetadata."""
    assert issubclass(PublishMetadata, ArtifactMetadata)


def test_publish_metadata_isinstance_artifact_metadata() -> None:
    """A PublishMetadata instance passes isinstance(ArtifactMetadata) check."""
    base = _base_metadata()
    pm = PublishMetadata.from_publish_results(
        base,
        ArchiveResult(skipped=False, location="s3://x"),
        DeliveryResult(skipped=False, status_code=200),
    )
    assert isinstance(pm, ArtifactMetadata)


# ---------------------------------------------------------------------------
# Frozen
# ---------------------------------------------------------------------------


def test_publish_metadata_is_frozen() -> None:
    """PublishMetadata is frozen — mutation raises AttributeError."""
    base = _base_metadata()
    pm = PublishMetadata.from_publish_results(
        base, ArchiveResult(skipped=True), DeliveryResult(skipped=True)
    )
    with pytest.raises((AttributeError, TypeError)):
        pm.location = "other"  # type: ignore[misc]
