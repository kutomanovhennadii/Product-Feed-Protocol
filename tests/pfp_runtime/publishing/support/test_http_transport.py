"""Tests for HttpTransport — reusable HTTP transport layer."""

from __future__ import annotations

import os
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from pfp_runtime.publishing.support.http_transport import (
    HttpTransport,
    HttpTransportError,
)
from pfp_runtime.publishing.support.transport_policy import TlsTransportPolicy
from pfp_utils.security import SecretRef

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_policy(**kwargs: Any) -> TlsTransportPolicy:
    """Build a TlsTransportPolicy with sensible test defaults."""
    defaults: Dict[str, Any] = {
        "timeout_seconds": 30.0,
        "max_retries": 2,
        "retry_backoff_seconds": 0.0,
        "verify_tls": True,
    }
    defaults.update(kwargs)
    return TlsTransportPolicy.model_validate(defaults)


def _make_mock_httpx(status_code: int = 200) -> MagicMock:
    """Return a mock httpx.Client whose post()/get() return a response."""
    mock = MagicMock()
    resp = MagicMock(status_code=status_code)
    mock.post.return_value = resp
    mock.get.return_value = resp
    return mock


def _make_transport(status_code: int = 200, **kwargs: Any) -> HttpTransport:
    """Build an HttpTransport with a mock httpx client returning status_code."""
    policy = kwargs.pop("policy", _make_policy())
    httpx_client = kwargs.pop("httpx_client", _make_mock_httpx(status_code))
    return HttpTransport(policy, httpx_client=httpx_client, **kwargs)


def _env_secret_ref(name: str) -> SecretRef:
    """Build a canonical env-backed SecretRef for auth tests."""
    return SecretRef(kind="env", value=name)


# ---------------------------------------------------------------------------
# Construction — auth resolution
# ---------------------------------------------------------------------------


class TestHttpTransportConstruction:
    """Auth header resolution and validation at __init__ time."""

    def test_no_auth(self) -> None:
        """Transport without auth has no Authorization header."""
        transport = _make_transport()
        assert "Authorization" not in transport._base_headers

    def test_api_key_ref(self) -> None:
        """api_key_ref resolves to Bearer token header."""
        with patch.dict(os.environ, {"TEST_API_KEY": "sk-secret"}):
            transport = HttpTransport(
                _make_policy(),
                api_key_ref=_env_secret_ref("TEST_API_KEY"),
                httpx_client=_make_mock_httpx(),
            )
        assert transport._base_headers["Authorization"] == "Bearer sk-secret"

    def test_token_ref(self) -> None:
        """token_ref resolves to Bearer token header."""
        with patch.dict(os.environ, {"TEST_TOKEN": "tok-abc"}):
            transport = HttpTransport(
                _make_policy(),
                token_ref=_env_secret_ref("TEST_TOKEN"),
                httpx_client=_make_mock_httpx(),
            )
        assert transport._base_headers["Authorization"] == "Bearer tok-abc"

    def test_both_auth_refs_rejected(self) -> None:
        """Providing both api_key_ref and token_ref raises HttpTransportError."""
        with pytest.raises(HttpTransportError, match="at most one"):
            HttpTransport(
                _make_policy(),
                api_key_ref=_env_secret_ref("K"),
                token_ref=_env_secret_ref("T"),
                httpx_client=_make_mock_httpx(),
            )

    def test_secret_resolution_failure(self) -> None:
        """Unresolvable secret raises HttpTransportError."""
        with patch.dict(os.environ, {}, clear=False):
            # Ensure the env var does not exist
            os.environ.pop("NONEXISTENT_SECRET_KEY", None)
            with pytest.raises(HttpTransportError, match="Failed to resolve"):
                HttpTransport(
                    _make_policy(),
                    api_key_ref=_env_secret_ref("NONEXISTENT_SECRET_KEY"),
                    httpx_client=_make_mock_httpx(),
                )

    def test_extra_headers_merged(self) -> None:
        """extra_headers are merged into base headers."""
        transport = HttpTransport(
            _make_policy(),
            extra_headers={"X-Custom": "value", "X-Another": "two"},
            httpx_client=_make_mock_httpx(),
        )
        assert transport._base_headers["X-Custom"] == "value"
        assert transport._base_headers["X-Another"] == "two"

    def test_extra_headers_with_auth(self) -> None:
        """extra_headers coexist with auth header."""
        with patch.dict(os.environ, {"KEY": "secret"}):
            transport = HttpTransport(
                _make_policy(),
                api_key_ref=_env_secret_ref("KEY"),
                extra_headers={"Stripe-Version": "2025-01-01"},
                httpx_client=_make_mock_httpx(),
            )
        assert "Authorization" in transport._base_headers
        assert transport._base_headers["Stripe-Version"] == "2025-01-01"


# ---------------------------------------------------------------------------
# open() / close() lifecycle
# ---------------------------------------------------------------------------


class TestHttpTransportLifecycle:
    """httpx.Client creation and teardown."""

    def test_open_creates_client(self) -> None:
        """open() creates an httpx.Client when none was injected."""
        mock_httpx = MagicMock()
        mock_client = MagicMock()
        mock_httpx.Client.return_value = mock_client
        transport = HttpTransport(_make_policy())
        with patch.dict("sys.modules", {"httpx": mock_httpx}):
            transport.open()
        assert transport._httpx_client is mock_client

    def test_open_noop_with_injected_client(self) -> None:
        """open() is a no-op when httpx_client was injected."""
        mock = _make_mock_httpx()
        transport = HttpTransport(_make_policy(), httpx_client=mock)
        transport.open()
        # Client should remain the same injected mock
        assert transport._httpx_client is mock

    def test_close_releases_owned_client(self) -> None:
        """close() calls .close() on owned client and sets it to None."""
        mock_httpx = MagicMock()
        mock_client = MagicMock()
        mock_httpx.Client.return_value = mock_client
        transport = HttpTransport(_make_policy())
        with patch.dict("sys.modules", {"httpx": mock_httpx}):
            transport.open()
        transport.close()
        mock_client.close.assert_called_once()
        assert transport._httpx_client is None

    def test_close_noop_with_injected_client(self) -> None:
        """close() does nothing when httpx_client was injected."""
        mock = _make_mock_httpx()
        transport = HttpTransport(_make_policy(), httpx_client=mock)
        transport.close()
        mock.close.assert_not_called()
        assert transport._httpx_client is mock

    def test_close_idempotent(self) -> None:
        """Calling close() twice does not raise."""
        transport = _make_transport()
        transport.close()
        transport.close()

    def test_open_closes_previous_owned_client(self) -> None:
        """open() closes previous owned client before creating new one."""
        mock_httpx = MagicMock()
        mock_client_1 = MagicMock()
        mock_client_2 = MagicMock()
        mock_httpx.Client.side_effect = [mock_client_1, mock_client_2]
        transport = HttpTransport(_make_policy())
        with patch.dict("sys.modules", {"httpx": mock_httpx}):
            transport.open()
            transport.open()
        mock_client_1.close.assert_called_once()
        assert transport._httpx_client is mock_client_2

    def test_open_swallows_close_error(self) -> None:
        """open() ignores errors when closing previous owned client."""
        mock_httpx = MagicMock()
        mock_client_1 = MagicMock()
        mock_client_1.close.side_effect = RuntimeError("close failed")
        mock_client_2 = MagicMock()
        mock_httpx.Client.side_effect = [mock_client_1, mock_client_2]
        transport = HttpTransport(_make_policy())
        with patch.dict("sys.modules", {"httpx": mock_httpx}):
            transport.open()
            transport.open()  # should not raise despite close error
        assert transport._httpx_client is mock_client_2

    def test_close_swallows_close_error(self) -> None:
        """close() ignores errors when closing owned client."""
        mock_httpx = MagicMock()
        mock_client = MagicMock()
        mock_client.close.side_effect = RuntimeError("close failed")
        mock_httpx.Client.return_value = mock_client
        transport = HttpTransport(_make_policy())
        with patch.dict("sys.modules", {"httpx": mock_httpx}):
            transport.open()
        transport.close()  # should not raise
        assert transport._httpx_client is None


# ---------------------------------------------------------------------------
# post() — happy path
# ---------------------------------------------------------------------------


class TestHttpTransportPost:
    """POST request execution."""

    def test_post_200(self) -> None:
        """Successful POST returns response."""
        mock = _make_mock_httpx(200)
        transport = _make_transport(httpx_client=mock)
        resp = transport.post("https://example.com/api", b"body")
        mock.post.assert_called_once()
        assert resp.status_code == 200

    def test_post_sends_body_and_headers(self) -> None:
        """POST passes body, auth headers, and content_type."""
        with patch.dict(os.environ, {"K": "secret"}):
            mock = _make_mock_httpx(200)
            transport = HttpTransport(
                _make_policy(),
                api_key_ref=_env_secret_ref("K"),
                httpx_client=mock,
            )
        transport.post(
            "https://example.com/api",
            b"data",
            content_type="application/json",
        )
        call_kwargs = mock.post.call_args
        assert call_kwargs.kwargs["content"] == b"data"
        headers = call_kwargs.kwargs["headers"]
        assert headers["Authorization"] == "Bearer secret"
        assert headers["Content-Type"] == "application/json"

    def test_post_without_content_type(self) -> None:
        """POST without content_type omits Content-Type header."""
        mock = _make_mock_httpx(200)
        transport = _make_transport(httpx_client=mock)
        transport.post("https://example.com/api", b"data")
        headers = mock.post.call_args.kwargs["headers"]
        assert "Content-Type" not in headers

    def test_post_no_retry(self) -> None:
        """POST with retry=False does not retry on 5xx."""
        mock = _make_mock_httpx(500)
        transport = _make_transport(httpx_client=mock)
        with pytest.raises(HttpTransportError, match="HTTP 500"):
            transport.post(
                "https://example.com/api",
                b"data",
                retry=False,
            )
        assert mock.post.call_count == 1


# ---------------------------------------------------------------------------
# post() — retry and error handling
# ---------------------------------------------------------------------------


class TestHttpTransportPostRetry:
    """Retry behaviour on 5xx responses."""

    def test_post_retries_on_5xx(self) -> None:
        """POST retries on 5xx up to max_retries, then raises."""
        mock = _make_mock_httpx(502)
        policy = _make_policy(max_retries=2, retry_backoff_seconds=0.0)
        transport = HttpTransport(policy, httpx_client=mock)
        with pytest.raises(HttpTransportError):
            transport.post("https://example.com/api", b"data")
        # 1 initial + 2 retries = 3 calls
        assert mock.post.call_count == 3

    def test_post_no_retry_on_4xx(self) -> None:
        """POST does not retry on 4xx — raises immediately."""
        mock = _make_mock_httpx(401)
        policy = _make_policy(max_retries=3)
        transport = HttpTransport(policy, httpx_client=mock)
        with pytest.raises(HttpTransportError, match="HTTP 401"):
            transport.post("https://example.com/api", b"data")
        assert mock.post.call_count == 1

    def test_post_recovers_after_5xx(self) -> None:
        """POST retries on 5xx and succeeds on subsequent attempt."""
        mock = _make_mock_httpx()
        resp_502 = MagicMock(status_code=502)
        resp_200 = MagicMock(status_code=200)
        mock.post.side_effect = [resp_502, resp_200]
        policy = _make_policy(max_retries=2, retry_backoff_seconds=0.0)
        transport = HttpTransport(policy, httpx_client=mock)
        resp = transport.post("https://example.com/api", b"data")
        assert resp.status_code == 200
        assert mock.post.call_count == 2

    def test_post_network_error_retried(self) -> None:
        """Network exceptions are retried."""
        mock = _make_mock_httpx()
        mock.post.side_effect = ConnectionError("connection refused")
        policy = _make_policy(max_retries=1, retry_backoff_seconds=0.0)
        transport = HttpTransport(policy, httpx_client=mock)
        with pytest.raises(HttpTransportError, match="retry_exhausted"):
            transport.post("https://example.com/api", b"data")
        # 1 initial + 1 retry = 2 calls
        assert mock.post.call_count == 2


# ---------------------------------------------------------------------------
# post_multipart()
# ---------------------------------------------------------------------------


class TestHttpTransportPostMultipart:
    """Multipart POST request execution."""

    def test_post_multipart_200(self) -> None:
        """Multipart POST returns response on success."""
        mock = _make_mock_httpx(200)
        transport = _make_transport(httpx_client=mock)
        resp = transport.post_multipart(
            "https://files.example.com/upload",
            files={"file": ("data.csv", b"a,b,c", "text/csv")},
            data={"purpose": "upload"},
        )
        assert resp.status_code == 200
        call_kwargs = mock.post.call_args
        assert call_kwargs.kwargs["files"] == {
            "file": ("data.csv", b"a,b,c", "text/csv")
        }
        assert call_kwargs.kwargs["data"] == {"purpose": "upload"}

    def test_post_multipart_retries_on_5xx(self) -> None:
        """Multipart POST retries on 5xx."""
        mock = _make_mock_httpx(503)
        policy = _make_policy(max_retries=1, retry_backoff_seconds=0.0)
        transport = HttpTransport(policy, httpx_client=mock)
        with pytest.raises(HttpTransportError):
            transport.post_multipart(
                "https://files.example.com/upload",
                files={"file": ("x.csv", b"data", "text/csv")},
            )
        assert mock.post.call_count == 2

    def test_post_multipart_no_retry_on_4xx(self) -> None:
        """Multipart POST does not retry on 4xx."""
        mock = _make_mock_httpx(422)
        policy = _make_policy(max_retries=3)
        transport = HttpTransport(policy, httpx_client=mock)
        with pytest.raises(HttpTransportError, match="HTTP 422"):
            transport.post_multipart(
                "https://files.example.com/upload",
                data={"key": "val"},
            )
        assert mock.post.call_count == 1

    def test_post_multipart_no_retry(self) -> None:
        """Multipart POST with retry=False does not retry."""
        mock = _make_mock_httpx(500)
        transport = _make_transport(httpx_client=mock)
        with pytest.raises(HttpTransportError):
            transport.post_multipart(
                "https://files.example.com/upload",
                files={"file": ("x.csv", b"data", "text/csv")},
                retry=False,
            )
        assert mock.post.call_count == 1


# ---------------------------------------------------------------------------
# get()
# ---------------------------------------------------------------------------


class TestHttpTransportGet:
    """GET request execution."""

    def test_get_200(self) -> None:
        """GET returns response on success."""
        mock = _make_mock_httpx(200)
        transport = _make_transport(httpx_client=mock)
        resp = transport.get("https://api.example.com/status")
        mock.get.assert_called_once()
        assert resp.status_code == 200

    def test_get_sends_auth_headers(self) -> None:
        """GET includes auth headers."""
        with patch.dict(os.environ, {"K": "my-key"}):
            mock = _make_mock_httpx(200)
            transport = HttpTransport(
                _make_policy(),
                api_key_ref=_env_secret_ref("K"),
                httpx_client=mock,
            )
        transport.get("https://api.example.com/resource")
        headers = mock.get.call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer my-key"

    def test_get_retries_on_5xx(self) -> None:
        """GET retries on 5xx."""
        mock = _make_mock_httpx(500)
        policy = _make_policy(max_retries=1, retry_backoff_seconds=0.0)
        transport = HttpTransport(policy, httpx_client=mock)
        with pytest.raises(HttpTransportError):
            transport.get("https://api.example.com/resource")
        assert mock.get.call_count == 2

    def test_get_no_retry_on_4xx(self) -> None:
        """GET does not retry on 4xx."""
        mock = _make_mock_httpx(404)
        policy = _make_policy(max_retries=3)
        transport = HttpTransport(policy, httpx_client=mock)
        with pytest.raises(HttpTransportError, match="HTTP 404"):
            transport.get("https://api.example.com/resource")
        assert mock.get.call_count == 1

    def test_get_no_retry(self) -> None:
        """GET with retry=False does not retry."""
        mock = _make_mock_httpx(500)
        transport = _make_transport(httpx_client=mock)
        with pytest.raises(HttpTransportError):
            transport.get("https://api.example.com/resource", retry=False)
        assert mock.get.call_count == 1


# ---------------------------------------------------------------------------
# stream_post()
# ---------------------------------------------------------------------------


class TestHttpTransportStreamPost:
    """Streaming POST execution — no retry."""

    def test_stream_post_200(self) -> None:
        """stream_post returns response on success."""
        mock = _make_mock_httpx(200)
        transport = _make_transport(httpx_client=mock)
        chunks = [b"chunk1", b"chunk2"]
        resp = transport.stream_post(
            "https://example.com/stream",
            chunks,
            content_type="application/octet-stream",
        )
        assert resp.status_code == 200
        call_kwargs = mock.post.call_args
        assert call_kwargs.kwargs["content"] is chunks

    def test_stream_post_no_retry_on_5xx(self) -> None:
        """stream_post does not retry on 5xx — raises immediately."""
        mock = _make_mock_httpx(500)
        policy = _make_policy(max_retries=3)
        transport = HttpTransport(policy, httpx_client=mock)
        with pytest.raises(HttpTransportError, match="HTTP 500"):
            transport.stream_post(
                "https://example.com/stream",
                [b"data"],
            )
        assert mock.post.call_count == 1

    def test_stream_post_no_retry_on_4xx(self) -> None:
        """stream_post does not retry on 4xx."""
        mock = _make_mock_httpx(403)
        transport = _make_transport(httpx_client=mock)
        with pytest.raises(HttpTransportError, match="HTTP 403"):
            transport.stream_post(
                "https://example.com/stream",
                [b"data"],
            )
        assert mock.post.call_count == 1

    def test_stream_post_network_error(self) -> None:
        """stream_post wraps network errors in HttpTransportError."""
        mock = _make_mock_httpx()
        mock.post.side_effect = ConnectionError("broken pipe")
        transport = _make_transport(httpx_client=mock)
        with pytest.raises(HttpTransportError, match="broken pipe"):
            transport.stream_post(
                "https://example.com/stream",
                [b"data"],
            )

    def test_stream_post_content_type(self) -> None:
        """stream_post includes content_type header when specified."""
        mock = _make_mock_httpx(200)
        transport = _make_transport(httpx_client=mock)
        transport.stream_post(
            "https://example.com/stream",
            [b"data"],
            content_type="application/x-ndjson",
        )
        headers = mock.post.call_args.kwargs["headers"]
        assert headers["Content-Type"] == "application/x-ndjson"


# ---------------------------------------------------------------------------
# _ensure_client — no client available
# ---------------------------------------------------------------------------


class TestHttpTransportNoClient:
    """Operations fail when httpx client is not available."""

    def test_post_before_open(self) -> None:
        """post() before open() raises HttpTransportError."""
        transport = HttpTransport(_make_policy())
        with pytest.raises(HttpTransportError, match="call open"):
            transport.post("https://example.com", b"data")

    def test_get_before_open(self) -> None:
        """get() before open() raises HttpTransportError."""
        transport = HttpTransport(_make_policy())
        with pytest.raises(HttpTransportError, match="call open"):
            transport.get("https://example.com")

    def test_post_multipart_before_open(self) -> None:
        """post_multipart() before open() raises HttpTransportError."""
        transport = HttpTransport(_make_policy())
        with pytest.raises(HttpTransportError, match="call open"):
            transport.post_multipart("https://example.com", data={"k": "v"})

    def test_stream_post_before_open(self) -> None:
        """stream_post() before open() raises HttpTransportError."""
        transport = HttpTransport(_make_policy())
        with pytest.raises(HttpTransportError, match="call open"):
            transport.stream_post("https://example.com", [b"data"])


# ---------------------------------------------------------------------------
# Header building
# ---------------------------------------------------------------------------


class TestHttpTransportHeaders:
    """Header assembly for requests."""

    def test_content_type_per_request(self) -> None:
        """content_type in post() does not leak to subsequent calls."""
        mock = _make_mock_httpx(200)
        transport = _make_transport(httpx_client=mock)
        transport.post("https://a.com", b"1", content_type="text/csv")
        transport.post("https://a.com", b"2")
        first_headers = mock.post.call_args_list[0].kwargs["headers"]
        second_headers = mock.post.call_args_list[1].kwargs["headers"]
        assert first_headers["Content-Type"] == "text/csv"
        assert "Content-Type" not in second_headers

    def test_extra_headers_in_every_request(self) -> None:
        """extra_headers appear in every request."""
        mock = _make_mock_httpx(200)
        transport = HttpTransport(
            _make_policy(),
            extra_headers={"X-Custom": "val"},
            httpx_client=mock,
        )
        transport.post("https://a.com", b"1")
        transport.get("https://a.com")
        for call in mock.post.call_args_list + mock.get.call_args_list:
            assert call.kwargs["headers"]["X-Custom"] == "val"


# ---------------------------------------------------------------------------
# Error wrapping
# ---------------------------------------------------------------------------


class TestHttpTransportErrorWrapping:
    """_wrap_error preserves already-wrapped errors."""

    def test_already_wrapped_error_passthrough(self) -> None:
        """HttpTransportError is returned as-is, not double-wrapped."""
        mock = _make_mock_httpx()
        original = HttpTransportError("already wrapped")
        mock.post.side_effect = original
        transport = _make_transport(httpx_client=mock)
        with pytest.raises(HttpTransportError, match="already wrapped"):
            transport.post("https://a.com", b"x", retry=False)


# ---------------------------------------------------------------------------
# Non-2xx status codes: 3xx, 429, 1xx
# ---------------------------------------------------------------------------


class TestHttpTransportNon2xx:
    """3xx, 429, and other non-2xx codes are treated as errors."""

    def test_post_3xx_is_error(self) -> None:
        """3xx redirect is treated as error, not success."""
        mock = _make_mock_httpx(301)
        policy = _make_policy(max_retries=0)
        transport = HttpTransport(policy, httpx_client=mock)
        with pytest.raises(HttpTransportError, match="HTTP 301"):
            transport.post("https://a.com", b"x")

    def test_get_302_is_error(self) -> None:
        """302 redirect is treated as error."""
        mock = _make_mock_httpx(302)
        policy = _make_policy(max_retries=0)
        transport = HttpTransport(policy, httpx_client=mock)
        with pytest.raises(HttpTransportError, match="HTTP 302"):
            transport.get("https://a.com")

    def test_3xx_not_retried(self) -> None:
        """3xx (remote_non2xx) is not retried."""
        mock = _make_mock_httpx(307)
        policy = _make_policy(max_retries=3, retry_backoff_seconds=0.0)
        transport = HttpTransport(policy, httpx_client=mock)
        with pytest.raises(HttpTransportError):
            transport.post("https://a.com", b"x")
        assert mock.post.call_count == 1

    def test_429_is_retried(self) -> None:
        """429 rate limit is retried up to max_retries."""
        mock = _make_mock_httpx(429)
        policy = _make_policy(max_retries=2, retry_backoff_seconds=0.0)
        transport = HttpTransport(policy, httpx_client=mock)
        with pytest.raises(HttpTransportError):
            transport.post("https://a.com", b"x")
        # 1 initial + 2 retries = 3 calls
        assert mock.post.call_count == 3

    def test_429_recovers(self) -> None:
        """429 retries and succeeds on subsequent attempt."""
        mock = _make_mock_httpx()
        resp_429 = MagicMock(status_code=429)
        resp_200 = MagicMock(status_code=200)
        mock.post.side_effect = [resp_429, resp_200]
        policy = _make_policy(max_retries=2, retry_backoff_seconds=0.0)
        transport = HttpTransport(policy, httpx_client=mock)
        resp = transport.post("https://a.com", b"x")
        assert resp.status_code == 200
        assert mock.post.call_count == 2

    def test_stream_post_3xx_is_error(self) -> None:
        """stream_post treats 3xx as error."""
        mock = _make_mock_httpx(301)
        transport = _make_transport(httpx_client=mock)
        with pytest.raises(HttpTransportError, match="HTTP 301"):
            transport.stream_post("https://a.com", [b"x"])

    def test_stream_post_429_not_retried(self) -> None:
        """stream_post does not retry 429 (no retry for streaming)."""
        mock = _make_mock_httpx(429)
        transport = _make_transport(httpx_client=mock)
        with pytest.raises(HttpTransportError, match="remote_429"):
            transport.stream_post("https://a.com", [b"x"])
        assert mock.post.call_count == 1

    def test_1xx_is_error(self) -> None:
        """1xx informational status is treated as non-2xx error."""
        mock = _make_mock_httpx(100)
        policy = _make_policy(max_retries=0)
        transport = HttpTransport(policy, httpx_client=mock)
        with pytest.raises(HttpTransportError, match="HTTP 100"):
            transport.post("https://a.com", b"x")
