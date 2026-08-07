import pytest

from pfp_core.artifact_production.artifact_production_naming import (
    _normalize_target_for_extension,
    make_filename_hint,
)


def test_make_filename_hint_is_deterministic() -> None:
    """Return stable filename hints for identical inputs."""
    hint_one = make_filename_hint("STRIPE", "FULL", "1")
    hint_two = make_filename_hint("STRIPE", "FULL", "1")
    assert hint_one == hint_two


def test_make_filename_hint_extensions() -> None:
    """Use target-specific extensions in filename hints."""
    assert make_filename_hint("STRIPE", "FULL", "1").endswith(".csv")
    assert make_filename_hint("OPENAI", "DIFF", "1").endswith(".jsonl")


def test_make_filename_hint_sanitizes_parts() -> None:
    """Replace disallowed characters in filename hints."""
    hint = make_filename_hint("STRI:PE", "DI FF", "v1/2")
    assert hint == "STRI_PE__DI_FF__vv1_2.csv"


def test_make_filename_hint_runtime_file_extension_mode() -> None:
    """Preserve runtime semantics when explicit writer extension is provided."""
    hint = make_filename_hint("stripe/product", "FULL/DIFF", "1/0/0", ".csv")
    assert hint == "stripe_product__FULL_DIFF__v1_0_0.csv"


def test_make_filename_hint_rejects_unknown_target() -> None:
    """Reject unsupported targets in filename hints."""
    with pytest.raises(ValueError, match="Unsupported target"):
        make_filename_hint("OTHER", "FULL", "1")


def test_make_filename_hint_rejects_empty_target() -> None:
    """Reject empty target before extension resolution."""
    with pytest.raises(ValueError, match="Target must not be empty"):
        make_filename_hint("", "FULL", "1")


def test_normalize_target_for_extension_empty() -> None:
    """Return empty normalized target when source target is empty."""
    assert _normalize_target_for_extension("") == ""
