"""Tests for publishing/clients/noop_client.py."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pfp_runtime.publishing.clients.client_contract import (
    DeliveryClient,
    DeliveryResult,
)
from pfp_runtime.publishing.clients.noop_client import NoopClient, NoopClientIaC

# ---------------------------------------------------------------------------
# NoopClientIaC
# ---------------------------------------------------------------------------


def test_iac_model_validate_empty_dict() -> None:
    """NoopClientIaC.model_validate({}) succeeds without error."""
    iac = NoopClientIaC.model_validate({})
    assert isinstance(iac, NoopClientIaC)


def test_iac_extra_fields_forbidden() -> None:
    """NoopClientIaC.model_validate({'x': 1}) raises ValidationError."""
    with pytest.raises(ValidationError):
        NoopClientIaC.model_validate({"x": 1})


# ---------------------------------------------------------------------------
# NoopClient construction
# ---------------------------------------------------------------------------


def test_init_accepts_iac() -> None:
    """NoopClient(iac) is constructed without error."""
    iac = NoopClientIaC.model_validate({})
    client = NoopClient(iac)
    assert isinstance(client, NoopClient)


# ---------------------------------------------------------------------------
# Protocol methods
# ---------------------------------------------------------------------------


def test_open_does_not_raise() -> None:
    """open() completes without raising."""
    iac = NoopClientIaC.model_validate({})
    client = NoopClient(iac)
    client.open()


def test_send_chunk_does_not_raise() -> None:
    """send_chunk(b'data') completes without raising."""
    iac = NoopClientIaC.model_validate({})
    client = NoopClient(iac)
    client.send_chunk(b"data")


def test_send_chunk_empty_bytes() -> None:
    """send_chunk(b'') completes without raising."""
    iac = NoopClientIaC.model_validate({})
    client = NoopClient(iac)
    client.send_chunk(b"")


# ---------------------------------------------------------------------------
# finalize
# ---------------------------------------------------------------------------


def test_finalize_returns_skipped_result() -> None:
    """finalize() returns DeliveryResult(skipped=True, status_code=None)."""
    iac = NoopClientIaC.model_validate({})
    client = NoopClient(iac)
    result = client.finalize()
    assert result == DeliveryResult(skipped=True, status_code=None)


def test_finalize_result_is_frozen() -> None:
    """Attempt to mutate the finalize() result raises FrozenInstanceError."""
    iac = NoopClientIaC.model_validate({})
    client = NoopClient(iac)
    result = client.finalize()
    with pytest.raises(AttributeError):
        result.skipped = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


def test_satisfies_delivery_client_protocol() -> None:
    """isinstance(NoopClient(iac), DeliveryClient) is True."""
    iac = NoopClientIaC.model_validate({})
    client = NoopClient(iac)
    assert isinstance(client, DeliveryClient)


# ---------------------------------------------------------------------------
# Full cycle
# ---------------------------------------------------------------------------


def test_full_cycle() -> None:
    """open() -> send_chunk() x2 -> finalize() completes and returns skipped result."""
    iac = NoopClientIaC.model_validate({})
    client = NoopClient(iac)
    client.open()
    client.send_chunk(b"a")
    client.send_chunk(b"b")
    result = client.finalize()
    assert result.skipped is True
    assert result.status_code is None
