from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


@dataclass(frozen=True)
class GoldenSampleCase:
    target: str
    mode: str
    case_id: str
    case_dir: Path
    input_um: Dict[str, Any]
    expected_bytes: bytes
    expected_format: str
    diagnostics: List[Dict[str, Any]]

    @classmethod
    def from_dir(cls, case_dir: Path) -> "GoldenSampleCase":
        target_dir = case_dir.parent.parent
        mode_dir = case_dir.parent
        target = target_dir.name
        mode = mode_dir.name
        case_id = case_dir.name
        input_path = case_dir / "input_um.json"
        if not input_path.exists():
            raise FileNotFoundError(f"input_um.json is missing in {case_dir}")
        with input_path.open(encoding="utf-8") as fp:
            input_um = json.load(fp)

        expected_files = sorted(case_dir.glob("expected.*"))
        if not expected_files:
            raise FileNotFoundError(f"no expected file found in {case_dir}")
        expected_path = expected_files[0]
        expected_bytes = expected_path.read_bytes()
        expected_format = expected_path.suffix.lstrip(".")

        diagnostics_path = case_dir / "diagnostics.json"
        diagnostics: List[Dict[str, Any]] = []
        if diagnostics_path.exists():
            with diagnostics_path.open(encoding="utf-8") as fp:
                diagnostics = json.load(fp)

        return cls(
            target=target,
            mode=mode,
            case_id=case_id,
            case_dir=case_dir,
            input_um=input_um,
            expected_bytes=expected_bytes,
            expected_format=expected_format,
            diagnostics=diagnostics,
        )

    @classmethod
    def from_output_file(cls, output_file: Path) -> "GoldenSampleCase":
        mode_dir = output_file.parent
        target_dir = mode_dir.parent

        return cls(
            target=target_dir.name,
            mode=mode_dir.name,
            case_id=output_file.stem,
            case_dir=mode_dir,
            input_um={},
            expected_bytes=output_file.read_bytes(),
            expected_format=output_file.suffix.lstrip("."),
            diagnostics=[],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target": self.target,
            "mode": self.mode,
            "case_id": self.case_id,
            "input_um": self.input_um,
            "expected_format": self.expected_format,
            "expected_bytes": self.expected_bytes,
            "diagnostics": self.diagnostics,
        }


def discover_cases(base_dir: Optional[Path] = None) -> Iterable[GoldenSampleCase]:
    base_dir = (base_dir or Path(__file__).parent / "outputs").resolve()
    for target_dir in sorted(p for p in base_dir.iterdir() if p.is_dir()):
        for mode_dir in sorted(p for p in target_dir.iterdir() if p.is_dir()):
            case_dirs = sorted(p for p in mode_dir.iterdir() if p.is_dir())
            if case_dirs:
                for case_dir in case_dirs:
                    yield GoldenSampleCase.from_dir(case_dir)
                continue

            for output_file in sorted(p for p in mode_dir.iterdir() if p.is_file()):
                yield GoldenSampleCase.from_output_file(output_file)
