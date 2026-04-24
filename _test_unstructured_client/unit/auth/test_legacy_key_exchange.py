"""Unit tests for :class:`unstructured_client.auth.LegacyKeyExchange`.

These only assert the surface differences from :class:`ClientCredentials`
(grant type, credential field). The full caching / retry / concurrency
behavior is covered in ``test_client_credentials.py`` since
:class:`LegacyKeyExchange` inherits that machinery unchanged.
"""

from __future__ import annotations

import httpx
import pytest

from unstructured_client.auth import (
    AsyncLegacyKeyExchange,
    InvalidCredentialError,
    LegacyKeyExchange,
)

from ._mock_transport import (
    AsyncScriptedTransport,
    ScriptedTransport,
    body_of,
    exchange_response,
)

SERVER_URL = "https://accounts.example.test"
LEGACY_KEY = "uns_ak_legacy_example"


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(
        "unstructured_client.auth.client_credentials.time.sleep",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "unstructured_client.auth.client_credentials.asyncio.sleep",
        _noop_async_sleep,
    )


async def _noop_async_sleep(*_args, **_kwargs):
    return None


class DescribeLegacyKeyExchangeBody:
    def it_sends_grant_type_api_key_and_api_key_field(self):
        transport = ScriptedTransport([exchange_response(access_token="jwt-1")])
        http_client = httpx.Client(transport=transport)
        lke = LegacyKeyExchange(
            api_key=LEGACY_KEY,
            server_url=SERVER_URL,
            http_client=http_client,
        )

        assert lke() == "jwt-1"

        req = transport.requests[0]
        assert body_of(req) == {"grant_type": "api_key", "api_key": LEGACY_KEY}

    def it_propagates_401_as_invalid_credential(self):
        transport = ScriptedTransport([httpx.Response(401, json={"detail": "bad"})])
        http_client = httpx.Client(transport=transport)
        lke = LegacyKeyExchange(
            api_key=LEGACY_KEY,
            server_url=SERVER_URL,
            http_client=http_client,
        )

        with pytest.raises(InvalidCredentialError):
            lke()


class DescribeAsyncLegacyKeyExchangeBody:
    @pytest.mark.asyncio
    async def it_sends_grant_type_api_key_and_api_key_field(self):
        transport = AsyncScriptedTransport([exchange_response(access_token="jwt-1")])
        http_client = httpx.AsyncClient(transport=transport)
        alke = AsyncLegacyKeyExchange(
            api_key=LEGACY_KEY,
            server_url=SERVER_URL,
            http_client=http_client,
        )

        token = await alke.acquire()

        assert token == "jwt-1"
        assert body_of(transport.requests[0]) == {
            "grant_type": "api_key",
            "api_key": LEGACY_KEY,
        }


class DescribeLegacyKeyExchangeConstruction:
    @pytest.mark.parametrize("bad", ["", None])
    def it_rejects_empty_api_key(self, bad):
        with pytest.raises(ValueError):
            LegacyKeyExchange(api_key=bad, server_url=SERVER_URL)  # type: ignore[arg-type]
