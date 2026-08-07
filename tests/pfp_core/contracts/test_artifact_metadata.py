from datetime import datetime, timezone

import pytest

from pfp_core.contracts.artifact_metadata import ArtifactMetadata


def _ts() -> datetime:
    return datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


def test_artifact_metadata_required_fields() -> None:
    """ArtifactMetadata stores all required fields correctly."""
    m = ArtifactMetadata(
        target="stripe.product",
        schema_version="1.0.0",
        generated_at=_ts(),
        content_type="text/csv",
        encoding="utf-8",
    )
    assert m.target == "stripe.product"
    assert m.schema_version == "1.0.0"
    assert m.generated_at == _ts()
    assert m.content_type == "text/csv"
    assert m.encoding == "utf-8"


def test_artifact_metadata_optional_defaults() -> None:
    """Optional fields default to None."""
    m = ArtifactMetadata(
        target="stripe.product",
        schema_version="1.0.0",
        generated_at=_ts(),
        content_type="text/csv",
        encoding="utf-8",
    )
    assert m.artifact_profile is None
    assert m.filename_hint is None


def test_artifact_metadata_optional_fields_set() -> None:
    """Optional fields are stored when provided."""
    m = ArtifactMetadata(
        target="stripe.product",
        schema_version="1.0.0",
        generated_at=_ts(),
        content_type="text/csv",
        encoding="utf-8",
        artifact_profile="catalog_snapshot",
        filename_hint="stripe.product__FULL__v1.0.0.csv",
    )
    assert m.artifact_profile == "catalog_snapshot"
    assert m.filename_hint == "stripe.product__FULL__v1.0.0.csv"


def test_artifact_metadata_is_frozen() -> None:
    """ArtifactMetadata is a frozen dataclass — mutation raises AttributeError."""
    m = ArtifactMetadata(
        target="stripe.product",
        schema_version="1.0.0",
        generated_at=_ts(),
        content_type="text/csv",
        encoding="utf-8",
    )
    with pytest.raises((AttributeError, TypeError)):
        m.target = "other"  # type: ignore[misc]


def test_artifact_metadata_equality() -> None:
    """Two ArtifactMetadata with identical fields are equal."""
    m1 = ArtifactMetadata(
        target="stripe.product",
        schema_version="1.0.0",
        generated_at=_ts(),
        content_type="text/csv",
        encoding="utf-8",
    )
    m2 = ArtifactMetadata(
        target="stripe.product",
        schema_version="1.0.0",
        generated_at=_ts(),
        content_type="text/csv",
        encoding="utf-8",
    )
    assert m1 == m2
