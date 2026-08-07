"""Reusable HTTP transport layer for delivery clients.

Consolidates httpx client lifecycle, auth header resolution, and
request execution (with optional retry) into a single component.
Used by HttpDeliveryClient, StreamingHttpDeliveryClient, and
StripeDataManagementClient.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from pfp_runtime.publishing.support.secret_resolver import (
    SecretResolutionError,
    resolve_secret_ref,
)
from pfp_runtime.publishing.support.transport_policy import (
    TlsTransportPolicy,
    classify_transport_error,
    execute_with_retry,
    mark_transport_error,
)
from pfp_utils.security import SecretRef


class HttpTransportError(RuntimeError):
    """Raised on transport-level HTTP errors (auth resolution, network, 4xx/5xx)."""


class HttpTransport:
    """Low-level HTTP transport: httpx client, auth headers, retry on 5xx.

    Encapsulates httpx.Client creation/lifecycle, auth header resolution
    from SecretRef, and request methods (post, post_multipart, get,
    stream_post) with optional retry via transport_policy.

    Lifecycle:
        __init__ -> open() -> post()/get()/... -> close()

    Note:
        Secrets (api_key_ref / token_ref) are resolved once at construction
        time and cached for the lifetime of the instance. This is intentional
        for batch pipelines where token rotation within a single run is not
        expected. Long-lived services requiring token refresh should
        re-create the transport instance.

    Args:
        policy: TLS transport policy with timeout, retry, and TLS settings.
        api_key_ref: Optional SecretRef for API key (Bearer token).
            Mutually exclusive with token_ref.
        token_ref: Optional SecretRef for OAuth/bearer token.
            Mutually exclusive with api_key_ref.
        extra_headers: Optional additional headers merged into every request.
        httpx_client: Optional pre-built httpx.Client for testing.
            When provided, lifecycle is managed externally (open/close are no-ops).

    Raises:
        HttpTransportError: If both api_key_ref and token_ref are provided,
            or if secret resolution fails.
    """

    def __init__(
        self,
        policy: TlsTransportPolicy,
        *,
        api_key_ref: Optional[SecretRef] = None,
        token_ref: Optional[SecretRef] = None,
        extra_headers: Optional[Dict[str, str]] = None,
        httpx_client: Any = None,
    ) -> None:
        if api_key_ref is not None and token_ref is not None:
            raise HttpTransportError("Specify at most one of api_key_ref and token_ref")

        self._policy = policy

        try:
            if api_key_ref is not None:
                key = resolve_secret_ref(api_key_ref)
                self._auth_header: Dict[str, str] = {
                    "Authorization": "Bearer {key}".format(key=key)
                }
            elif token_ref is not None:
                token = resolve_secret_ref(token_ref)
                self._auth_header = {
                    "Authorization": "Bearer {token}".format(token=token)
                }
            else:
                self._auth_header = {}
        except SecretResolutionError as exc:
            raise HttpTransportError(
                "Failed to resolve HTTP transport secret: {exc}".format(exc=exc)
            ) from exc

        self._base_headers: Dict[str, str] = dict(self._auth_header)
        if extra_headers:
            self._base_headers.update(extra_headers)

        self._injected_httpx: Any = httpx_client
        self._httpx_client: Any = httpx_client

    def open(self) -> None:
        """Create a fresh httpx.Client for this transport cycle.

        When an httpx_client was injected at construction, this is a no-op.
        Otherwise, closes any previously owned client and creates a new one.
        """
        if self._injected_httpx is not None:
            return
        if self._httpx_client is not None:
            try:
                self._httpx_client.close()
            except Exception:  # nosec B110
                pass
        import httpx as _httpx

        self._httpx_client = _httpx.Client(
            verify=self._policy.verify_tls,
            timeout=self._policy.timeout_seconds,
        )

    def post(
        self,
        url: str,
        body: bytes,
        *,
        content_type: Optional[str] = None,
        retry: bool = True,
    ) -> Any:
        """Send a POST request with body bytes.

        Args:
            url: Target URL.
            body: Request body as raw bytes.
            content_type: Optional Content-Type header for this request.
            retry: When True, retries on 5xx up to policy.max_retries times.

        Returns:
            httpx.Response object.

        Raises:
            HttpTransportError: On unrecoverable network or HTTP error.
        """
        self._ensure_client()
        headers = self._build_headers(content_type=content_type)

        def _do_post() -> Any:
            response = self._httpx_client.post(
                url,
                content=body,
                headers=headers,
            )
            self._check_status(response, url)
            return response

        return self._execute(_do_post, retry=retry)

    def post_multipart(
        self,
        url: str,
        *,
        files: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, str]] = None,
        retry: bool = True,
    ) -> Any:
        """Send a multipart/form-data POST request.

        Args:
            url: Target URL.
            files: Mapping for httpx files parameter (name -> (filename, content, mime)).
            data: Mapping for httpx data parameter (form fields).
            retry: When True, retries on 5xx up to policy.max_retries times.

        Returns:
            httpx.Response object.

        Raises:
            HttpTransportError: On unrecoverable network or HTTP error.
        """
        self._ensure_client()
        headers = self._build_headers()

        def _do_post() -> Any:
            response = self._httpx_client.post(
                url,
                files=files,
                data=data,
                headers=headers,
            )
            self._check_status(response, url)
            return response

        return self._execute(_do_post, retry=retry)

    def get(self, url: str, *, retry: bool = True) -> Any:
        """Send a GET request.

        Args:
            url: Target URL.
            retry: When True, retries on 5xx up to policy.max_retries times.

        Returns:
            httpx.Response object.

        Raises:
            HttpTransportError: On unrecoverable network or HTTP error.
        """
        self._ensure_client()
        headers = self._build_headers()

        def _do_get() -> Any:
            response = self._httpx_client.get(url, headers=headers)
            self._check_status(response, url)
            return response

        return self._execute(_do_get, retry=retry)

    def stream_post(
        self,
        url: str,
        chunks: Iterable[bytes],
        *,
        content_type: Optional[str] = None,
    ) -> Any:
        """Send a streaming POST request (chunked transfer encoding).

        No retry is applied — a partially-sent streaming request cannot
        be replayed.

        Args:
            url: Target URL.
            chunks: Iterable of byte chunks to stream as request body.
            content_type: Optional Content-Type header for this request.

        Returns:
            httpx.Response object.

        Raises:
            HttpTransportError: On network or HTTP error.
        """
        headers = self._build_headers(content_type=content_type)
        self._ensure_client()
        try:
            response = self._httpx_client.post(
                url,
                content=chunks,
                headers=headers,
            )
        except Exception as exc:
            raise self._wrap_error(exc) from exc
        self._check_status_no_retry(response, url)
        return response

    def close(self) -> None:
        """Release the httpx.Client if owned by this transport.

        Injected clients are never closed. Safe to call multiple times.
        """
        if self._injected_httpx is not None:
            return
        if self._httpx_client is not None:
            try:
                self._httpx_client.close()
            except Exception:  # nosec B110
                pass
            self._httpx_client = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_headers(
        self,
        *,
        content_type: Optional[str] = None,
    ) -> Dict[str, str]:
        """Build merged headers dict for a single request.

        Args:
            content_type: Optional Content-Type override for this request.

        Returns:
            Headers dict combining base headers with optional Content-Type.
        """
        if content_type is None:
            return dict(self._base_headers)
        headers = dict(self._base_headers)
        headers["Content-Type"] = content_type
        return headers

    def _ensure_client(self) -> None:
        """Verify that an httpx client is available.

        Raises:
            HttpTransportError: If no client exists (open() not called).
        """
        if self._httpx_client is None:
            raise HttpTransportError("No httpx client available — call open() first")

    def _check_status(self, response: Any, url: str) -> None:
        """Raise transport marker errors for non-2xx responses.

        These markers are caught by execute_with_retry for retry decisions.
        429 is separated into its own retryable category (remote_429).

        Args:
            response: httpx.Response to inspect.
            url: Request URL for error messages.

        Raises:
            _TransportCategoryError: With category remote_5xx, remote_429,
                remote_4xx, or remote_non2xx.
        """
        status = response.status_code
        if 200 <= status < 300:
            return
        if 500 <= status < 600:
            raise mark_transport_error(
                category="remote_5xx",
                message="HTTP {status} from {url}".format(status=status, url=url),
            )
        if status == 429:
            raise mark_transport_error(
                category="remote_429",
                message="HTTP 429 from {url}".format(url=url),
            )
        if 400 <= status < 500:
            raise mark_transport_error(
                category="remote_4xx",
                message="HTTP {status} from {url}".format(status=status, url=url),
            )
        raise mark_transport_error(
            category="remote_non2xx",
            message="HTTP {status} from {url}".format(status=status, url=url),
        )

    def _check_status_no_retry(self, response: Any, url: str) -> None:
        """Raise HttpTransportError for non-2xx responses without retry.

        Args:
            response: httpx.Response to inspect.
            url: Request URL for error messages.

        Raises:
            HttpTransportError: On any non-2xx response.
        """
        status = response.status_code
        if 200 <= status < 300:
            return
        if status == 429:
            category = "remote_429"
        elif 400 <= status < 500:
            category = "remote_4xx"
        elif 500 <= status < 600:
            category = "remote_5xx"
        else:
            category = "remote_non2xx"
        raise HttpTransportError(
            "http_transport [category={category}]: HTTP {status} "
            "from {url}".format(category=category, status=status, url=url)
        )

    def _execute(self, operation: Any, *, retry: bool) -> Any:
        """Execute operation with optional retry.

        Args:
            operation: Zero-argument callable performing the HTTP request.
            retry: When True, delegates to execute_with_retry.

        Returns:
            Operation result (httpx.Response).

        Raises:
            HttpTransportError: On unrecoverable error.
        """
        if retry:
            try:
                return execute_with_retry(
                    operation,
                    policy=self._policy,
                    classify_error=lambda exc: classify_transport_error(
                        exc, transport="http"
                    ),
                )
            except Exception as exc:
                raise self._wrap_error(exc) from exc
        else:
            try:
                return operation()
            except Exception as exc:
                raise self._wrap_error(exc) from exc

    def _wrap_error(self, exc: BaseException) -> HttpTransportError:
        """Wrap an exception into HttpTransportError with category info.

        Args:
            exc: Original exception.

        Returns:
            HttpTransportError with formatted message.
        """
        if isinstance(exc, HttpTransportError):
            return exc
        category = classify_transport_error(exc, transport="http")
        return HttpTransportError(
            "http_transport [category={category}]: {exc}".format(
                category=category, exc=exc
            )
        )


__all__ = ["HttpTransport", "HttpTransportError"]
