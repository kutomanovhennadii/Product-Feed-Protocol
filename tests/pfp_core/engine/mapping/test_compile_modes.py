"""Contract tests for deprecated mapping compile-modes shim."""

import pfp_core.engine.mapping.compile_modes as compile_modes_mod


def test_compile_modes_module_remains_intentionally_empty() -> None:
    """Deprecated shim stays importable and intentionally empty."""

    assert compile_modes_mod.__doc__ == "Deprecated module kept intentionally empty."
