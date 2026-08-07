"""Compiler diagnostics helpers for deterministic error collection."""

from __future__ import annotations

from typing import List

from pfp_core.engine.plan_types import CompileDiagItem


def add_error(
    diagnostics: List[CompileDiagItem],
    *,
    code: str,
    path: str,
    message: str,
) -> None:
    """Append an `ERROR` diagnostic.

    Args:
        diagnostics: Mutable diagnostics accumulator.
        code: Stable diagnostic code.
        path: Schema path where issue was found.
        message: Deterministic diagnostic message.

    Returns:
        None.
    """

    diagnostics.append(
        CompileDiagItem(
            code=code,
            path=path,
            message=message,
            severity="ERROR",
        )
    )
