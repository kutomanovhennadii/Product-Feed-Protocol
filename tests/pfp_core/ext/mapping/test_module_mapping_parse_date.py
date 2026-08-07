from datetime import date, datetime

import pytest

from pfp_core.ext.ext_types import MISSING
from pfp_core.ext.mapping.module_mapping_parse_date import get_spec
from tests.pfp_core.ext.mapping._helpers import call_spec


def test_module_mapping_parse_date_parses_valid_inputs() -> None:
    """parse_date converts valid string/date/datetime inputs to date."""
    spec = get_spec()
    assert spec.op_id == "parse_date"
    assert call_spec(spec, "2026-02-12", {}).isoformat() == "2026-02-12"
    assert call_spec(spec, date(2026, 2, 12), {}).isoformat() == "2026-02-12"
    assert (
        call_spec(spec, datetime(2026, 2, 12, 10, 0, 0), {}).isoformat() == "2026-02-12"
    )
    assert (
        call_spec(spec, "12.02.2026", {"fmt": "%d.%m.%Y"}).isoformat() == "2026-02-12"
    )
    assert call_spec(spec, MISSING, {}) is MISSING
    assert call_spec(spec, None, {}) is None


def test_module_mapping_parse_date_rejects_invalid_inputs() -> None:
    """parse_date raises ValueError for unsupported values and format args."""
    spec = get_spec()
    assert spec.op_id == "parse_date"
    with pytest.raises(ValueError):
        call_spec(spec, object(), {})

    with pytest.raises(ValueError):
        call_spec(spec, "2026-02-12", {"fmt": 123})

    with pytest.raises(ValueError):
        call_spec(spec, "12/02/2026", {})
