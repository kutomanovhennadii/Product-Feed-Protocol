"""Tests for publishing/clients/http_client.py."""

from __future__ import annotations

import sys
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from pfp_runtime.publishing.clients.client_contract import (
    DeliveryClient,
    DeliveryResult,
)
from pfp_runtime.publishing.clients.http_client import (
    HttpClientError,
    HttpClientIaC,
    HttpDeliveryClient,
)
from pfp_runtime.publishing.support.transport_policy import TlsTransportPolicy

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_iac(**kwargs: Any) -> HttpClientIaC:
    defaults: Dict[str, Any] = {
        "endpoint": "https://example.com/feed",
    }
    defaults.update(kwargs)
    return HttpClientIaC.model_validate(defaults)


def _make_mock_httpx(status_code: int = 200) -> MagicMock:
    """Return a mock httpx.Client whose post() returns a response with status_code."""
    mock = MagicMock()
    mock.post.return_value = MagicMock(status_code=status_code)
    return mock


def _make_client(iac: HttpClientIaC, status_code: int = 200) -> HttpDeliveryClient:
    return HttpDeliveryClient(iac, httpx_client=_make_mock_httpx(status_code))


# ---------------------------------------------------------------------------
# IaC validation
# ---------------------------------------------------------------------------


def test_iac_endpoint_required() -> None:
    """Verify endpoint is required."""
    with pytest.raises(ValidationError):
        HttpClientIaC.model_validate({})


def test_iac_both_auth_refs_forbidden() -> None:
    """Verify api_key_ref and token_ref simultaneously raises ValidationError."""
    with pytest.raises(ValidationError):
        _make_iac(
            api_key_ref={"kind": "env", "value": "API_KEY"},
            token_ref={"kind": "env", "value": "TOKEN"},
        )


def test_iac_transport_optional() -> None:
    """Verify transport block is fully optional (uses defaults)."""
    iac = _make_iac()
    assert iac.transport.timeout_seconds == 60.0
    assert iac.transport.max_retries == 3


def test_iac_extra_field_forbidden() -> None:
    """Verify extra fields raise ValidationError."""
    with pytest.raises(ValidationError):
        _make_iac(unknown_field="x")


def test_iac_no_auth_allowed() -> None:
    """Verify neither api_key_ref nor token_ref is valid (no auth)."""
    iac = _make_iac()
    assert iac.api_key_ref is None
    assert iac.token_ref is None


def test_iac_max_body_bytes_default() -> None:
    """Verify max_body_bytes defaults to 100 MB."""
    assert _make_iac().max_body_bytes == 100 * 1024 * 1024


def test_iac_max_body_bytes_custom() -> None:
    """Verify max_body_bytes accepts a custom value."""
    iac = _make_iac(max_body_bytes=50 * 1024 * 1024)
    assert iac.max_body_bytes == 50 * 1024 * 1024


def test_iac_max_body_bytes_zero_forbidden() -> None:
    """Verify max_body_bytes=0 raises ValidationError."""
    with pytest.raises(ValidationError):
        _make_iac(max_body_bytes=0)


def test_iac_content_type_default_none() -> None:
    """Verify content_type defaults to None."""
    assert _make_iac().content_type is None


def test_iac_content_type_stored() -> None:
    """Verify content_type is accepted and stored on IaC."""
    iac = _make_iac(content_type="application/x-ndjson")
    assert iac.content_type == "application/x-ndjson"


# ---------------------------------------------------------------------------
# __init__ — secret resolution and auth header
# ---------------------------------------------------------------------------


def test_init_no_auth_empty_header(monkeypatch: Any) -> None:
    """Verify empty auth header when no auth refs configured."""
    iac = _make_iac()
    client = HttpDeliveryClient(iac, httpx_client=MagicMock())
    assert client._auth_header == {}


def test_init_api_key_auth(monkeypatch: Any) -> None:
    """Verify Authorization: Bearer header built from api_key_ref."""
    monkeypatch.setenv("API_KEY", "sk-test-123")
    iac = _make_iac(api_key_ref={"kind": "env", "value": "API_KEY"})
    client = HttpDeliveryClient(iac, httpx_client=MagicMock())
    assert client._auth_header == {"Authorization": "Bearer sk-test-123"}


def test_init_token_auth(monkeypatch: Any) -> None:
    """Verify Authorization: Bearer header built from token_ref."""
    monkeypatch.setenv("BEARER_TOKEN", "my-oauth-token")
    iac = _make_iac(token_ref={"kind": "env", "value": "BEARER_TOKEN"})
    client = HttpDeliveryClient(iac, httpx_client=MagicMock())
    assert client._auth_header == {"Authorization": "Bearer my-oauth-token"}


def test_init_secret_resolution_failure_raises_http_error(monkeypatch: Any) -> None:
    """Verify SecretResolutionError in __init__ is wrapped in HttpClientError."""
    iac = _make_iac(api_key_ref={"kind": "env", "value": "MISSING_VAR"})
    monkeypatch.delenv("MISSING_VAR", raising=False)
    with pytest.raises(HttpClientError, match="Failed to resolve HTTP client secret"):
        HttpDeliveryClient(iac, httpx_client=MagicMock())


# ---------------------------------------------------------------------------
# open()
# ---------------------------------------------------------------------------


def test_open_initialises_buffer() -> None:
    """Verify open() creates an empty buffer."""
    client = _make_client(_make_iac())
    assert client._buffer is None
    client.open()
    assert client._buffer is not None


def test_open_resets_finalized_flag() -> None:
    """Verify open() clears _finalized so next cycle can proceed."""
    client = _make_client(_make_iac())
    client.open()
    client.send_chunk(b"x")
    client.finalize()
    assert client._finalized is True
    client.open()
    assert client._finalized is False


def test_double_open_clears_previous_buffer() -> None:
    """Verify calling open() twice discards the first buffer's content."""
    client = _make_client(_make_iac())
    client.open()
    client.send_chunk(b"old data")
    client.open()
    client.send_chunk(b"new")
    # finalize will POST only "new"
    client.finalize()
    posted_body = client._httpx_client.post.call_args[1]["content"]
    assert posted_body == b"new"


# ---------------------------------------------------------------------------
# send_chunk()
# ---------------------------------------------------------------------------


def test_send_chunk_before_open_raises() -> None:
    """Verify send_chunk() before open() raises HttpClientError."""
    client = _make_client(_make_iac())
    with pytest.raises(HttpClientError, match="before open"):
        client.send_chunk(b"data")


def test_send_chunk_after_finalize_raises() -> None:
    """Verify send_chunk() after finalize() raises HttpClientError."""
    client = _make_client(_make_iac())
    client.open()
    client.finalize()
    with pytest.raises(HttpClientError, match="after finalize"):
        client.send_chunk(b"late")


def test_send_chunk_raises_when_payload_exceeds_max_body_bytes() -> None:
    """Verify send_chunk() raises HttpClientError when buffer would exceed max_body_bytes."""
    client = _make_client(_make_iac(max_body_bytes=10))
    client.open()
    with pytest.raises(HttpClientError, match="max_body_bytes=10"):
        client.send_chunk(b"12345678901")  # 11 bytes > 10


def test_send_chunk_at_max_body_bytes_is_allowed() -> None:
    """Verify send_chunk() succeeds when total equals exactly max_body_bytes."""
    client = _make_client(_make_iac(max_body_bytes=10))
    client.open()
    client.send_chunk(b"1234567890")  # exactly 10 bytes — allowed


def test_send_chunk_limit_error_recommends_streaming() -> None:
    """Verify the limit error message mentions http_streaming."""
    client = _make_client(_make_iac(max_body_bytes=5))
    client.open()
    with pytest.raises(HttpClientError, match="http_streaming"):
        client.send_chunk(b"123456")


def test_send_chunk_cumulative_chunks_trigger_limit() -> None:
    """Verify limit is checked against the cumulative buffer, not per-chunk size."""
    client = _make_client(_make_iac(max_body_bytes=10))
    client.open()
    client.send_chunk(b"12345")  # 5 bytes — ok
    client.send_chunk(b"67890")  # 5 bytes — ok (total = 10, at limit)
    with pytest.raises(HttpClientError, match="max_body_bytes=10"):
        client.send_chunk(b"x")  # 1 byte — pushes to 11, fails


def test_send_chunk_accumulates_data() -> None:
    """Verify multiple send_chunk() calls accumulate bytes in the buffer."""
    client = _make_client(_make_iac())
    client.open()
    client.send_chunk(b"aa")
    client.send_chunk(b"bb")
    assert client._buffer is not None
    assert client._buffer.getvalue() == b"aabb"


# ---------------------------------------------------------------------------
# finalize()
# ---------------------------------------------------------------------------


def test_finalize_before_open_raises() -> None:
    """Verify finalize() before open() raises HttpClientError."""
    client = _make_client(_make_iac())
    with pytest.raises(HttpClientError, match="before open"):
        client.finalize()


def test_finalize_double_call_raises() -> None:
    """Verify calling finalize() twice raises HttpClientError."""
    client = _make_client(_make_iac())
    client.open()
    client.finalize()
    with pytest.raises(HttpClientError, match="already called"):
        client.finalize()


def test_finalize_posts_correct_body() -> None:
    """Verify finalize() POSTs the concatenated chunk bytes as the body."""
    mock_httpx = _make_mock_httpx(200)
    iac = _make_iac()
    client = HttpDeliveryClient(iac, httpx_client=mock_httpx)
    client.open()
    client.send_chunk(b"hello ")
    client.send_chunk(b"world")
    client.finalize()
    call_kwargs = mock_httpx.post.call_args
    assert call_kwargs[1]["content"] == b"hello world"


def test_finalize_posts_to_correct_endpoint() -> None:
    """Verify finalize() POSTs to the configured endpoint URL."""
    mock_httpx = _make_mock_httpx(200)
    iac = _make_iac(endpoint="https://api.example.com/v1/feed")
    client = HttpDeliveryClient(iac, httpx_client=mock_httpx)
    client.open()
    client.finalize()
    url_arg = mock_httpx.post.call_args[0][0]
    assert url_arg == "https://api.example.com/v1/feed"


def test_finalize_sends_auth_header(monkeypatch: Any) -> None:
    """Verify finalize() includes the Authorization header."""
    monkeypatch.setenv("MY_KEY", "secret-value")
    mock_httpx = _make_mock_httpx(200)
    iac = _make_iac(api_key_ref={"kind": "env", "value": "MY_KEY"})
    client = HttpDeliveryClient(iac, httpx_client=mock_httpx)
    client.open()
    client.finalize()
    headers = mock_httpx.post.call_args[1]["headers"]
    assert headers == {"Authorization": "Bearer secret-value"}


def test_finalize_returns_delivery_result_with_status() -> None:
    """Verify finalize() returns DeliveryResult with correct status_code."""
    client = _make_client(_make_iac())
    client.open()
    result = client.finalize()
    assert isinstance(result, DeliveryResult)
    assert result.skipped is False
    assert result.status_code == 200


# ---------------------------------------------------------------------------
# Retry and error handling
# ---------------------------------------------------------------------------


def test_finalize_retries_on_5xx_then_succeeds() -> None:
    """Verify 5xx response triggers retry and succeeds on next attempt."""
    iac = _make_iac(
        transport=TlsTransportPolicy(
            timeout_seconds=10.0, max_retries=3, retry_backoff_seconds=0.0
        )
    )
    mock_httpx = MagicMock()
    calls = [0]

    def post_side_effect(url: str, **kwargs: Any) -> MagicMock:
        calls[0] += 1
        if calls[0] < 3:
            return MagicMock(status_code=500)
        return MagicMock(status_code=200)

    mock_httpx.post.side_effect = post_side_effect
    client = HttpDeliveryClient(iac, httpx_client=mock_httpx)
    client.open()
    result = client.finalize()
    assert result.status_code == 200
    assert calls[0] == 3


def test_finalize_raises_after_all_5xx_retries_exhausted() -> None:
    """Verify HttpClientError raised when 5xx persists across all retries."""
    iac = _make_iac(
        transport=TlsTransportPolicy(
            timeout_seconds=10.0, max_retries=2, retry_backoff_seconds=0.0
        )
    )
    mock_httpx = MagicMock()
    mock_httpx.post.return_value = MagicMock(status_code=503)
    client = HttpDeliveryClient(iac, httpx_client=mock_httpx)
    client.open()
    with pytest.raises(HttpClientError):
        client.finalize()
    assert mock_httpx.post.call_count == 3  # 1 initial + 2 retries


def test_finalize_does_not_retry_on_4xx() -> None:
    """Verify 4xx response is not retried and raises HttpClientError."""
    iac = _make_iac(
        transport=TlsTransportPolicy(
            timeout_seconds=10.0, max_retries=3, retry_backoff_seconds=0.0
        )
    )
    mock_httpx = MagicMock()
    mock_httpx.post.return_value = MagicMock(status_code=403)
    client = HttpDeliveryClient(iac, httpx_client=mock_httpx)
    client.open()
    with pytest.raises(HttpClientError):
        client.finalize()
    assert mock_httpx.post.call_count == 1  # no retry


def test_finalize_raises_on_network_error() -> None:
    """Verify network exception from httpx is wrapped in HttpClientError."""
    mock_httpx = MagicMock()
    mock_httpx.post.side_effect = RuntimeError("connection refused")
    client = HttpDeliveryClient(_make_iac(), httpx_client=mock_httpx)
    client.open()
    with pytest.raises(HttpClientError):
        client.finalize()


# ---------------------------------------------------------------------------
# content_type header
# ---------------------------------------------------------------------------


def test_finalize_sends_content_type_header(monkeypatch: Any) -> None:
    """Verify Content-Type from IaC is included in the POST headers."""
    mock_httpx = _make_mock_httpx(200)
    iac = _make_iac(content_type="application/x-ndjson")
    client = HttpDeliveryClient(iac, httpx_client=mock_httpx)
    client.open()
    client.finalize()
    headers = mock_httpx.post.call_args[1]["headers"]
    assert headers.get("Content-Type") == "application/x-ndjson"


def test_finalize_no_content_type_header_when_not_set() -> None:
    """Verify Content-Type is absent from POST headers when content_type is None."""
    mock_httpx = _make_mock_httpx(200)
    client = HttpDeliveryClient(_make_iac(), httpx_client=mock_httpx)
    client.open()
    client.finalize()
    headers = mock_httpx.post.call_args[1]["headers"]
    assert "Content-Type" not in headers


# ---------------------------------------------------------------------------
# httpx client lifecycle
# ---------------------------------------------------------------------------


def test_finalize_does_not_close_injected_httpx_client() -> None:
    """Verify injected httpx client is not closed by finalize()."""
    mock_httpx = _make_mock_httpx(200)
    client = HttpDeliveryClient(_make_iac(), httpx_client=mock_httpx)
    client.open()
    client.finalize()
    mock_httpx.close.assert_not_called()


def test_open_creates_httpx_client_and_finalize_closes_it(monkeypatch: Any) -> None:
    """Verify prod path: open() creates a fresh httpx.Client, finalize() closes it."""
    mock_client = MagicMock()
    mock_client.post.return_value = MagicMock(status_code=200)
    mock_httpx_module = MagicMock()
    mock_httpx_module.Client.return_value = mock_client
    monkeypatch.setitem(sys.modules, "httpx", mock_httpx_module)

    client = HttpDeliveryClient(_make_iac())
    client.open()
    mock_httpx_module.Client.assert_called_once()
    client.finalize()
    mock_client.close.assert_called_once()


def test_double_open_closes_previous_httpx_client(monkeypatch: Any) -> None:
    """Verify second open() closes the client created by the first open()."""
    first_mock = MagicMock()
    first_mock.post.return_value = MagicMock(status_code=200)
    second_mock = MagicMock()
    second_mock.post.return_value = MagicMock(status_code=200)
    mock_httpx_module = MagicMock()
    mock_httpx_module.Client.side_effect = [first_mock, second_mock]
    monkeypatch.setitem(sys.modules, "httpx", mock_httpx_module)

    client = HttpDeliveryClient(_make_iac())
    client.open()
    client.open()  # should close first_mock and create second_mock
    first_mock.close.assert_called_once()
    client.finalize()


def test_open_close_raises_is_suppressed(monkeypatch: Any) -> None:
    """Verify second open() suppresses exception from closing previous httpx client."""
    first_mock = MagicMock()
    first_mock.close.side_effect = RuntimeError("close failed")
    second_mock = MagicMock()
    second_mock.post.return_value = MagicMock(status_code=200)
    mock_httpx_module = MagicMock()
    mock_httpx_module.Client.side_effect = [first_mock, second_mock]
    monkeypatch.setitem(sys.modules, "httpx", mock_httpx_module)

    client = HttpDeliveryClient(_make_iac())
    client.open()
    client.open()  # first_mock.close() raises — must be suppressed
    client.finalize()


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


def test_http_client_satisfies_protocol() -> None:
    """Verify HttpDeliveryClient is recognised as DeliveryClient."""
    client = _make_client(_make_iac())
    assert isinstance(client, DeliveryClient)


# ---------------------------------------------------------------------------
# Full cycle
# ---------------------------------------------------------------------------


def test_full_cycle_body_is_concatenation_of_chunks() -> None:
    """Verify open → 3× send_chunk → finalize sends exactly the concatenated bytes."""
    mock_httpx = _make_mock_httpx(201)
    client = HttpDeliveryClient(_make_iac(), httpx_client=mock_httpx)
    client.open()
    client.send_chunk(b"chunk1")
    client.send_chunk(b"chunk2")
    client.send_chunk(b"chunk3")
    result = client.finalize()
    posted_body = mock_httpx.post.call_args[1]["content"]
    assert posted_body == b"chunk1chunk2chunk3"
    assert result.status_code == 201
