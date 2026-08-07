"""Tests for connector adapter protocol contract."""

from __future__ import annotations

from typing import Any, Mapping, cast
from unittest.mock import Mock

from pfp_runtime.connectors.adapters.adapter_contract import (
    AdapterFormatError,
    FormatAdapter,
)
from pfp_utils.logging.log_pipeline import LogPipeline


class _StubAdapter:
    format_name = "rows"
    constants: Mapping[str, Any]

    def __init__(
        self,
        constants: Mapping[str, Any],
        *,
        log_pipeline: LogPipeline,
    ) -> None:
        self.constants = constants
        self.log_pipeline = log_pipeline

    def parse(self, raw_input: Any) -> list[dict[str, Any]]:
        return [{"payload": raw_input, "limit": self.constants["limit"]}]


def test_adapter_format_error_is_value_error() -> None:
    """Adapter format errors remain value errors for caller compatibility."""

    assert issubclass(AdapterFormatError, ValueError)


def test_format_adapter_protocol_shape_is_usable_by_runtime_code() -> None:
    """Concrete adapters can satisfy the documented protocol surface."""

    adapter: FormatAdapter = _StubAdapter(
        {"limit": 10},
        log_pipeline=cast(LogPipeline, Mock()),
    )

    assert adapter.format_name == "rows"
    assert list(adapter.parse("input")) == [{"payload": "input", "limit": 10}]
