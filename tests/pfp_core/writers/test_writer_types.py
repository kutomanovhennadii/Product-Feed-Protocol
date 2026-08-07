"""Tests for writer-layer shared types and canonical sentinel."""

from pfp_core.writers.writer_types import MISSING


def test_missing_is_singleton_marker_object() -> None:
    """Preserve identity-based sentinel semantics for pipeline-writer boundary."""

    another_object = object()

    assert MISSING is MISSING
    assert MISSING is not None
    assert MISSING is not another_object


def test_missing_is_distinct_from_regular_values() -> None:
    """Keep Missing marker distinct from normal payload values."""

    assert MISSING != ""
    assert MISSING != 0
    assert MISSING is not False
