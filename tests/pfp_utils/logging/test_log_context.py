"""Tests for observability logging context."""

from pfp_utils.logging.log_context import LogContext, _get_context


def test_log_context_threading() -> None:
    """Test context isolation and stacking."""
    with LogContext(a=1):
        assert _get_context()["a"] == 1
        with LogContext(b=2):
            assert _get_context()["a"] == 1
            assert _get_context()["b"] == 2
        assert "b" not in _get_context()
    assert not _get_context()
