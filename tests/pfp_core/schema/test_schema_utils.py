from __future__ import annotations

from pfp_core.schema.schema_utils import is_semver, semver_sort_key


def test_utils_semver_helpers() -> None:
    """Ensure SemVer helper functions return deterministic results."""

    assert is_semver("1.2.3") is True
    assert is_semver("1.2") is False
    assert semver_sort_key("2.10.3") == (0, 2, 10, 3, "2.10.3")
    assert semver_sort_key("x") == (1, 0, 0, 0, "x")
