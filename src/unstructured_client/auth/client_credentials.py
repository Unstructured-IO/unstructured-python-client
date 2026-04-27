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
import concurrent.futures
import threading
import time
import weakref
from typing import Any, Dict, Optional

import httpx

from ._base import _ExchangeCallableBase
from ._exceptions import TokenExchangeError


def _close_httpx_client(client: Optional[httpx.Client]) -> None:
    """Best-effort sync close used by :func:`weakref.finalize`."""
    if client is None:
        return
    try:
        client.close()
    except Exception:  # noqa: BLE001 - finalize must never raise
        pass


def _close_async_httpx_client(client: Optional[httpx.AsyncClient]) -> None:
    """Best-effort async close from :func:`weakref.finalize`.

    ``AsyncClient.aclose`` is a coroutine, so we run it on a fresh event loop
    on a worker thread to avoid touching whatever loop (if any) the user is
    currently running.
    """
    if client is None:
        return

    def _run() -> None:
        try:
            asyncio.run(client.aclose())
        except Exception:  # noqa: BLE001
            pass

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(_run).result(timeout=5)
    except Exception:  # noqa: BLE001 - finalize must never raise
        pass


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
        # Separate init lock so :meth:`_get_http_client` can atomically create
        # the lazy client even though :meth:`_exchange` already holds the
        # outer ``self._lock`` (a non-reentrant ``threading.Lock``).
        self._http_client_init_lock = threading.Lock()
        self._finalizer: Optional[weakref.finalize] = None
        if self._owns_http_client:
            # Register a finalizer that closes a lazily-created private
            # ``httpx.Client`` if the user never calls :meth:`close`. The
            # closure binds an attribute lookup (``self._http_client``) at
            # finalize-time via a small accessor so the finalizer doesn't
            # itself keep ``self`` alive.
            owner_ref = weakref.ref(self)

            def _finalize() -> None:
                owner = owner_ref()
                if owner is None:
                    return
                # pylint: disable=protected-access
                _close_httpx_client(owner._http_client)
                owner._http_client = None

            self._finalizer = weakref.finalize(self, _finalize)

    def _build_request_body(self) -> Dict[str, Any]:
        return {
            "grant_type": "client_credentials",
            "client_secret": self._client_secret,
        }

    def _get_http_client(self) -> httpx.Client:
        """Return the lazily-initialized private ``httpx.Client``.

        Atomic across threads: a dedicated init lock guarantees that only a
        single private client is ever created even if two callers race here
        before any cache exists.
        """
        if self._http_client is not None:
            return self._http_client
        with self._http_client_init_lock:
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
        if self._finalizer is not None:
            # We've already cleaned up; detach the finalizer so it doesn't
            # double-close.
            self._finalizer.detach()
            self._finalizer = None


class AsyncClientCredentials(_ExchangeCallableBase):
    """Asynchronous twin of :class:`ClientCredentials`.

    Async callers should ``await acquire()`` for a non-blocking exchange.

    The synchronous :meth:`__call__` exists so ``AsyncClientCredentials`` can
    still be plugged into the SDK's sync-only ``api_key_auth`` callable hook.
    Note that calling :meth:`__call__` from inside a running event loop blocks
    that loop while the exchange runs on a worker thread - prefer
    :meth:`acquire` in async-native code.
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
        self._http_client_init_lock = threading.Lock()
        # The async lock is created lazily inside a coroutine so it binds to
        # the *currently running* event loop. We refresh it whenever the
        # running loop changes (e.g. a fresh ``asyncio.run()`` invocation
        # after the cache lapses). A dedicated init lock guards the lazy
        # field assignment so it stays decoupled from ``self._lock`` (the
        # sync-entry coalescing lock) and can't deadlock with it.
        self._async_lock: Optional[asyncio.Lock] = None
        self._async_lock_loop: Optional[asyncio.AbstractEventLoop] = None
        self._async_lock_init_lock = threading.Lock()
        self._finalizer: Optional[weakref.finalize] = None
        if self._owns_http_client:
            owner_ref = weakref.ref(self)

            def _finalize() -> None:
                owner = owner_ref()
                if owner is None:
                    return
                # pylint: disable=protected-access
                _close_async_httpx_client(owner._http_client)
                owner._http_client = None

            self._finalizer = weakref.finalize(self, _finalize)

    def _build_request_body(self) -> Dict[str, Any]:
        return {
            "grant_type": "client_credentials",
            "client_secret": self._client_secret,
        }

    def _get_http_client(self) -> httpx.AsyncClient:
        """Return the lazily-initialized private ``httpx.AsyncClient``.

        Atomic across threads: a dedicated init lock guarantees only a single
        private client is ever created.
        """
        if self._http_client is not None:
            return self._http_client
        with self._http_client_init_lock:
            if self._http_client is None:
                self._http_client = httpx.AsyncClient(
                    timeout=self._request_timeout_seconds
                )
            return self._http_client

    def _get_async_lock(self) -> asyncio.Lock:
        """Return an :class:`asyncio.Lock` bound to the *currently running* loop.

        A dedicated threading lock guards the lazy field assignment so
        multiple OS threads concurrently driving their own event loops
        can't race to replace the lock.
        """
        loop = asyncio.get_running_loop()
        with self._async_lock_init_lock:
            if self._async_lock is None or self._async_lock_loop is not loop:
                self._async_lock = asyncio.Lock()
                self._async_lock_loop = loop
            return self._async_lock

    async def acquire(self) -> str:
        """Async variant of ``__call__``. Returns a valid JWT."""
        now = time.monotonic()
        cached = self._cached_token_if_fresh(now)
        if cached is not None:
            return cached

        async with self._get_async_lock():
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

        Async-native code should ``await acquire()`` instead - it does not
        block the caller's event loop and does not pay the cost of spinning
        up a new event loop on a worker thread.

        Concurrency notes:

        * Outside a running loop, ``asyncio.run(self.acquire())`` drives a
          fresh event loop. The threading lock coalesces concurrent OS
          threads onto a single exchange so we don't fire N HTTP calls.
        * Inside a running loop, we offload to a worker thread that runs a
          private event loop. ``future.result()`` then blocks the caller's
          loop until the exchange completes. This is unavoidable while we
          have to return a sync value to Speakeasy's security factory; if
          you need a non-blocking path, await :meth:`acquire` directly.
        """
        now = time.monotonic()
        cached = self._cached_token_if_fresh(now)
        if cached is not None:
            return cached

        try:
            asyncio.get_running_loop()
            inside_running_loop = True
        except RuntimeError:
            inside_running_loop = False

        # Coalesce concurrent OS threads onto a single in-flight exchange.
        # ``self._lock`` is non-reentrant; ``acquire()`` and helpers that run
        # under it use dedicated init locks (``_http_client_init_lock`` and
        # ``_async_lock_init_lock``) to avoid re-entering this lock.
        with self._lock:
            now = time.monotonic()
            cached = self._cached_token_if_fresh(now)
            if cached is not None:
                return cached

            if not inside_running_loop:
                return asyncio.run(self.acquire())

            # Inside a running loop. ``future.result()`` blocks the caller's
            # loop while the worker thread runs the exchange (see docstring).
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
        if self._finalizer is not None:
            self._finalizer.detach()
            self._finalizer = None
