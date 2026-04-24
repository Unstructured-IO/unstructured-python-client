"""``ClientCredentials`` callable - transparent client-secret -> JWT exchange.

Usage::

    from unstructured_client import UnstructuredClient
    from unstructured_client.auth import ClientCredentials

    client = UnstructuredClient(
        api_key_auth=ClientCredentials(
            client_secret="uns_sk_...",
            server_url="https://accounts.unstructuredapp.io",
        ),
    )

The SDK invokes the callable on each request; this class caches the exchanged
JWT in-memory and refreshes it shortly before expiry.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional

import httpx

from ._base import _ExchangeCallableBase
from ._exceptions import InvalidCredentialError, TokenExchangeError


class ClientCredentials(_ExchangeCallableBase):
    """Synchronous ``client_credentials`` grant callable.

    Exchanges a long-lived client secret for a short-lived account-service JWT
    via ``POST /auth/token-exchange``. Thread-safe: concurrent callers collapse
    onto a single in-flight exchange via an internal lock.
    """

    def __init__(
        self,
        client_secret: str,
        *,
        server_url: str,
        refresh_buffer_seconds: int = 60,
        request_timeout_seconds: float = 30.0,
        max_retries: int = 3,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        """
        :param client_secret: ``uns_sk_...`` client secret provisioned via
            account-service.
        :param server_url: Base URL of account-service (e.g.
            ``https://accounts.unstructuredapp.io``).
        :param refresh_buffer_seconds: Re-exchange when fewer than this many
            seconds remain before the token's absolute expiry.
        :param request_timeout_seconds: Per-attempt timeout for the exchange
            HTTP call.
        :param max_retries: Number of additional attempts on 5xx / network
            errors before serving a cached JWT or raising.
        :param http_client: Optional :class:`httpx.Client` injected for tests
            or shared connection pooling. If omitted, a private client is
            created lazily.
        """
        if not client_secret:
            raise ValueError("client_secret must be a non-empty string")
        super().__init__(
            server_url=server_url,
            refresh_buffer_seconds=refresh_buffer_seconds,
            request_timeout_seconds=request_timeout_seconds,
            max_retries=max_retries,
        )
        self._client_secret = client_secret
        self._http_client = http_client
        self._owns_http_client = http_client is None

    def _build_request_body(self) -> Dict[str, Any]:
        return {
            "grant_type": "client_credentials",
            "client_secret": self._client_secret,
        }

    def _get_http_client(self) -> httpx.Client:
        if self._http_client is None:
            self._http_client = httpx.Client(timeout=self._request_timeout_seconds)
        return self._http_client

    def __call__(self) -> str:
        """Return a valid JWT, performing an exchange only when necessary."""
        now = time.monotonic()
        cached = self._cached_token_if_fresh(now)
        if cached is not None:
            return cached

        with self._lock:
            now = time.monotonic()
            cached = self._cached_token_if_fresh(now)
            if cached is not None:
                return cached
            return self._exchange()

    def _exchange(self) -> str:
        client = self._get_http_client()
        body = self._build_request_body()
        last_error: Optional[Exception] = None

        for attempt in range(self._max_retries + 1):
            try:
                response = client.post(
                    self._exchange_url,
                    json=body,
                    headers={"Content-Type": "application/json"},
                    timeout=self._request_timeout_seconds,
                )
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt < self._max_retries:
                    time.sleep(self._backoff_delay(attempt))
                    continue
                break

            self._raise_for_status(response)

            if 500 <= response.status_code < 600:
                last_error = TokenExchangeError(
                    f"Account-service returned {response.status_code} on token exchange",
                )
                if attempt < self._max_retries:
                    time.sleep(self._backoff_delay(attempt))
                    continue
                break

            if response.status_code != 200:
                raise TokenExchangeError(
                    f"Unexpected status {response.status_code} from token exchange: "
                    f"{response.text[:500]}",
                )

            return self._parse_exchange_response(response)

        return self._handle_outage(last_error)

    def close(self) -> None:
        """Close the private HTTP client, if one was created internally."""
        if self._owns_http_client and self._http_client is not None:
            self._http_client.close()
            self._http_client = None


class AsyncClientCredentials(_ExchangeCallableBase):
    """Asynchronous twin of :class:`ClientCredentials`.

    The synchronous wrapper (:meth:`__call__`) runs the async exchange via
    :func:`asyncio.run` when invoked from a non-async context, so it can still
    be plugged into the SDK's sync-only ``api_key_auth`` callable hook. When
    already inside a running loop, it uses that loop's executor to avoid
    deadlocking.
    """

    def __init__(
        self,
        client_secret: str,
        *,
        server_url: str,
        refresh_buffer_seconds: int = 60,
        request_timeout_seconds: float = 30.0,
        max_retries: int = 3,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        if not client_secret:
            raise ValueError("client_secret must be a non-empty string")
        super().__init__(
            server_url=server_url,
            refresh_buffer_seconds=refresh_buffer_seconds,
            request_timeout_seconds=request_timeout_seconds,
            max_retries=max_retries,
        )
        self._client_secret = client_secret
        self._http_client = http_client
        self._owns_http_client = http_client is None
        self._async_lock = asyncio.Lock()

    def _build_request_body(self) -> Dict[str, Any]:
        return {
            "grant_type": "client_credentials",
            "client_secret": self._client_secret,
        }

    def _get_http_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=self._request_timeout_seconds)
        return self._http_client

    async def acquire(self) -> str:
        """Async variant of ``__call__``. Returns a valid JWT."""
        now = time.monotonic()
        cached = self._cached_token_if_fresh(now)
        if cached is not None:
            return cached

        async with self._async_lock:
            now = time.monotonic()
            cached = self._cached_token_if_fresh(now)
            if cached is not None:
                return cached
            return await self._exchange()

    async def _exchange(self) -> str:
        client = self._get_http_client()
        body = self._build_request_body()
        last_error: Optional[Exception] = None

        for attempt in range(self._max_retries + 1):
            try:
                response = await client.post(
                    self._exchange_url,
                    json=body,
                    headers={"Content-Type": "application/json"},
                    timeout=self._request_timeout_seconds,
                )
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt < self._max_retries:
                    await asyncio.sleep(self._backoff_delay(attempt))
                    continue
                break

            self._raise_for_status(response)

            if 500 <= response.status_code < 600:
                last_error = TokenExchangeError(
                    f"Account-service returned {response.status_code} on token exchange",
                )
                if attempt < self._max_retries:
                    await asyncio.sleep(self._backoff_delay(attempt))
                    continue
                break

            if response.status_code != 200:
                raise TokenExchangeError(
                    f"Unexpected status {response.status_code} from token exchange: "
                    f"{response.text[:500]}",
                )

            return self._parse_exchange_response(response)

        return self._handle_outage(last_error)

    def __call__(self) -> str:
        """Sync entry point so the SDK's ``api_key_auth`` callable hook works.

        When invoked from inside a running event loop (the usual case for
        async SDK methods), the exchange runs in the loop's default executor
        so we don't reenter :func:`asyncio.run`. Otherwise we spin up a
        temporary loop via :func:`asyncio.run`.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.acquire())

        # Inside a running loop - offload to a worker thread that drives its
        # own event loop so we don't block the caller's loop on httpx IO.
        import concurrent.futures

        def _run_in_new_loop() -> str:
            return asyncio.run(self.acquire())

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_run_in_new_loop)
            return future.result()

    async def aclose(self) -> None:
        """Close the private HTTP client, if one was created internally."""
        if self._owns_http_client and self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None
