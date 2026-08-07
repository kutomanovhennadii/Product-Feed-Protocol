from datetime import datetime, timedelta, timezone

import pytest

from pfp_core.ext.ext_types import MISSING
from pfp_core.ext.mapping.module_mapping_format_datetime_utc import get_spec
from tests.pfp_core.ext.mapping._helpers import call_spec


def test_module_mapping_format_datetime_utc_formats_deterministically() -> None:
    """format_datetime_utc normalizes input to deterministic UTC output."""
    spec = get_spec()
    assert spec.op_id == "format_datetime_utc"
    assert call_spec(spec, "2026-02-12T10:00:00+03:00", {}) == "2026-02-12T07:00:00Z"
    assert (
        call_spec(spec, datetime(2026, 2, 12, 10, 0, 0), {}) == "2026-02-12T10:00:00Z"
    )
    assert (
        call_spec(
            spec,
            datetime(2026, 2, 12, 10, 0, 0, tzinfo=timezone(timedelta(hours=3))),
            {},
        )
        == "2026-02-12T07:00:00Z"
    )
    assert (
        call_spec(spec, "2026-02-12T10:00:00Z", {"out_fmt": "%Y/%m/%d"}) == "2026/02/12"
    )
    assert call_spec(spec, MISSING, {}) is MISSING
    assert call_spec(spec, None, {}) is None


def test_module_mapping_format_datetime_utc_rejects_invalid_inputs() -> None:
    """format_datetime_utc rejects unsupported values and invalid out_fmt args."""
    spec = get_spec()
    assert spec.op_id == "format_datetime_utc"
    with pytest.raises(ValueError):
        call_spec(spec, object(), {})

    with pytest.raises(ValueError):
        call_spec(spec, "2026-02-12T10:00:00Z", {"out_fmt": 1})
