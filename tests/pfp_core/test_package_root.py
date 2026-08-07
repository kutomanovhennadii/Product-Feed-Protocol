import pfp_core


def test_import_version() -> None:
    """Expose package version through top-level import contract."""
    assert getattr(pfp_core, "__version__", None) == "0.1.0"
