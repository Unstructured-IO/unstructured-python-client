"""Unit tests for :class:`unstructured_client.auth.ClientCredentials`.

Uses a scripted :class:`httpx.MockTransport` to stand in for the
``/auth/token-exchange`` endpoint; no real network IO.
"""

from __future__ import annotations

import logging
import threading
from typing import List, Tuple

import httpx
import pytest

from unstructured_client.auth import (
    ClientCredentials,
    InvalidCredentialError,
    TokenExchangeDisabledError,
    TokenExchangeError,
)

from ._mock_transport import (
    ScriptedTransport,
    body_of,
    exchange_response,
)

SERVER_URL = "https://accounts.example.test"
SECRET = "uns_sk_example_secret"


def _make_client_credentials(
    steps: List,
    *,
    refresh_buffer_seconds: int = 60,
    max_retries: int = 3,
) -> Tuple[ClientCredentials, ScriptedTransport]:
    transport = ScriptedTransport(steps)
    http_client = httpx.Client(transport=transport)
    cc = ClientCredentials(
        client_secret=SECRET,
        server_url=SERVER_URL,
        refresh_buffer_seconds=refresh_buffer_seconds,
        max_retries=max_retries,
        http_client=http_client,
    )
    return cc, transport


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    """Neutralize exponential-backoff sleeps so 5xx tests run instantly."""
    monkeypatch.setattr(
        "unstructured_client.auth.client_credentials.time.sleep",
        lambda *_args, **_kwargs: None,
    )


@pytest.fixture
def fake_clock(monkeypatch):
    """Controllable ``time.monotonic`` shared by the auth module."""
    state = {"now": 1_000_000.0}

    def _now() -> float:
        return state["now"]

    monkeypatch.setattr("unstructured_client.auth._base.time.monotonic", _now)
    monkeypatch.setattr(
        "unstructured_client.auth.client_credentials.time.monotonic", _now
    )
    return state


def test_posts_client_credentials_body(fake_clock):
    cc, transport = _make_client_credentials(
        [exchange_response(access_token="jwt-1", expires_in=900)]
    )

    token = cc()

    assert token == "jwt-1"
    assert len(transport.requests) == 1
    req = transport.requests[0]
    assert req.method == "POST"
    assert req.url.path == "/auth/token-exchange"
    assert req.headers["content-type"] == "application/json"
    assert body_of(req) == {
        "grant_type": "client_credentials",
        "client_secret": SECRET,
    }


def test_strips_trailing_slash_from_server_url(fake_clock):
    transport = ScriptedTransport([exchange_response()])
    http_client = httpx.Client(transport=transport)
    cc = ClientCredentials(
        client_secret=SECRET,
        server_url=f"{SERVER_URL}/",
        http_client=http_client,
    )

    cc()

    assert str(transport.requests[0].url).endswith("/auth/token-exchange")
    assert "//auth/token-exchange" not in str(transport.requests[0].url)


def test_returns_cached_jwt_within_ttl(fake_clock):
    cc, transport = _make_client_credentials(
        [exchange_response(access_token="jwt-1", expires_in=900)]
    )

    first = cc()
    second = cc()
    third = cc()

    assert first == second == third == "jwt-1"
    assert len(transport.requests) == 1


def test_refreshes_when_within_buffer_of_expiry(fake_clock):
    cc, transport = _make_client_credentials(
        [
            exchange_response(access_token="jwt-1", expires_in=900),
            exchange_response(access_token="jwt-2", expires_in=900),
        ],
        refresh_buffer_seconds=60,
    )

    assert cc() == "jwt-1"
    fake_clock["now"] += 900 - 59  # within the 60s refresh buffer
    assert cc() == "jwt-2"
    assert len(transport.requests) == 2


def test_does_not_refresh_outside_buffer(fake_clock):
    cc, transport = _make_client_credentials(
        [exchange_response(access_token="jwt-1", expires_in=900)],
        refresh_buffer_seconds=60,
    )

    cc()
    fake_clock["now"] += 900 - 120  # still 120s from expiry
    cc()

    assert len(transport.requests) == 1


def test_raises_invalid_credential_on_401_without_retry(fake_clock):
    cc, transport = _make_client_credentials(
        [httpx.Response(401, json={"detail": "invalid"})],
        max_retries=5,
    )

    with pytest.raises(InvalidCredentialError):
        cc()
    assert len(transport.requests) == 1


def test_raises_on_400_without_retry(fake_clock):
    cc, transport = _make_client_credentials(
        [httpx.Response(400, json={"detail": "bad"})],
        max_retries=5,
    )

    with pytest.raises(TokenExchangeError):
        cc()
    assert len(transport.requests) == 1


def test_raises_disabled_when_server_opts_out(fake_clock):
    cc, transport = _make_client_credentials(
        [exchange_response(access_token=None, expires_in=0, token_exchange_enabled=False)]
    )

    with pytest.raises(TokenExchangeDisabledError):
        cc()
    assert len(transport.requests) == 1


def test_retries_5xx_then_succeeds(fake_clock):
    cc, transport = _make_client_credentials(
        [
            httpx.Response(503, json={}),
            httpx.Response(500, json={}),
            exchange_response(access_token="jwt-1", expires_in=900),
        ],
        max_retries=3,
    )

    assert cc() == "jwt-1"
    assert len(transport.requests) == 3


def test_retries_network_errors_then_succeeds(fake_clock):
    cc, transport = _make_client_credentials(
        [
            httpx.ConnectError("refused"),
            httpx.ReadTimeout("slow"),
            exchange_response(access_token="jwt-1", expires_in=900),
        ],
        max_retries=3,
    )

    assert cc() == "jwt-1"
    assert len(transport.requests) == 3


def test_raises_when_retries_exhausted_without_cached_token(fake_clock):
    cc, transport = _make_client_credentials(
        [httpx.Response(500, json={})] * 4,
        max_retries=3,
    )

    with pytest.raises(TokenExchangeError):
        cc()
    assert len(transport.requests) == 4


def test_serves_cached_jwt_during_outage_when_still_within_ttl(fake_clock, caplog):
    cc, transport = _make_client_credentials(
        [
            exchange_response(access_token="jwt-1", expires_in=900),
            httpx.Response(500, json={}),
            httpx.Response(502, json={}),
            httpx.Response(503, json={}),
            httpx.Response(504, json={}),
        ],
        max_retries=3,
        refresh_buffer_seconds=60,
    )

    assert cc() == "jwt-1"
    fake_clock["now"] += 900 - 30  # past refresh buffer but before absolute expiry

    caplog.set_level(logging.WARNING, logger="unstructured-client.auth")
    assert cc() == "jwt-1"
    assert any(
        "serving cached JWT" in record.getMessage() for record in caplog.records
    )


def test_raises_when_cached_token_has_fully_expired(fake_clock):
    cc, transport = _make_client_credentials(
        [
            exchange_response(access_token="jwt-1", expires_in=900),
            httpx.Response(500, json={}),
            httpx.Response(500, json={}),
            httpx.Response(500, json={}),
            httpx.Response(500, json={}),
        ],
        max_retries=3,
        refresh_buffer_seconds=60,
    )

    assert cc() == "jwt-1"
    fake_clock["now"] += 1000  # past absolute expiry

    with pytest.raises(TokenExchangeError):
        cc()


def test_collapses_concurrent_calls_into_one_exchange():
    """Ten threads calling ``cc()`` concurrently must drive a single exchange."""
    barrier = threading.Barrier(10)
    transport = ScriptedTransport(
        [exchange_response(access_token="jwt-1", expires_in=900)]
    )
    http_client = httpx.Client(transport=transport)
    cc = ClientCredentials(
        client_secret=SECRET,
        server_url=SERVER_URL,
        http_client=http_client,
    )

    results: List[str] = []

    def _worker():
        barrier.wait()
        results.append(cc())

    threads = [threading.Thread(target=_worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert results == ["jwt-1"] * 10
    assert len(transport.requests) == 1


@pytest.mark.parametrize("bad_secret", ["", None])
def test_rejects_empty_secret(bad_secret):
    with pytest.raises(ValueError):
        ClientCredentials(
            client_secret=bad_secret,  # type: ignore[arg-type]
            server_url=SERVER_URL,
        )


def test_rejects_empty_server_url():
    with pytest.raises(ValueError):
        ClientCredentials(client_secret=SECRET, server_url="")


@pytest.mark.parametrize("bad_buffer", [-1, -100])
def test_rejects_negative_refresh_buffer(bad_buffer):
    with pytest.raises(ValueError):
        ClientCredentials(
            client_secret=SECRET,
            server_url=SERVER_URL,
            refresh_buffer_seconds=bad_buffer,
        )


def test_rejects_negative_max_retries():
    with pytest.raises(ValueError):
        ClientCredentials(
            client_secret=SECRET,
            server_url=SERVER_URL,
            max_retries=-1,
        )
