"""Streaming HTTP delivery client for client_type: http_streaming.

Streams chunks in real time using queue + background thread and
Transfer-Encoding: chunked. Unlike HttpDeliveryClient, no retry is
applied — a partially-sent request cannot be replayed.

Shares HttpClientIaC with http_client.py. Both clients accept the same
YAML configuration file; the difference is in the streaming contract.
"""

from __future__ import annotations

import queue
import threading
from typing import Any, Iterator, List, Optional

from pfp_runtime.publishing.clients.client_contract import DeliveryResult
from pfp_runtime.publishing.clients.http_client import HttpClientIaC
from pfp_runtime.publishing.support.secret_resolver import (
    SecretResolutionError,
    resolve_secret_ref,
)
from pfp_runtime.publishing.support.transport_policy import (
    classify_transport_error,
    format_transport_runtime_error,
)


class StreamingHttpClientError(RuntimeError):
    """Raised when StreamingHttpDeliveryClient encounters an error."""


class StreamingHttpDeliveryClient:
    """Delivery client that streams chunks over HTTP using chunked transfer encoding.

    Uses a queue.Queue and a background thread. The main thread feeds chunks
    via send_chunk(); the background thread consumes them through a generator
    and passes the generator to httpx.post(content=gen), which sends each
    chunk as soon as it arrives without buffering the full body.

    No retry is applied — a partially-sent streaming request cannot be
    replayed. Use client_type: http for retry support.

    Satisfies the DeliveryClient protocol structurally. Instantiated by
    client_builder when client_type is 'http_streaming'.

    Args:
        iac: Validated HttpClientIaC instance (shared with HttpDeliveryClient).
        httpx_client: Optional pre-built httpx.Client for testing.
    """

    def __init__(
        self,
        iac: HttpClientIaC,
        *,
        httpx_client: Any = None,
    ) -> None:
        """Resolve auth secrets and create httpx client in Fail-Fast mode.

        Args:
            iac: Validated HttpClientIaC instance.
            httpx_client: Optional pre-built httpx.Client (injected in tests).

        Raises:
            StreamingHttpClientError: If a referenced secret cannot be resolved.
        """
        self._iac = iac
        try:
            if iac.api_key_ref is not None:
                key = resolve_secret_ref(iac.api_key_ref)
                self._auth_header = {"Authorization": f"Bearer {key}"}
            elif iac.token_ref is not None:
                token = resolve_secret_ref(iac.token_ref)
                self._auth_header = {"Authorization": f"Bearer {token}"}
            else:
                self._auth_header = {}
        except SecretResolutionError as exc:
            raise StreamingHttpClientError(
                f"Failed to resolve HTTP client secret: {exc}"
            ) from exc

        self._headers = dict(self._auth_header)
        if iac.content_type is not None:
            self._headers["Content-Type"] = iac.content_type

        # Injected client (tests): lifecycle managed externally.
        # No injection (prod): client is created in open() and closed in finalize().
        self._injected_httpx: Any = httpx_client
        self._httpx_client: Any = httpx_client

        self._queue: Optional[queue.Queue] = None  # type: ignore[type-arg]
        self._thread: Optional[threading.Thread] = None
        self._exc: Optional[BaseException] = None
        self._response: Any = None
        self._finalized: bool = False

    def open(self) -> None:
        """Initialise queue and start the background streaming thread.

        If a previous open() cycle is still alive (thread not finished),
        sends a sentinel to terminate it before starting a fresh cycle.
        """
        if self._thread is not None and self._thread.is_alive():
            # Best-effort: signal previous thread to exit
            if self._queue is not None:
                self._queue.put(None)
            self._thread.join(timeout=1.0)

        if self._injected_httpx is None:
            if self._httpx_client is not None:
                try:
                    self._httpx_client.close()
                except Exception:  # nosec B110
                    pass
            import httpx as _httpx

            self._httpx_client = _httpx.Client(
                verify=self._iac.transport.verify_tls,
                timeout=self._iac.transport.timeout_seconds,
            )

        self._queue = queue.Queue()
        self._exc = None
        self._response = None
        self._finalized = False
        self._thread = threading.Thread(target=self._stream_thread, daemon=True)
        self._thread.start()

    def send_chunk(self, chunk: bytes) -> None:
        """Enqueue a chunk for the background thread to stream.

        Args:
            chunk: Payload bytes to stream.

        Raises:
            StreamingHttpClientError: If called before open() or after finalize().
        """
        if self._queue is None:
            raise StreamingHttpClientError("send_chunk() called before open()")
        if self._finalized:
            raise StreamingHttpClientError("send_chunk() called after finalize()")
        self._queue.put(chunk)

    def finalize(self) -> DeliveryResult:
        """Signal end-of-stream and wait for the background thread to finish.

        Sends a sentinel (None) into the queue, joins the thread, and checks
        for errors. Returns the HTTP status code from the response.

        Returns:
            DeliveryResult with skipped=False and the HTTP status code.

        Raises:
            StreamingHttpClientError: On thread error, timeout, or non-2xx response.
        """
        if self._queue is None:
            raise StreamingHttpClientError("finalize() called before open()")
        if self._finalized:
            raise StreamingHttpClientError(
                "finalize() already called; call open() to start a new run"
            )

        self._queue.put(None)  # sentinel — tells generator to stop
        assert self._thread is not None  # nosec B101
        self._thread.join(timeout=self._iac.transport.timeout_seconds)

        # Thread is done — close owned httpx client (on any outcome below)
        if self._injected_httpx is None and self._httpx_client is not None:
            try:
                self._httpx_client.close()
            except Exception:  # nosec B110
                pass
            self._httpx_client = None

        if self._exc is not None:
            exc = self._exc
            category = classify_transport_error(exc, transport="http")
            msg = format_transport_runtime_error(
                prefix="streaming_http_client",
                category=category,
                exc=exc,
            )
            raise StreamingHttpClientError(msg) from exc

        if self._response is None:
            raise StreamingHttpClientError(
                "streaming_http_client: no response received (thread timed out)"
            )

        status = self._response.status_code
        if status >= 400:
            category = "remote_4xx" if status < 500 else "remote_5xx"
            raise StreamingHttpClientError(
                f"streaming_http_client [category={category}]: HTTP {status} "
                f"from {self._iac.endpoint}"
            )

        self._finalized = True
        return DeliveryResult(skipped=False, status_code=status)

    def _stream_thread(self) -> None:
        """Background thread: consume queue via generator and POST to endpoint."""

        def _gen() -> Iterator[bytes]:
            assert self._queue is not None  # nosec B101
            while True:
                chunk = self._queue.get()
                if chunk is None:  # sentinel from finalize()
                    break
                yield chunk

        try:
            resp = self._httpx_client.post(
                self._iac.endpoint,
                content=_gen(),
                headers=self._headers,
            )
            self._response = resp
        except Exception as exc:  # nosec B110
            self._exc = exc


__all__: List[str] = [
    "StreamingHttpDeliveryClient",
    "StreamingHttpClientError",
]
