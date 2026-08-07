"""Tests for publishing/clients/client_contract.py."""

from __future__ import annotations

import pytest

from pfp_runtime.publishing.clients.client_contract import (
    DeliveryClient,
    DeliveryResult,
)

# ---------------------------------------------------------------------------
# DeliveryResult
# ---------------------------------------------------------------------------


def test_delivery_result_skipped_defaults_status_code_to_none() -> None:
    """Verify DeliveryResult(skipped=True) sets status_code to None by default."""
    result = DeliveryResult(skipped=True)
    assert result.skipped is True
    assert result.status_code is None


def test_delivery_result_with_status_code() -> None:
    """Verify DeliveryResult(skipped=False, status_code=200) stores both fields correctly."""
    result = DeliveryResult(skipped=False, status_code=200)
    assert result.skipped is False
    assert result.status_code == 200


def test_delivery_result_is_frozen() -> None:
    """Verify DeliveryResult raises AttributeError on field mutation (frozen dataclass)."""
    result = DeliveryResult(skipped=True)
    with pytest.raises(AttributeError):
        result.status_code = 500  # type: ignore[misc]


# ---------------------------------------------------------------------------
# DeliveryClient Protocol (duck typing via runtime_checkable)
# ---------------------------------------------------------------------------


def test_delivery_client_protocol_accepts_valid_stub() -> None:
    """Verify class implementing open/send_chunk/finalize passes isinstance check."""

    class StubClient:
        def open(self) -> None:
            pass

        def send_chunk(self, chunk: bytes) -> None:
            pass

        def finalize(self) -> DeliveryResult:
            return DeliveryResult(skipped=True)

    assert isinstance(StubClient(), DeliveryClient)


def test_delivery_client_protocol_rejects_missing_method() -> None:
    """Verify class missing send_chunk() fails isinstance check against DeliveryClient."""

    class IncompleteClient:
        def open(self) -> None:
            pass

        def finalize(self) -> DeliveryResult:
            return DeliveryResult(skipped=True)

    assert not isinstance(IncompleteClient(), DeliveryClient)
