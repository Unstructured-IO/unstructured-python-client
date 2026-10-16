"""TCP keepalive configuration and transport integration."""

import asyncio
import socket
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from unittest.mock import patch

import httpcore
import httpx
import pytest

from unstructured_client import UnstructuredClient
from unstructured_client._hooks.custom import http_transport as transport


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for suffix in ("", "_IDLE", "_INTERVAL", "_COUNT"):
        monkeypatch.delenv("UNSTRUCTURED_CLIENT_TCP_KEEPALIVE" + suffix, raising=False)
    monkeypatch.setenv("NO_PROXY", "*")


DEFAULTS = transport.TCPKeepAlive(enabled=True)
BASE_OPTIONS = [(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)]


def _close(client):
    if isinstance(client, httpx.AsyncClient):
        asyncio.run(client.aclose())
    else:
        client.close()


@contextmanager
def local_server(handler):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_port
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.mark.parametrize("attrs_to_set,expected_options", [
    ({"TCP_KEEPIDLE": 100, "TCP_KEEPINTVL": 101, "TCP_KEEPCNT": 102},
     [(socket.IPPROTO_TCP, 100, DEFAULTS.idle),
      (socket.IPPROTO_TCP, 101, DEFAULTS.interval),
      (socket.IPPROTO_TCP, 102, DEFAULTS.count)]),
    ({"TCP_KEEPALIVE": 100, "TCP_KEEPINTVL": 101, "TCP_KEEPCNT": 102},
     [(socket.IPPROTO_TCP, 100, DEFAULTS.idle),
      (socket.IPPROTO_TCP, 101, DEFAULTS.interval),
      (socket.IPPROTO_TCP, 102, DEFAULTS.count)]),
    ({"TCP_KEEPALIVE": 100}, [(socket.IPPROTO_TCP, 100, DEFAULTS.idle)]),
    ({}, []),
], ids=["linux", "macos", "macos_old", "windows"])
def test_unit_platform_options(monkeypatch, attrs_to_set, expected_options):
    for name in ("TCP_KEEPIDLE", "TCP_KEEPALIVE", "TCP_KEEPINTVL", "TCP_KEEPCNT"):
        monkeypatch.delattr(socket, name, raising=False)
    for name, value in attrs_to_set.items():
        monkeypatch.setattr(socket, name, value, raising=False)
    assert transport.resolve_tcp_keepalive().socket_options() == BASE_OPTIONS + expected_options


@pytest.mark.parametrize("value", ["0", "false", "False", " FALSE "])
def test_unit_disabled(monkeypatch, caplog, value):
    monkeypatch.setenv("UNSTRUCTURED_CLIENT_TCP_KEEPALIVE", value)
    for suffix in ("IDLE", "INTERVAL", "COUNT"):
        monkeypatch.setenv("UNSTRUCTURED_CLIENT_TCP_KEEPALIVE_" + suffix, "invalid")
    settings = transport.resolve_tcp_keepalive()
    assert settings.socket_options() == []
    assert settings.describe() == "off"
    assert not caplog.records


@pytest.mark.parametrize("suffix,value,expected", [
    (suffix, value, expected)
    for suffix, maximum in (
        ("IDLE", transport.MAX_IDLE),
        ("INTERVAL", transport.MAX_INTERVAL),
        ("COUNT", transport.MAX_COUNT),
    )
    for value, expected in (
        *[(invalid, getattr(DEFAULTS, suffix.lower()))
          for invalid in ("0", "-1", "bad", "1.5", "", str(maximum + 1))],
        ("1", 1),
        (str(maximum), maximum),
    )
])
def test_unit_value_bounds(monkeypatch, caplog, suffix, value, expected):
    monkeypatch.setenv("UNSTRUCTURED_CLIENT_TCP_KEEPALIVE_" + suffix, value)
    assert getattr(transport.resolve_tcp_keepalive(), suffix.lower()) == expected
    assert ("using default" in caplog.text) == (value != str(expected))


@pytest.mark.parametrize("asynchronous", [False, True])
def test_unit_missing_proxy_helper_client_options(monkeypatch, asynchronous):
    monkeypatch.setattr(transport, "get_environment_proxies", None)
    if asynchronous:
        options = {"verify": False, "cert": "client.pem", "limits": httpx.Limits(max_connections=3)}
        with patch.object(httpx, "AsyncClient") as constructor:
            transport.create_async_http_client(timeout=42, **options)
        constructor.assert_called_once_with(timeout=42, **options)
    else:
        with patch.object(httpx, "Client") as constructor:
            transport.create_http_client()
        constructor.assert_called_once_with()


def test_unit_custom_values(monkeypatch):
    for suffix, value in (("IDLE", "5"), ("INTERVAL", "6"), ("COUNT", "7")):
        monkeypatch.setenv("UNSTRUCTURED_CLIENT_TCP_KEEPALIVE_" + suffix, value)
    settings = transport.resolve_tcp_keepalive()
    assert settings == transport.TCPKeepAlive(True, 5, 6, 7)
    assert settings.describe() == "idle=5s interval=6s count=7"


def test_unit_sdk_owned_clients():
    sdk = UnstructuredClient()
    options = transport.resolve_tcp_keepalive().socket_options()
    assert sdk.sdk_configuration.client._transport.base_transport._pool._socket_options == options
    assert sdk.sdk_configuration.async_client._transport._pool._socket_options == options
    _close(sdk.sdk_configuration.client)
    _close(sdk.sdk_configuration.async_client)


def test_unit_supplied_clients_untouched():
    sync = httpx.Client()
    asynchronous = httpx.AsyncClient()
    sync_transport = sync._transport
    async_transport = asynchronous._transport
    UnstructuredClient(client=sync, async_client=asynchronous)
    assert sync._transport.base_transport is sync_transport
    assert asynchronous._transport is async_transport
    _close(sync)
    _close(asynchronous)


@pytest.mark.parametrize("missing_proxy_helper", [False, True])
@pytest.mark.parametrize("asynchronous", [False, True])
def test_unit_environment_proxy_routes(monkeypatch, asynchronous, missing_proxy_helper):
    if missing_proxy_helper:
        monkeypatch.setattr(transport, "get_environment_proxies", None)
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:8123")
    monkeypatch.setenv("NO_PROXY", "excluded.example")
    client = transport.create_async_http_client() if asynchronous else transport.create_http_client()
    proxied = client._transport_for_url(httpx.URL("https://api.example"))
    assert isinstance(proxied._pool, httpcore.AsyncHTTPProxy if asynchronous else httpcore.HTTPProxy)
    assert proxied._pool._proxy_url.host == b"127.0.0.1"
    assert proxied._pool._socket_options is None
    if missing_proxy_helper:
        assert client._transport._pool._socket_options is None
    assert client._transport_for_url(httpx.URL("https://excluded.example")) is client._transport
    _close(client)


@pytest.mark.parametrize("asynchronous", [False, True])
def test_unit_real_socket_keepalive(asynchronous):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"ok")

    def check(response):
        stream = response.extensions["network_stream"]
        sock = stream.get_extra_info("socket")
        assert sock.getsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE)

    async def request():
        async with transport.create_async_http_client() as client:
            async with client.stream("GET", url) as response:
                check(response)
                await response.aread()

    with local_server(Handler) as port:
        url = f"http://127.0.0.1:{port}"
        if asynchronous:
            asyncio.run(request())
        else:
            with transport.create_http_client() as client:
                with client.stream("GET", url) as response:
                    check(response)
                    response.read()


@pytest.mark.parametrize("asynchronous", [False, True])
def test_unit_https_proxy_receives_connect(monkeypatch, asynchronous):
    destinations = []

    class ProxyHandler(BaseHTTPRequestHandler):
        def do_CONNECT(self):
            destinations.append(self.path)
            self.send_error(502)

    async def request():
        async with transport.create_async_http_client() as client:
            await client.get("https://proxy-target.invalid/")

    with local_server(ProxyHandler) as port:
        monkeypatch.setenv("HTTPS_PROXY", f"http://127.0.0.1:{port}")
        monkeypatch.setenv("NO_PROXY", "")
        with pytest.raises(httpx.ProxyError, match="502"):
            if asynchronous:
                asyncio.run(request())
            else:
                with transport.create_http_client() as client:
                    client.get("https://proxy-target.invalid/")
        assert destinations == ["proxy-target.invalid:443"]
