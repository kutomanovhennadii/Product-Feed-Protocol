"""Tests for pfp_core.unified_model.common."""

from typing import cast

import pytest

_common = pytest.importorskip(
    "pfp_core.unified_model.common",
    reason="unified_model removed: legacy tests disabled",
)
URL = cast(type[str], _common.URL)
ISODate = cast(type[str], _common.ISODate)


def test_common_aliases_are_string_aliases() -> None:
    """Expose URL and ISODate aliases as str for runtime typing compatibility."""
    assert URL is str
    assert ISODate is str
