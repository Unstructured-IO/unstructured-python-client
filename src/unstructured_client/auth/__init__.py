"""Transparent token-exchange auth helpers for ``unstructured-client``.

Pass one of these instances as ``api_key_auth`` to :class:`~unstructured_client.UnstructuredClient`
and the SDK will automatically exchange your credential for a short-lived
account-service JWT, cache it, refresh before expiry, and send it as
``Authorization: Bearer`` instead of ``unstructured-api-key``::

    from unstructured_client import UnstructuredClient
    from unstructured_client.auth import ClientCredentials

    client = UnstructuredClient(
        api_key_auth=ClientCredentials(
            client_secret="uns_sk_...",
            server_url="https://accounts.unstructuredapp.io",
        ),
    )

Plain-string ``api_key_auth="..."`` continues to work unchanged and is sent
as the ``unstructured-api-key`` header.
"""

from ._exceptions import (
    InvalidCredentialError,
    TokenExchangeDisabledError,
    TokenExchangeError,
)
from .client_credentials import AsyncClientCredentials, ClientCredentials
from .legacy_api_key import AsyncLegacyKeyExchange, LegacyKeyExchange

__all__ = [
    "AsyncClientCredentials",
    "AsyncLegacyKeyExchange",
    "ClientCredentials",
    "InvalidCredentialError",
    "LegacyKeyExchange",
    "TokenExchangeDisabledError",
    "TokenExchangeError",
]
