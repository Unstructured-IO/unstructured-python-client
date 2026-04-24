"""Unit tests for :class:`unstructured_client.auth.AsyncClientCredentials`."""

from __future__ import annotations

import asyncio
from typing import List

import httpx
import pytest

from unstructured_client.auth import (
    AsyncClientCredentials,
    InvalidCredentialError,
    TokenExchangeError,
)

from ._mock_transport import AsyncScriptedTransport, body_of, exchange_response

SERVER_URL = "https://accounts.example.test"
SECRET = "uns_sk_async_example"


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    async def _noop(*_args, **_kwargs):
        return None

    monkeypatch.setattr(
        "unstructured_client.auth.client_credentials.asyncio.sleep",
        _noop,
    )


@pytest.fixture
def fake_clock(monkeypatch):
    state = {"now": 2_000_000.0}

    def _now() -> float:
        return state["now"]

    monkeypatch.setattr("unstructured_client.auth._base.time.monotonic", _now)
    monkeypatch.setattr(
        "unstructured_client.auth.client_credentials.time.monotonic", _now
    )
    return state


class DescribeAsyncClientCredentials:
    @pytest.mark.asyncio
    async def it_exchanges_then_caches(self, fake_clock):
        transport = AsyncScriptedTransport(
            [exchange_response(access_token="jwt-1", expires_in=900)]
        )
        http_client = httpx.AsyncClient(transport=transport)
        acc = AsyncClientCredentials(
            client_secret=SECRET,
            server_url=SERVER_URL,
            http_client=http_client,
        )

        first = await acc.acquire()
        second = await acc.acquire()

        assert first == second == "jwt-1"
        assert len(transport.requests) == 1
        assert body_of(transport.requests[0]) == {
            "grant_type": "client_credentials",
            "client_secret": SECRET,
        }

    @pytest.mark.asyncio
    async def it_raises_invalid_credential_on_401(self, fake_clock):
        transport = AsyncScriptedTransport(
            [httpx.Response(401, json={"detail": "bad"})]
        )
        http_client = httpx.AsyncClient(transport=transport)
        acc = AsyncClientCredentials(
            client_secret=SECRET,
            server_url=SERVER_URL,
            http_client=http_client,
            max_retries=5,
        )

        with pytest.raises(InvalidCredentialError):
            await acc.acquire()

    @pytest.mark.asyncio
    async def it_retries_5xx_then_succeeds(self, fake_clock):
        transport = AsyncScriptedTransport(
            [
                httpx.Response(500),
                httpx.Response(502),
                exchange_response(access_token="jwt-1", expires_in=900),
            ]
        )
        http_client = httpx.AsyncClient(transport=transport)
        acc = AsyncClientCredentials(
            client_secret=SECRET,
            server_url=SERVER_URL,
            http_client=http_client,
            max_retries=3,
        )

        assert await acc.acquire() == "jwt-1"
        assert len(transport.requests) == 3

    @pytest.mark.asyncio
    async def it_serializes_concurrent_acquires(self, fake_clock):
        """Ten concurrent ``acquire()`` calls must share one exchange."""
        transport = AsyncScriptedTransport(
            [exchange_response(access_token="jwt-1", expires_in=900)]
        )
        http_client = httpx.AsyncClient(transport=transport)
        acc = AsyncClientCredentials(
            client_secret=SECRET,
            server_url=SERVER_URL,
            http_client=http_client,
        )

        results: List[str] = await asyncio.gather(*(acc.acquire() for _ in range(10)))

        assert results == ["jwt-1"] * 10
        assert len(transport.requests) == 1

    @pytest.mark.asyncio
    async def it_raises_outage_error_without_cached_token(self, fake_clock):
        transport = AsyncScriptedTransport([httpx.Response(500)] * 4)
        http_client = httpx.AsyncClient(transport=transport)
        acc = AsyncClientCredentials(
            client_secret=SECRET,
            server_url=SERVER_URL,
            http_client=http_client,
            max_retries=3,
        )

        with pytest.raises(TokenExchangeError):
            await acc.acquire()

    def it_sync_call_works_outside_running_loop(self, fake_clock):
        """``__call__`` is the SDK entry point; must work without a loop."""
        transport = AsyncScriptedTransport(
            [exchange_response(access_token="jwt-1", expires_in=900)]
        )
        http_client = httpx.AsyncClient(transport=transport)
        acc = AsyncClientCredentials(
            client_secret=SECRET,
            server_url=SERVER_URL,
            http_client=http_client,
        )

        assert acc() == "jwt-1"

    @pytest.mark.asyncio
    async def it_sync_call_works_inside_running_loop(self, fake_clock):
        """Driving __call__ from a running loop offloads to a worker thread."""
        transport = AsyncScriptedTransport(
            [exchange_response(access_token="jwt-1", expires_in=900)]
        )
        http_client = httpx.AsyncClient(transport=transport)
        acc = AsyncClientCredentials(
            client_secret=SECRET,
            server_url=SERVER_URL,
            http_client=http_client,
        )

        token = await asyncio.to_thread(acc)
        assert token == "jwt-1"
