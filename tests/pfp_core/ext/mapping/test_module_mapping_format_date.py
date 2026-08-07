from datetime import date, datetime, timezone

import pytest

from pfp_core.ext.ext_types import MISSING
from pfp_core.ext.mapping.module_mapping_format_date import get_spec
from tests.pfp_core.ext.mapping._helpers import call_spec


def test_module_mapping_format_date_is_deterministic() -> None:
    """format_date does not depend on environment time or timezone."""
    spec = get_spec()
    assert spec.op_id == "format_date"
    assert call_spec(spec, "2026-02-12", {}) == "2026-02-12"
    assert call_spec(spec, MISSING, {}) is MISSING
    assert call_spec(spec, None, {}) is None


def test_module_mapping_format_date_validates_inputs_and_args() -> None:
    """format_date supports date/datetime inputs and validates arguments."""
    spec = get_spec()
    assert spec.op_id == "format_date"
    assert (
        call_spec(
            spec,
            datetime(2026, 2, 12, 10, 0, 0, tzinfo=timezone.utc),
            {},
        )
        == "2026-02-12"
    )
    assert call_spec(spec, date(2026, 2, 12), {"out_fmt": "%d/%m/%Y"}) == "12/02/2026"

    with pytest.raises(ValueError):
        call_spec(spec, object(), {})

    with pytest.raises(ValueError):
        call_spec(spec, "2026-02-12", {"out_fmt": 1})
