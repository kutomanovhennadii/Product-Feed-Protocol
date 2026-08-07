from __future__ import annotations

import re

_SEMVER_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def is_semver(version: str) -> bool:
    """Check whether a version string matches strict SemVer MAJOR.MINOR.PATCH.

    Args:
        version: Candidate version string.

    Returns:
        ``True`` when the value is strict three-part SemVer, otherwise ``False``.
    """

    return _SEMVER_PATTERN.fullmatch(version) is not None


def semver_sort_key(version: str) -> tuple[int, int, int, int, str]:
    """Build a deterministic sort key for SemVer-like values.

    Args:
        version: Version string to transform into a sort key.

    Returns:
        A tuple that sorts valid SemVer values numerically first and invalid
        values after them in lexical order.
    """

    match = _SEMVER_PATTERN.fullmatch(version)
    if match is None:
        return (1, 0, 0, 0, version)
    major, minor, patch = match.groups()
    return (0, int(major), int(minor), int(patch), version)
