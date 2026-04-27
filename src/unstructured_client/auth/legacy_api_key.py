"""``LegacyKeyExchange`` - transitional api-key -> JWT exchange.

This mirrors :class:`ClientCredentials` but uses ``grant_type=api_key`` so
customers still on legacy api-tracking keys can get JWT-backed requests
without re-issuing credentials. The class is intentionally flagged as
transitional and will be removed once legacy keys are decommissioned.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from .client_credentials import AsyncClientCredentials, ClientCredentials


class LegacyKeyExchange(ClientCredentials):
    """Synchronous ``api_key`` grant callable (transitional).

    Accepts a legacy raw API key (validated by account-service against
    api-tracking) and exchanges it for an account-service JWT. Caching,
    refresh, and retry behavior are identical to
    :class:`~unstructured_client.auth.ClientCredentials`.

    The legacy key is stored once on the inherited ``_client_secret`` slot;
    only the request body shape differs from the parent class.

    .. deprecated::
        Prefer :class:`~unstructured_client.auth.ClientCredentials` with a
        ``uns_sk_...`` client secret. ``LegacyKeyExchange`` exists only to
        bridge customers during the API Key Scoping rollout and will be
        removed once legacy keys are retired.
    """

    def __init__(
        self,
        api_key: str,
        *,
        server_url: str,
        refresh_buffer_seconds: int = 60,
        request_timeout_seconds: float = 30.0,
        max_retries: int = 3,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        if not api_key:
            raise ValueError("api_key must be a non-empty string")
        super().__init__(
            client_secret=api_key,
            server_url=server_url,
            refresh_buffer_seconds=refresh_buffer_seconds,
            request_timeout_seconds=request_timeout_seconds,
            max_retries=max_retries,
            http_client=http_client,
        )

    def _build_request_body(self) -> Dict[str, Any]:
        return {"grant_type": "api_key", "api_key": self._client_secret}


class AsyncLegacyKeyExchange(AsyncClientCredentials):
    """Asynchronous twin of :class:`LegacyKeyExchange` (transitional).

    .. deprecated::
        Prefer :class:`~unstructured_client.auth.AsyncClientCredentials` with
        a ``uns_sk_...`` client secret.
    """

    def __init__(
        self,
        api_key: str,
        *,
        server_url: str,
        refresh_buffer_seconds: int = 60,
        request_timeout_seconds: float = 30.0,
        max_retries: int = 3,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        if not api_key:
            raise ValueError("api_key must be a non-empty string")
        super().__init__(
            client_secret=api_key,
            server_url=server_url,
            refresh_buffer_seconds=refresh_buffer_seconds,
            request_timeout_seconds=request_timeout_seconds,
            max_retries=max_retries,
            http_client=http_client,
        )

    def _build_request_body(self) -> Dict[str, Any]:
        return {"grant_type": "api_key", "api_key": self._client_secret}
