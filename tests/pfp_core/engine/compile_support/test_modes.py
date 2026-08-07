"""Contract tests for deprecated compile-support modes shim."""

import pfp_core.engine.compile_support.modes as modes_mod


def test_modes_module_remains_intentionally_empty() -> None:
    """Deprecated shim stays importable and intentionally empty."""

    assert modes_mod.__doc__ == "Deprecated module kept intentionally empty."
