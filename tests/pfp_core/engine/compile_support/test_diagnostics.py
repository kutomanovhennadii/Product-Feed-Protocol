from pfp_core.engine.compile_support.diagnostics import add_error
from pfp_core.engine.plan_types import CompileDiagItem


def test_add_error_appends_error_item() -> None:
    diagnostics: list[CompileDiagItem] = []
    add_error(
        diagnostics,
        code="E_CODE",
        path="schema.path",
        message="deterministic",
    )

    assert len(diagnostics) == 1
    assert diagnostics[0].code == "E_CODE"
    assert diagnostics[0].DiagnosticSeverity == "ERROR"
