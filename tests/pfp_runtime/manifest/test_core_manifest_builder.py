"""Mirror unit tests for manifest.core_manifest_builder."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from pfp_core.artifact_production.artifact_producer import ArtifactProducer
from pfp_runtime.config.infra_models import InfraConfig
from pfp_runtime.manifest import core_manifest_builder
from pfp_runtime.manifest.pipeline_manifest import CoreManifest, ManifestBuildError
from pfp_utils.logging import LogPipeline


def _make_infra() -> InfraConfig:
    """Build minimal canonical infra model for core manifest tests."""
    return InfraConfig.model_validate(
        {
            "input": {
                "format": "csv",
                "config": {
                    "connector_mapping": "./mapping.yaml",
                },
            },
            "output": {
                "archive_type": "noop",
                "archive_config": "./archive/noop.yaml",
                "client_type": "noop",
                "client_config": "./clients/noop.yaml",
            },
            "producer": {
                "schema_file": "./schemas/product.yaml",
                "policy_file": "./config/policies.yaml",
            },
        }
    )


def _make_tax_mapping_file(tmp_path: Path, *, content: str) -> str:
    """Persist a temporary tax mapping JSON file for manifest builder tests."""
    mapping_file = tmp_path / "tax_mapping.json"
    mapping_file.write_text(content, encoding="utf-8")
    return str(mapping_file)


def test_build_core_manifest_returns_non_none_producer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Build CoreManifest with prepared non-None ArtifactProducer instance."""
    infra = _make_infra()
    producer = cast(ArtifactProducer, object())
    log_pipeline = cast(LogPipeline, object())

    def _fake_prepare(
        *,
        schema_file: str,
        policy_file: str,
        tax_mapping: object | None,
        log_pipeline: LogPipeline,
    ) -> ArtifactProducer:
        assert schema_file == infra.producer.schema_file
        assert policy_file == infra.producer.policy_file
        assert tax_mapping is None
        assert log_pipeline is not None
        return producer

    monkeypatch.setattr(
        core_manifest_builder,
        "prepare_artifact_producer_from_files",
        _fake_prepare,
    )

    result = core_manifest_builder.build_core_manifest(
        infra,
        log_pipeline=log_pipeline,
    )

    assert isinstance(result, CoreManifest)
    assert result.producer is producer


def test_build_core_manifest_wraps_prepare_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Translate producer preparation failure into ManifestBuildError."""
    infra = _make_infra()
    log_pipeline = cast(LogPipeline, object())

    def _failing_prepare(
        *,
        schema_file: str,
        policy_file: str,
        tax_mapping: object | None,
        log_pipeline: LogPipeline,
    ) -> ArtifactProducer:
        del schema_file, policy_file, tax_mapping, log_pipeline
        raise ValueError("producer preparation failed")

    monkeypatch.setattr(
        core_manifest_builder,
        "prepare_artifact_producer_from_files",
        _failing_prepare,
    )

    with pytest.raises(
        ManifestBuildError, match="producer preparation failed"
    ) as exc_info:
        core_manifest_builder.build_core_manifest(
            infra,
            log_pipeline=log_pipeline,
        )

    assert isinstance(exc_info.value.__cause__, ValueError)


def test_build_core_manifest_loads_tax_mapping_and_passes_it_forward(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Load tax mapping JSON and forward parsed data into producer assembly."""
    infra = _make_infra().model_copy(
        update={
            "producer": _make_infra().producer.model_copy(
                update={
                    "tax_mapping_file": _make_tax_mapping_file(
                        tmp_path,
                        content='{"mappings": {"Pet Supplies": "txcd_99999999"}}',
                    )
                }
            )
        }
    )
    producer = cast(ArtifactProducer, object())
    log_pipeline = cast(LogPipeline, object())

    def _fake_prepare(
        *,
        schema_file: str,
        policy_file: str,
        tax_mapping: object | None,
        log_pipeline: LogPipeline,
    ) -> ArtifactProducer:
        assert schema_file == infra.producer.schema_file
        assert policy_file == infra.producer.policy_file
        assert tax_mapping == {"mappings": {"Pet Supplies": "txcd_99999999"}}
        assert log_pipeline is not None
        return producer

    monkeypatch.setattr(
        core_manifest_builder,
        "prepare_artifact_producer_from_files",
        _fake_prepare,
    )

    result = core_manifest_builder.build_core_manifest(
        infra,
        log_pipeline=log_pipeline,
    )

    assert result.producer is producer


def test_build_core_manifest_wraps_missing_tax_mapping_file(
    tmp_path: Path,
) -> None:
    """Wrap missing tax mapping file errors with ManifestBuildError."""
    infra = _make_infra().model_copy(
        update={
            "producer": _make_infra().producer.model_copy(
                update={"tax_mapping_file": str(tmp_path / "missing_tax_mapping.json")}
            )
        }
    )

    with pytest.raises(
        ManifestBuildError, match="missing_tax_mapping.json"
    ) as exc_info:
        core_manifest_builder.build_core_manifest(
            infra,
            log_pipeline=cast(LogPipeline, object()),
        )

    assert isinstance(exc_info.value.__cause__, OSError)


def test_build_core_manifest_wraps_invalid_tax_mapping_json(
    tmp_path: Path,
) -> None:
    """Wrap tax mapping JSON parse failures with ManifestBuildError."""
    infra = _make_infra().model_copy(
        update={
            "producer": _make_infra().producer.model_copy(
                update={
                    "tax_mapping_file": _make_tax_mapping_file(
                        tmp_path,
                        content='{"mappings": ',
                    )
                }
            )
        }
    )

    with pytest.raises(
        ManifestBuildError, match="failed to parse tax mapping JSON"
    ) as exc_info:
        core_manifest_builder.build_core_manifest(
            infra,
            log_pipeline=cast(LogPipeline, object()),
        )

    assert isinstance(exc_info.value.__cause__, ValueError)


def test_build_core_manifest_rejects_tax_mapping_without_mappings_object(
    tmp_path: Path,
) -> None:
    """Reject tax mapping JSON files that lack the required mappings object."""
    infra = _make_infra().model_copy(
        update={
            "producer": _make_infra().producer.model_copy(
                update={
                    "tax_mapping_file": _make_tax_mapping_file(
                        tmp_path,
                        content='{"unexpected": {}}',
                    )
                }
            )
        }
    )

    with pytest.raises(
        ManifestBuildError, match="must contain a 'mappings' object"
    ) as exc_info:
        core_manifest_builder.build_core_manifest(
            infra,
            log_pipeline=cast(LogPipeline, object()),
        )

    assert isinstance(exc_info.value.__cause__, ValueError)


def test_build_core_manifest_rejects_tax_mapping_without_object_root(
    tmp_path: Path,
) -> None:
    """Reject tax mapping JSON files whose root value is not an object."""
    infra = _make_infra().model_copy(
        update={
            "producer": _make_infra().producer.model_copy(
                update={
                    "tax_mapping_file": _make_tax_mapping_file(
                        tmp_path,
                        content='["not-an-object"]',
                    )
                }
            )
        }
    )

    with pytest.raises(
        ManifestBuildError, match="must contain an object root"
    ) as exc_info:
        core_manifest_builder.build_core_manifest(
            infra,
            log_pipeline=cast(LogPipeline, object()),
        )

    assert isinstance(exc_info.value.__cause__, ValueError)
