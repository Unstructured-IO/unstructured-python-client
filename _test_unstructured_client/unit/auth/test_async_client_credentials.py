"""Unit tests for :class:`unstructured_client.auth.AsyncClientCredentials`."""

from __future__ import annotations

import asyncio
import threading
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


@pytest.mark.asyncio
async def test_exchanges_then_caches(fake_clock):
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
async def test_raises_invalid_credential_on_401(fake_clock):
    transport = AsyncScriptedTransport([httpx.Response(401, json={"detail": "bad"})])
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
async def test_retries_5xx_then_succeeds(fake_clock):
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
async def test_serializes_concurrent_acquires(fake_clock):
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
async def test_raises_outage_error_without_cached_token(fake_clock):
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


def test_sync_call_works_outside_running_loop(fake_clock):
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
async def test_sync_call_works_inside_running_loop(fake_clock):
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


def test_sync_call_re_exchanges_after_cache_lapse_across_loops(fake_clock):
    """Regression: ``__call__`` must not crash on the second exchange.

    Each invocation outside a running loop spins a fresh event loop via
    ``asyncio.run``. The internal ``asyncio.Lock`` is created lazily inside
    ``acquire`` so it binds to whatever loop is current; if it were created
    in ``__init__`` it would stay bound to the first loop and ``async with``
    would raise ``RuntimeError`` on the second exchange.
    """
    transport = AsyncScriptedTransport(
        [
            exchange_response(access_token="jwt-1", expires_in=900),
            exchange_response(access_token="jwt-2", expires_in=900),
        ]
    )
    http_client = httpx.AsyncClient(transport=transport)
    acc = AsyncClientCredentials(
        client_secret=SECRET,
        server_url=SERVER_URL,
        http_client=http_client,
        refresh_buffer_seconds=60,
    )

    assert acc() == "jwt-1"
    fake_clock["now"] += 900 - 30  # past refresh buffer
    assert acc() == "jwt-2"
    assert len(transport.requests) == 2


@pytest.mark.asyncio
async def test_acquire_re_uses_correct_async_lock_after_loop_change(fake_clock):
    """The lazy per-loop lock must refresh when the running loop changes."""
    transport = AsyncScriptedTransport(
        [
            exchange_response(access_token="jwt-1", expires_in=900),
            exchange_response(access_token="jwt-2", expires_in=900),
        ]
    )
    http_client = httpx.AsyncClient(transport=transport)
    acc = AsyncClientCredentials(
        client_secret=SECRET,
        server_url=SERVER_URL,
        http_client=http_client,
        refresh_buffer_seconds=60,
    )

    first = await acc.acquire()
    assert first == "jwt-1"
    first_loop = acc._async_lock_loop  # type: ignore[attr-defined]

    fake_clock["now"] += 900 - 30  # past refresh buffer

    # Run the next exchange on a *different* event loop driven from a worker
    # thread; the lazy-init code path must re-bind the lock to that loop.
    second = await asyncio.to_thread(lambda: asyncio.run(acc.acquire()))
    assert second == "jwt-2"

    second_loop = acc._async_lock_loop  # type: ignore[attr-defined]
    assert second_loop is not None
    assert second_loop is not first_loop


def test_sync_call_coalesces_concurrent_threads_into_one_exchange(fake_clock):
    """Two OS threads racing into ``__call__`` must share one exchange."""
    barrier = threading.Barrier(2)
    transport = AsyncScriptedTransport(
        [exchange_response(access_token="jwt-1", expires_in=900)]
    )
    http_client = httpx.AsyncClient(transport=transport)
    acc = AsyncClientCredentials(
        client_secret=SECRET,
        server_url=SERVER_URL,
        http_client=http_client,
    )

    results = []

    def _worker():
        barrier.wait()
        results.append(acc())

    threads = [threading.Thread(target=_worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert results == ["jwt-1", "jwt-1"]
    assert len(transport.requests) == 1
