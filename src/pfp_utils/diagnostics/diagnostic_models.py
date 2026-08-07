from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Union

_SEVERITY_ALIASES: Dict[str, str] = {
    "WARNING": "WARN",
}

_SEVERITY_RANKS: Dict[str, int] = {
    "ERROR": 0,
    "WARN": 1,
    "INFO": 2,
}


class DiagnosticSeverity(Enum):
    ERROR = "ERROR"
    WARN = "WARN"
    INFO = "INFO"

    @classmethod
    def normalize(cls, value: "Union[DiagnosticSeverity, str]") -> "DiagnosticSeverity":
        if isinstance(value, DiagnosticSeverity):
            return value
        text = str(value).strip().upper()
        text = _SEVERITY_ALIASES.get(text, text)
        try:
            return cls[text]
        except KeyError as exc:
            raise ValueError("Unknown severity '{0}'".format(value)) from exc

    @property
    def rank(self) -> int:
        return _SEVERITY_RANKS[self.value]

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, init=False)
class Diagnostic:
    severity: Union[DiagnosticSeverity, str]
    code: str
    message: str
    path: Optional[str] = None
    item_ref: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict, compare=False)

    def __init__(
        self,
        severity: Union[DiagnosticSeverity, str],
        code: str = "",
        message: str = "",
        path: Optional[str] = None,
        item_ref: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        object.__setattr__(
            self,
            "severity",
            DiagnosticSeverity.normalize(severity),
        )
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "message", message)
        object.__setattr__(self, "path", path)
        object.__setattr__(self, "item_ref", item_ref)
        object.__setattr__(self, "metadata", dict(metadata or {}))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": str(self.severity),
            "code": self.code,
            "message": self.message,
            "path": self.path,
            "item_ref": self.item_ref,
            "metadata": dict(self.metadata),
        }
