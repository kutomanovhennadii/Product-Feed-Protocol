from datetime import datetime, timezone

from pfp_core.contracts.artifact_metadata import ArtifactMetadata
from pfp_core.contracts.artifact_production_result import ArtifactProductionResult
from pfp_core.contracts.produced_artifact import ProducedArtifact
from pfp_utils.diagnostics.validation_report import ValidationReport


def test_artifact_production_result_keeps_contract_shape() -> None:
    """Preserve artifacts tuple and aggregated validation report contract."""
    artifact = ProducedArtifact(
        payload=iter([b"x"]),
        metadata=ArtifactMetadata(
            target="stripe.product",
            artifact_profile="catalog_snapshot",
            schema_version="1.0.0",
            generated_at=datetime(2026, 2, 12, tzinfo=timezone.utc),
            content_type="text/csv",
            encoding="utf-8",
            filename_hint="stripe.product__FULL__v1.0.0.csv",
        ),
    )
    result = ArtifactProductionResult(
        artifacts=(artifact,),
        validation_report=ValidationReport(
            target="MULTI", artifact_profile="catalog_snapshot"
        ),
    )
    assert len(result.artifacts) == 1
    assert result.validation_report.target == "MULTI"
