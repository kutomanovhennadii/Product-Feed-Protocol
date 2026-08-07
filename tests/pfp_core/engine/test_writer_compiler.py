"""Entrypoint tests for `pfp_core.engine.writer_compiler.compile_writer_spec`."""

from typing import List, Tuple

from pfp_core.engine.plan_types import CompileDiagItem
from pfp_core.engine.writer_compiler import compile_writer_spec


def _diag_codes(items: Tuple[CompileDiagItem, ...]) -> List[str]:
    """Return diagnostic codes list."""

    return [item.code for item in items]


def test_writer_compile_invalid_output_type() -> None:
    """Ensure non-object output yields COMPILER_OUTPUT_INVALID and empty writer spec."""

    diagnostics: List[CompileDiagItem] = []
    spec = compile_writer_spec({"output": "invalid"}, diagnostics)

    assert spec.writer_id == ""
    assert spec.artifact_content_type == ""
    assert spec.artifact_file_extension == ""
    assert _diag_codes(tuple(diagnostics)) == ["COMPILER_OUTPUT_INVALID"]


def test_writer_compile_invalid_nested_types() -> None:
    """Ensure invalid nested output fields produce deterministic diagnostics."""

    diagnostics: List[CompileDiagItem] = []
    spec = compile_writer_spec(
        {
            "output": {
                "writer_id": 123,
                "writer_config": [],
                "artifact": {
                    "content_type": 10,
                    "file_extension": False,
                },
            }
        },
        diagnostics,
    )

    assert spec.writer_id == ""
    assert spec.artifact_content_type == ""
    assert spec.artifact_file_extension == ""
    assert _diag_codes(tuple(diagnostics)) == [
        "COMPILER_OUTPUT_INVALID",
        "COMPILER_OUTPUT_INVALID",
        "COMPILER_OUTPUT_INVALID",
        "COMPILER_OUTPUT_INVALID",
    ]


def test_writer_compile_invalid_artifact_object_type() -> None:
    """Ensure non-object artifact branch emits dedicated artifact diagnostic."""

    diagnostics: List[CompileDiagItem] = []
    spec = compile_writer_spec(
        {
            "output": {
                "writer_id": "csv",
                "writer_config": {},
                "artifact": "bad",
            }
        },
        diagnostics,
    )

    assert spec.writer_id == "csv"
    assert spec.artifact_content_type == ""
    assert spec.artifact_file_extension == ""
    assert _diag_codes(tuple(diagnostics)) == [
        "COMPILER_OUTPUT_INVALID",
        "COMPILER_OUTPUT_INVALID",
        "COMPILER_OUTPUT_INVALID",
    ]
