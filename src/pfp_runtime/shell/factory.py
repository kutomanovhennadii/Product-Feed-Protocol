"""User-facing factory API for building Product Shell runtime workers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Union

from pfp_core.artifact_production import ArtifactProducer
from pfp_runtime.manifest.pipeline_manifest_provider import build_pipeline_manifest
from pfp_runtime.orchestration.pipeline_runner import PipelineRunner
from pfp_runtime.pipeline.execution_report import ExecutionReport


class FactoryConfigError(ValueError):
    """Raised when factory inputs violate user-facing contract constraints.

    Args:
        *args: Positional error message fragments propagated to ``ValueError``.

    Returns:
        FactoryConfigError instance describing the invalid factory input.
    """


@dataclass(frozen=True)
class PFPWorker:
    """Prepared runtime worker context assembled from user-facing configs.

    Args:
        _runner: Internal runtime orchestrator used for execution.
        producer: Prepared artifact producer exposed for advanced callers.

    Returns:
        PFPWorker instance ready to execute ``run`` calls.
    """

    _runner: PipelineRunner
    producer: ArtifactProducer

    def run(self, input_data: bytes) -> ExecutionReport:
        """Execute one pipeline run with the provided input data.

        Args:
            input_data: Raw input bytes to process through the pipeline.

        Returns:
            ExecutionReport from the pipeline execution.
        """
        return self._runner.run(input_data)


class PFPFactory:
    """Factory that assembles ready ``PFPWorker`` instances from infra YAML paths.

    Args:
        None.

    Returns:
        Stateless PFPFactory instance ready to build workers on demand.
    """

    def __init__(self) -> None:
        """Create a stateless factory instance.

        Args:
            None.

        Returns:
            None.
        """
        return None

    def build_worker(
        self,
        *,
        infra_path: Union[str, Path],
    ) -> PFPWorker:
        """Build a ready worker by orchestrating the manifest pipeline.

        Args:
            infra_path: Path to infra YAML configuration file.

        Returns:
            PFPWorker: Prepared worker context with compiled manifest and
            artifact producer.

        Raises:
            FactoryConfigError: If infra_path is empty or not a string/Path.
        """
        if not isinstance(infra_path, (str, Path)):
            raise FactoryConfigError("infra_path must be a string or Path")
        if not str(infra_path).strip():
            raise FactoryConfigError("infra_path must be non-empty")
        manifest = build_pipeline_manifest(str(infra_path))
        runner = PipelineRunner(manifest)
        return PFPWorker(_runner=runner, producer=manifest.core.producer)


def get_pfp_factory() -> PFPFactory:
    """Create a ``PFPFactory`` using the canonical user-facing factory contract.

    Args:
        None.

    Returns:
        PFPFactory: Configured factory instance.
    """
    return PFPFactory()


__all__ = ["FactoryConfigError", "PFPFactory", "PFPWorker", "get_pfp_factory"]
