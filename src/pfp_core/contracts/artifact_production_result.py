from dataclasses import dataclass
from typing import Tuple

from pfp_core.contracts.produced_artifact import ProducedArtifact
from pfp_utils.diagnostics.validation_report import ValidationReport


@dataclass(frozen=True)
class ArtifactProductionResult:
    """Public build result returned by schema-driven API.

    Args:
        artifacts: Per-schema artifacts in deterministic order.
        validation_report: Aggregated validation report across produced targets.

    Returns:
        None.
    """

    artifacts: Tuple[ProducedArtifact, ...]
    validation_report: ValidationReport
