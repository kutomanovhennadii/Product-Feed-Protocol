"""Public facade contract tests for pfp_core.writers."""

import pfp_core.writers as writers


def test_public_facade_hides_concrete_writers() -> None:
    """Do not re-export concrete writer classes from package facade."""

    assert not hasattr(writers, "CSVWriter")
    assert not hasattr(writers, "JSONLWriter")


def test_public_facade_exports_expected_symbols() -> None:
    """Expose only the approved writer-layer public surface symbols."""

    expected_symbols = {
        "Writer",
        "WriterRegistry",
        "WriterSpec",
        "MISSING",
        "build_default_writer_registry",
    }

    assert set(writers.__all__) == expected_symbols

    for symbol in expected_symbols:
        assert hasattr(writers, symbol)


def test_public_facade_hides_internal_error_symbols() -> None:
    """Do not leak internal registry error symbols through package facade."""

    assert not hasattr(writers, "UnknownWriterError")
    assert not hasattr(writers, "WriterConfigError")


def test_public_facade_hides_internal_type_symbols() -> None:
    """Do not leak internal writer type contracts through package facade."""

    assert not hasattr(writers, "ArtifactMeta")
