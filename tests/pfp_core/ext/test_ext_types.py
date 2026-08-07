import pytest

from pfp_core.ext.ext_types import MISSING, Emission


def test_types_missing_repr_and_emission_invariants() -> None:
    """MISSING and Emission enforce their invariants deterministically."""
    assert repr(MISSING) == "MISSING"

    with pytest.raises(ValueError):
        Emission(kind="VALUE", value=None)

    with pytest.raises(ValueError):
        Emission(kind="OMIT", value="x")
