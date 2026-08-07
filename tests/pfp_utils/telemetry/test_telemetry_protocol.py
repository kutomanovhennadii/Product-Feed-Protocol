"""Tests for telemetry protocol contract."""

from unittest.mock import Mock

from pfp_utils.telemetry import TelemetryHandler


def test_telemetry_handler_protocol_is_usable_with_mock() -> None:
    """Allow creating mocks with the TelemetryHandler protocol as spec."""
    Mock(spec=TelemetryHandler)
