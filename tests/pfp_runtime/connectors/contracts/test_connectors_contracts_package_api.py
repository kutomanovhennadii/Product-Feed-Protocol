"""Tests for package-level runtime connectors contracts API surface."""

import pfp_runtime.connectors.contracts as contracts_pkg


def test_package_api_exposes_public_symbols() -> None:
    """Package import exposes canonical connector contract surface."""
    expected = {
        "SourceConnector",
        "UnifiedItem",
    }
    assert set(contracts_pkg.__all__) == expected

    for symbol in expected:
        assert hasattr(contracts_pkg, symbol)
