"""HTTP delivery client for client_type: http.

Buffers all chunks in memory and sends a single POST in finalize().
Retries on 5xx responses up to transport.max_retries times.

HttpClientIaC is shared with StreamingHttpDeliveryClient
(streaming_http_client.py), which uses the same YAML configuration but
streams chunks in real time via queue + background thread.
"""

from __future__ import annotations

import io
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pfp_runtime.publishing.clients.client_contract import DeliveryResult
from pfp_runtime.publishing.support.secret_resolver import (
    SecretResolutionError,
    resolve_secret_ref,
)
from pfp_runtime.publishing.support.transport_policy import (
    TlsTransportPolicy,
    classify_transport_error,
    execute_with_retry,
    format_transport_runtime_error,
    mark_transport_error,
)
from pfp_utils.security import SecretRef


class HttpClientError(RuntimeError):
    """Raised when HttpDeliveryClient encounters a configuration or network error."""


class HttpClientIaC(BaseModel):
    """IaC model shared by HttpDeliveryClient and StreamingHttpDeliveryClient.

    Attributes:
        endpoint: Full URL for the POST request (e.g. https://api.example.com/feed).
        api_key_ref: Optional SecretRef for the API key sent as a Bearer token.
            Mutually exclusive with token_ref.
        token_ref: Optional SecretRef for an OAuth / bearer token.
            Mutually exclusive with api_key_ref.
        content_type: Optional Content-Type header value sent with every POST
            (e.g. 'application/x-ndjson'). When None, no Content-Type is added.
        transport: TLS transport policy. All sub-fields have defaults —
            the entire block is optional in YAML.
    """

    model_config = ConfigDict(extra="forbid")

    endpoint: str
    api_key_ref: Optional[SecretRef] = None
    token_ref: Optional[SecretRef] = None
    content_type: Optional[str] = None
    max_body_bytes: int = Field(
        default=100 * 1024 * 1024,  # 100 MB
        gt=0,
    )
    transport: TlsTransportPolicy = Field(default_factory=TlsTransportPolicy)

    @model_validator(mode="after")
    def _validate_auth(self) -> "HttpClientIaC":
        if self.api_key_ref is not None and self.token_ref is not None:
            raise ValueError("Specify at most one of api_key_ref and token_ref")
        return self


class HttpDeliveryClient:
    """Delivery client that buffers all chunks and POSTs them in finalize().

    Satisfies the DeliveryClient protocol structurally. Instantiated by
    client_builder when client_type is 'http', using the standard 5-step
    build path.

    Retries on 5xx responses up to transport.max_retries times with optional
    backoff. Does not retry 4xx or auth failures.

    Args:
        iac: Validated HttpClientIaC instance.
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
            HttpClientError: If a referenced secret cannot be resolved.
        """
        self._iac = iac
        try:
            if iac.api_key_ref is not None:
                key = resolve_secret_ref(iac.api_key_ref)
                self._auth_header: Dict[str, str] = {"Authorization": f"Bearer {key}"}
            elif iac.token_ref is not None:
                token = resolve_secret_ref(iac.token_ref)
                self._auth_header = {"Authorization": f"Bearer {token}"}
            else:
                self._auth_header = {}
        except SecretResolutionError as exc:
            raise HttpClientError(
                f"Failed to resolve HTTP client secret: {exc}"
            ) from exc

        self._headers: Dict[str, str] = dict(self._auth_header)
        if iac.content_type is not None:
            self._headers["Content-Type"] = iac.content_type

        # Injected client (tests): lifecycle managed externally.
        # No injection (prod): client is created in open() and closed in finalize().
        self._injected_httpx: Any = httpx_client
        self._httpx_client: Any = httpx_client

        self._buffer: Optional[io.BytesIO] = None
        self._finalized: bool = False

    def open(self) -> None:
        """Initialise a fresh in-memory buffer and httpx client for this delivery cycle.

        In production (no injected httpx_client), closes any previously owned
        client and creates a fresh one. Injected clients are never closed here.
        """
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
        self._buffer = io.BytesIO()
        self._finalized = False

    def send_chunk(self, chunk: bytes) -> None:
        """Append chunk to the in-memory buffer.

        Args:
            chunk: Payload bytes to buffer.

        Raises:
            HttpClientError: If called before open() or after finalize().
        """
        if self._finalized:
            raise HttpClientError("send_chunk() called after finalize()")
        if self._buffer is None:
            raise HttpClientError("send_chunk() called before open()")
        current = self._buffer.tell()
        if current + len(chunk) > self._iac.max_body_bytes:
            raise HttpClientError(
                f"http_client: payload size ({current + len(chunk)} bytes) would exceed "
                f"max_body_bytes={self._iac.max_body_bytes}. "
                f"Use client_type: http_streaming for large payloads."
            )
        self._buffer.write(chunk)

    def finalize(self) -> DeliveryResult:
        """POST the buffered body and return delivery result.

        The entire body is sent in a single POST. On 5xx the operation is
        retried up to transport.max_retries times. On 4xx no retry is
        attempted.

        Returns:
            DeliveryResult with skipped=False and the HTTP status code.

        Raises:
            HttpClientError: On unrecoverable network or protocol error.
        """
        if self._finalized:
            raise HttpClientError(
                "finalize() already called; call open() to start a new run"
            )
        if self._buffer is None:
            raise HttpClientError("finalize() called before open()")

        body = self._buffer.getvalue()
        self._buffer = None

        def _post() -> Any:
            response = self._httpx_client.post(
                self._iac.endpoint,
                content=body,
                headers=self._headers,
            )
            status = response.status_code
            if 500 <= status < 600:
                raise mark_transport_error(
                    category="remote_5xx",
                    message=f"HTTP {status} from {self._iac.endpoint}",
                )
            if 400 <= status < 500:
                raise mark_transport_error(
                    category="remote_4xx",
                    message=f"HTTP {status} from {self._iac.endpoint}",
                )
            return response

        try:
            response = execute_with_retry(
                _post,
                policy=self._iac.transport,
                classify_error=lambda exc: classify_transport_error(
                    exc, transport="http"
                ),
            )
        except Exception as exc:
            category = classify_transport_error(exc, transport="http")
            msg = format_transport_runtime_error(
                prefix="http_client",
                category=category,
                exc=exc,
            )
            raise HttpClientError(msg) from exc

        self._finalized = True
        if self._injected_httpx is None and self._httpx_client is not None:
            self._httpx_client.close()
            self._httpx_client = None
        return DeliveryResult(skipped=False, status_code=response.status_code)


__all__: List[str] = ["HttpClientIaC", "HttpDeliveryClient", "HttpClientError"]
