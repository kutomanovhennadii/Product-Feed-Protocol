from dataclasses import dataclass, field
from typing import Dict, List, Optional

from pfp_utils.diagnostics.diagnostic_models import Diagnostic, DiagnosticSeverity


@dataclass
class ValidationReport:
    target: Optional[str]
    artifact_profile: Optional[str] = None
    diagnostics: List[Diagnostic] = field(default_factory=list)

    def add(self, diagnostic: Diagnostic) -> None:
        self.diagnostics.append(diagnostic)

    def sorted_diagnostics(self) -> List[Diagnostic]:
        return sorted(
            self.diagnostics,
            key=lambda diag: (
                DiagnosticSeverity.normalize(diag.severity).rank,
                diag.code,
                diag.item_ref or "",
                diag.path or "",
            ),
        )

    def to_dict(self) -> Dict[str, object]:
        return {
            "target": self.target,
            "artifact_profile": self.artifact_profile,
            "diagnostics": [diag.to_dict() for diag in self.sorted_diagnostics()],
        }
