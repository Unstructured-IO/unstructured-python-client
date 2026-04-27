"""Shared internals for token-exchange auth callables.

This module holds the abstract base class used by :class:`ClientCredentials`,
:class:`AsyncClientCredentials`, :class:`LegacyKeyExchange`, and
:class:`AsyncLegacyKeyExchange`. It implements:

* In-memory caching of the most recent access token with TTL math.
* Lock-guarded refresh (``threading.Lock`` for sync, ``asyncio.Lock`` for async)
  so concurrent callers collapse to a single in-flight exchange.
* Exponential-backoff retry on 5xx / network errors.
* Fallback to a still-unexpired cached token when account-service is
  unavailable.

No public API lives here. Users import from :mod:`unstructured_client.auth`.
"""

from __future__ import annotations

import logging
import random
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx

from ._exceptions import (
    InvalidCredentialError,
    TokenExchangeDisabledError,
    TokenExchangeError,
)

logger = logging.getLogger("unstructured-client.auth")


TOKEN_EXCHANGE_PATH = "/auth/token-exchange"

# Exponential-backoff delays (seconds) used for 5xx / network failures.
_BACKOFF_BASE_SECONDS = 0.5
_BACKOFF_EXPONENT = 2.0


@dataclass
class _CachedToken:
    access_token: str
    expires_at: float


class _ExchangeCallableBase:
    """Shared state container for sync/async token-exchange callables.

    Subclasses only need to provide :meth:`_build_request_body`. The detection
    logic in :class:`AuthHeaderBeforeRequestHook` uses ``isinstance`` against
    this class to decide whether to rewrite the outgoing ``unstructured-api-key``
    header into ``Authorization: Bearer``.
    """

    def __init__(
        self,
        *,
        server_url: str,
        refresh_buffer_seconds: int = 60,
        request_timeout_seconds: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        if not server_url:
            raise ValueError("server_url must be a non-empty account-service base URL")
        if refresh_buffer_seconds < 0:
            raise ValueError("refresh_buffer_seconds must be >= 0")
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if request_timeout_seconds <= 0:
            raise ValueError("request_timeout_seconds must be > 0")

        self._server_url = server_url.rstrip("/")
        self._refresh_buffer_seconds = refresh_buffer_seconds
        self._request_timeout_seconds = request_timeout_seconds
        self._max_retries = max_retries

        self._cache: Optional[_CachedToken] = None
        self._lock = threading.Lock()

    def _build_request_body(self) -> Dict[str, Any]:
        """Return the JSON body for the `/auth/token-exchange` POST.

        Subclasses override to select `grant_type` and the credential field.
        """
        raise NotImplementedError

    @property
    def _exchange_url(self) -> str:
        return f"{self._server_url}{TOKEN_EXCHANGE_PATH}"

    def _cached_token_if_fresh(self, now: float) -> Optional[str]:
        """Return the cached JWT if it is still valid beyond the refresh buffer."""
        cached = self._cache
        if cached is None:
            return None
        if now >= cached.expires_at - self._refresh_buffer_seconds:
            return None
        return cached.access_token

    def _cached_token_if_not_expired(self, now: float) -> Optional[str]:
        """Return the cached JWT if it has not yet crossed absolute expiry.

        Used as an outage fallback: when account-service is unreachable but a
        previously fetched token is still technically valid (past the refresh
        buffer but before ``expires_at``), serving it keeps the caller working
        until the real expiry lands.
        """
        cached = self._cache
        if cached is None:
            return None
        if now >= cached.expires_at:
            return None
        return cached.access_token

    def _parse_exchange_response(self, response: httpx.Response) -> str:
        """Parse a successful ``/auth/token-exchange`` response into a JWT.

        Updates the in-memory cache with the new token and its absolute expiry.
        Raises :class:`TokenExchangeDisabledError` if the server reports
        ``token_exchange_enabled=False``, and :class:`TokenExchangeError` for
        malformed payloads.
        """
        try:
            payload = response.json()
        except ValueError as exc:
            raise TokenExchangeError(
                f"Account-service returned a non-JSON body on token exchange: {exc}"
            ) from exc

        if not payload.get("token_exchange_enabled", True):
            raise TokenExchangeDisabledError(
                "Account-service reports token_exchange_enabled=False. "
                "ClientCredentials / LegacyKeyExchange require a server with "
                "DEPLOYMENT_MODE=dedicated (or equivalent) that accepts token "
                "exchange. Fall back to plain api_key_auth=<raw key> if needed.",
            )

        access_token = payload.get("access_token")
        expires_in = payload.get("expires_in")
        if not access_token or not isinstance(expires_in, (int, float)) or expires_in <= 0:
            raise TokenExchangeError(
                "Account-service returned a malformed token-exchange response: "
                f"access_token={'<present>' if access_token else '<missing>'}, "
                f"expires_in={expires_in!r}",
            )

        self._cache = _CachedToken(
            access_token=access_token,
            expires_at=time.monotonic() + float(expires_in),
        )
        return access_token

    @staticmethod
    def _backoff_delay(attempt: int) -> float:
        """Exponential backoff with a small jitter to avoid thundering herds."""
        base = _BACKOFF_BASE_SECONDS * (_BACKOFF_EXPONENT ** attempt)
        jitter = random.uniform(0, _BACKOFF_BASE_SECONDS)
        return base + jitter

    def _raise_for_status(self, response: httpx.Response) -> None:
        """Map HTTP status to auth-specific exceptions before retry decisions."""
        if response.status_code == 401:
            raise InvalidCredentialError(
                f"Account-service rejected the credential (401) at "
                f"{self._exchange_url}. Check that the client secret / API "
                f"key is correct and not revoked.",
            )
        if response.status_code == 400:
            raise TokenExchangeError(
                f"Account-service rejected the token-exchange request (400) "
                f"at {self._exchange_url}. This commonly indicates the "
                f"server_url is pointing somewhere other than account-service "
                f"(for example, at platform-api). Response body: "
                f"{response.text[:500]}",
            )

    def _handle_outage(self, last_error: Optional[Exception]) -> str:
        """Serve a still-unexpired cached JWT after exhausting retries, else raise."""
        now = time.monotonic()
        cached = self._cached_token_if_not_expired(now)
        if cached is not None:
            logger.warning(
                "Account-service unavailable during token exchange; "
                "serving cached JWT while still within its absolute TTL. "
                "Last error: %s",
                last_error,
            )
            return cached
        raise TokenExchangeError(
            f"Token exchange failed after {self._max_retries + 1} attempt(s) "
            f"and no valid cached token is available: {last_error}",
        ) from last_error
