"""Tests for publishing/clients/streaming_http_client.py."""

from __future__ import annotations

import sys
import threading
from typing import Any, Dict, Iterator
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from pfp_runtime.publishing.clients.client_contract import (
    DeliveryClient,
    DeliveryResult,
)
from pfp_runtime.publishing.clients.http_client import HttpClientIaC
from pfp_runtime.publishing.clients.streaming_http_client import (
    StreamingHttpClientError,
    StreamingHttpDeliveryClient,
)
from pfp_runtime.publishing.support.transport_policy import TlsTransportPolicy

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_iac(**kwargs: Any) -> HttpClientIaC:
    defaults: Dict[str, Any] = {
        "endpoint": "https://example.com/stream",
    }
    defaults.update(kwargs)
    return HttpClientIaC.model_validate(defaults)


def _make_consuming_mock(status_code: int = 200) -> MagicMock:
    """Return a mock httpx.Client whose post() consumes the content generator."""
    mock = MagicMock()

    def post_side_effect(url: str, content: Iterator[bytes] = None, **kwargs: Any) -> MagicMock:  # type: ignore[assignment]
        if content is not None:
            list(content)  # drain the generator so the thread can exit cleanly
        return MagicMock(status_code=status_code)

    mock.post.side_effect = post_side_effect
    return mock


def _make_non_consuming_mock(status_code: int = 200) -> MagicMock:
    """Return a mock httpx.Client whose post() returns immediately without draining."""
    mock = MagicMock()
    mock.post.return_value = MagicMock(status_code=status_code)
    return mock


def _make_client(
    iac: HttpClientIaC, *, consuming: bool = True, status_code: int = 200
) -> StreamingHttpDeliveryClient:
    httpx = (
        _make_consuming_mock(status_code)
        if consuming
        else _make_non_consuming_mock(status_code)
    )
    return StreamingHttpDeliveryClient(iac, httpx_client=httpx)


# ---------------------------------------------------------------------------
# IaC validation (shared with HttpDeliveryClient via HttpClientIaC)
# ---------------------------------------------------------------------------


def test_iac_endpoint_required() -> None:
    """Verify endpoint is required for the shared IaC."""
    with pytest.raises(ValidationError):
        HttpClientIaC.model_validate({})


def test_iac_both_auth_refs_forbidden() -> None:
    """Verify api_key_ref and token_ref simultaneously raises ValidationError."""
    with pytest.raises(ValidationError):
        _make_iac(
            api_key_ref={"kind": "env", "value": "A"},
            token_ref={"kind": "env", "value": "B"},
        )


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------


def test_init_secret_resolution_failure_raises_error(monkeypatch: Any) -> None:
    """Verify SecretResolutionError in __init__ is wrapped in StreamingHttpClientError."""
    iac = _make_iac(api_key_ref={"kind": "env", "value": "MISSING_VAR"})
    monkeypatch.delenv("MISSING_VAR", raising=False)
    with pytest.raises(
        StreamingHttpClientError, match="Failed to resolve HTTP client secret"
    ):
        StreamingHttpDeliveryClient(iac, httpx_client=MagicMock())


def test_init_auth_header_from_api_key(monkeypatch: Any) -> None:
    """Verify Bearer header is built from api_key_ref."""
    monkeypatch.setenv("STREAM_KEY", "key-abc")
    iac = _make_iac(api_key_ref={"kind": "env", "value": "STREAM_KEY"})
    client = StreamingHttpDeliveryClient(iac, httpx_client=MagicMock())
    assert client._auth_header == {"Authorization": "Bearer key-abc"}


def test_init_auth_header_from_token_ref(monkeypatch: Any) -> None:
    """Verify Bearer header is built from token_ref."""
    monkeypatch.setenv("STREAM_TOKEN", "tok-xyz")
    iac = _make_iac(token_ref={"kind": "env", "value": "STREAM_TOKEN"})
    client = StreamingHttpDeliveryClient(iac, httpx_client=MagicMock())
    assert client._auth_header == {"Authorization": "Bearer tok-xyz"}


# ---------------------------------------------------------------------------
# open()
# ---------------------------------------------------------------------------


def test_open_starts_background_thread() -> None:
    """Verify open() launches the background streaming thread."""
    # Use consuming mock: the thread blocks on queue.get() while draining the generator,
    # so is_alive() is True until we put the sentinel via finalize().
    client = _make_client(_make_iac(), consuming=True)
    assert client._thread is None
    client.open()
    assert client._thread is not None
    # Thread is alive — blocked inside the generator waiting for the next chunk/sentinel
    assert client._thread.is_alive()
    client.finalize()  # sends sentinel → thread exits


def test_double_open_terminates_previous_thread() -> None:
    """Verify second open() terminates the first thread and starts a fresh one."""
    client = _make_client(_make_iac(), consuming=False)
    client.open()
    first_thread = client._thread
    # second open without calling finalize — should terminate first cycle
    client.open()
    if first_thread is not None:
        first_thread.join(timeout=2.0)
        assert not first_thread.is_alive()
    client.finalize()


def test_double_open_with_live_thread_sends_sentinel() -> None:
    """Verify second open() sends sentinel and joins a still-live thread."""
    # consuming mock keeps thread alive (blocks on queue.get() inside list(content))
    client = _make_client(_make_iac(), consuming=True)
    client.open()
    first_thread = client._thread
    assert first_thread is not None
    assert first_thread.is_alive()
    # second open should send sentinel, join first thread, then start fresh
    client.open()
    first_thread.join(timeout=2.0)
    assert not first_thread.is_alive()
    client.finalize()


def test_open_resets_finalized_flag() -> None:
    """Verify open() allows a new cycle after finalize()."""
    client = _make_client(_make_iac())
    client.open()
    client.finalize()
    assert client._finalized is True
    client.open()
    assert client._finalized is False
    client.finalize()


# ---------------------------------------------------------------------------
# send_chunk()
# ---------------------------------------------------------------------------


def test_send_chunk_before_open_raises() -> None:
    """Verify send_chunk() before open() raises StreamingHttpClientError."""
    client = _make_client(_make_iac())
    with pytest.raises(StreamingHttpClientError, match="before open"):
        client.send_chunk(b"data")


def test_send_chunk_after_finalize_raises() -> None:
    """Verify send_chunk() after finalize() raises StreamingHttpClientError."""
    client = _make_client(_make_iac())
    client.open()
    client.finalize()
    with pytest.raises(StreamingHttpClientError, match="after finalize"):
        client.send_chunk(b"late")


def test_send_chunk_puts_data_in_queue() -> None:
    """Verify send_chunk() enqueues the chunk (verifiable via full cycle)."""
    received: list = []
    mock = MagicMock()

    def post_side_effect(url: str, content: Any = None, **kwargs: Any) -> MagicMock:
        if content is not None:
            received.extend(content)
        return MagicMock(status_code=200)

    mock.post.side_effect = post_side_effect
    client = StreamingHttpDeliveryClient(_make_iac(), httpx_client=mock)
    client.open()
    client.send_chunk(b"abc")
    client.finalize()
    assert b"abc" in received


# ---------------------------------------------------------------------------
# finalize()
# ---------------------------------------------------------------------------


def test_finalize_before_open_raises() -> None:
    """Verify finalize() before open() raises StreamingHttpClientError."""
    client = _make_client(_make_iac())
    with pytest.raises(StreamingHttpClientError, match="before open"):
        client.finalize()


def test_finalize_double_call_raises() -> None:
    """Verify calling finalize() twice raises StreamingHttpClientError."""
    client = _make_client(_make_iac())
    client.open()
    client.finalize()
    with pytest.raises(StreamingHttpClientError, match="already called"):
        client.finalize()


def test_finalize_returns_delivery_result() -> None:
    """Verify finalize() returns DeliveryResult with correct status_code."""
    client = _make_client(_make_iac(), status_code=200)
    client.open()
    result = client.finalize()
    assert isinstance(result, DeliveryResult)
    assert result.skipped is False
    assert result.status_code == 200


def test_finalize_joins_thread() -> None:
    """Verify finalize() waits for the background thread to finish."""
    client = _make_client(_make_iac())
    client.open()
    thread = client._thread
    client.finalize()
    assert thread is not None
    assert not thread.is_alive()


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_finalize_propagates_thread_network_error() -> None:
    """Verify exception raised in background thread is re-raised by finalize()."""
    mock = MagicMock()
    mock.post.side_effect = RuntimeError("connection refused")
    client = StreamingHttpDeliveryClient(_make_iac(), httpx_client=mock)
    client.open()
    with pytest.raises(StreamingHttpClientError, match="connection refused"):
        client.finalize()


def test_finalize_raises_on_4xx_response() -> None:
    """Verify 4xx response from server raises StreamingHttpClientError."""
    client = _make_client(_make_iac(), consuming=False, status_code=400)
    client.open()
    with pytest.raises(StreamingHttpClientError, match="remote_4xx"):
        client.finalize()


def test_finalize_raises_on_5xx_response() -> None:
    """Verify 5xx response raises StreamingHttpClientError (no retry applied)."""
    client = _make_client(_make_iac(), consuming=False, status_code=503)
    client.open()
    with pytest.raises(StreamingHttpClientError, match="remote_5xx"):
        client.finalize()


# ---------------------------------------------------------------------------
# content_type header
# ---------------------------------------------------------------------------


def test_finalize_sends_content_type_header() -> None:
    """Verify Content-Type from IaC is included in the streaming POST headers."""
    received_headers: Dict[str, Any] = {}
    mock = MagicMock()

    def post_side_effect(url: str, content: Any = None, **kwargs: Any) -> MagicMock:
        received_headers.update(kwargs.get("headers", {}))
        if content is not None:
            list(content)
        return MagicMock(status_code=200)

    mock.post.side_effect = post_side_effect
    iac = _make_iac(content_type="application/x-ndjson")
    client = StreamingHttpDeliveryClient(iac, httpx_client=mock)
    client.open()
    client.finalize()
    assert received_headers.get("Content-Type") == "application/x-ndjson"


def test_finalize_no_content_type_header_when_not_set() -> None:
    """Verify Content-Type is absent when content_type is None."""
    received_headers: Dict[str, Any] = {}
    mock = MagicMock()

    def post_side_effect(url: str, content: Any = None, **kwargs: Any) -> MagicMock:
        received_headers.update(kwargs.get("headers", {}))
        if content is not None:
            list(content)
        return MagicMock(status_code=200)

    mock.post.side_effect = post_side_effect
    client = StreamingHttpDeliveryClient(_make_iac(), httpx_client=mock)
    client.open()
    client.finalize()
    assert "Content-Type" not in received_headers


# ---------------------------------------------------------------------------
# httpx client lifecycle
# ---------------------------------------------------------------------------


def test_finalize_does_not_close_injected_httpx_client() -> None:
    """Verify injected httpx client is not closed by finalize()."""
    mock = _make_consuming_mock(200)
    client = StreamingHttpDeliveryClient(_make_iac(), httpx_client=mock)
    client.open()
    client.finalize()
    mock.close.assert_not_called()


def test_open_creates_httpx_client_and_finalize_closes_it(monkeypatch: Any) -> None:
    """Verify prod path: open() creates a fresh httpx.Client, finalize() closes it."""
    mock_client = _make_consuming_mock(200)
    mock_httpx_module = MagicMock()
    mock_httpx_module.Client.return_value = mock_client
    monkeypatch.setitem(sys.modules, "httpx", mock_httpx_module)

    client = StreamingHttpDeliveryClient(_make_iac())
    client.open()
    mock_httpx_module.Client.assert_called_once()
    client.finalize()
    mock_client.close.assert_called_once()


def test_open_close_raises_is_suppressed(monkeypatch: Any) -> None:
    """Verify second open() suppresses exception when closing previous httpx client."""
    first_mock = _make_consuming_mock(200)
    first_mock.close.side_effect = RuntimeError("close failed")
    second_mock = _make_consuming_mock(200)
    mock_httpx_module = MagicMock()
    mock_httpx_module.Client.side_effect = [first_mock, second_mock]
    monkeypatch.setitem(sys.modules, "httpx", mock_httpx_module)

    client = StreamingHttpDeliveryClient(_make_iac())
    # First open creates first_mock; second open WITHOUT finalize still owns first_mock.
    # Second open signals first thread, then tries to close first_mock — must suppress error.
    client.open()
    client.open()  # first_mock.close() raises — must be suppressed
    client.finalize()


def test_finalize_close_raises_is_suppressed(monkeypatch: Any) -> None:
    """Verify finalize() suppresses exception from closing owned httpx client."""
    mock_client = _make_consuming_mock(200)
    mock_client.close.side_effect = RuntimeError("close error")
    mock_httpx_module = MagicMock()
    mock_httpx_module.Client.return_value = mock_client
    monkeypatch.setitem(sys.modules, "httpx", mock_httpx_module)

    client = StreamingHttpDeliveryClient(_make_iac())
    client.open()
    result = client.finalize()  # close() raises — must be suppressed
    assert result.status_code == 200


def test_finalize_raises_when_thread_times_out() -> None:
    """Verify finalize() raises StreamingHttpClientError when thread does not finish."""
    block_event = threading.Event()
    mock = MagicMock()

    def blocking_post(url: str, content: Any = None, **kwargs: Any) -> MagicMock:
        block_event.wait()  # blocks until released
        return MagicMock(status_code=200)

    mock.post.side_effect = blocking_post
    iac = _make_iac(transport=TlsTransportPolicy(timeout_seconds=0.001, max_retries=0))
    client = StreamingHttpDeliveryClient(iac, httpx_client=mock)
    client.open()
    try:
        with pytest.raises(StreamingHttpClientError, match="timed out"):
            client.finalize()
    finally:
        block_event.set()  # release the blocked thread so it can exit cleanly


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


def test_streaming_client_satisfies_protocol() -> None:
    """Verify StreamingHttpDeliveryClient is recognised as DeliveryClient."""
    client = _make_client(_make_iac())
    assert isinstance(client, DeliveryClient)


# ---------------------------------------------------------------------------
# Full cycle
# ---------------------------------------------------------------------------


def test_full_cycle_chunks_delivered_in_order() -> None:
    """Verify open → 3× send_chunk → finalize delivers all chunks in order."""
    received: list = []
    mock = MagicMock()

    def post_side_effect(url: str, content: Any = None, **kwargs: Any) -> MagicMock:
        if content is not None:
            received.extend(content)
        return MagicMock(status_code=200)

    mock.post.side_effect = post_side_effect
    client = StreamingHttpDeliveryClient(_make_iac(), httpx_client=mock)
    client.open()
    client.send_chunk(b"first")
    client.send_chunk(b"second")
    client.send_chunk(b"third")
    result = client.finalize()
    assert received == [b"first", b"second", b"third"]
    assert result.status_code == 200
