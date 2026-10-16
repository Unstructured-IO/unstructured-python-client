"""TCP keepalive configuration and transport integration."""

import asyncio
import socket
import sys
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
    if hasattr(transport, "_log_keepalive_unavailable"):
        transport._log_keepalive_unavailable.cache_clear()
    for suffix in ("", "_IDLE", "_INTERVAL", "_COUNT"):
        monkeypatch.delenv("UNSTRUCTURED_CLIENT_TCP_KEEPALIVE" + suffix, raising=False)
    monkeypatch.setenv("NO_PROXY", "*")


@pytest.mark.parametrize("platform", ["linux", "macos", "macos_old", "windows"])
def test_unit_platform_options(monkeypatch, platform):
    for name in ("TCP_KEEPIDLE", "TCP_KEEPALIVE", "TCP_KEEPINTVL", "TCP_KEEPCNT"):
        monkeypatch.delattr(socket, name, raising=False)
    expected = [(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)]
    if platform != "windows":
        monkeypatch.setattr(socket, "TCP_KEEPIDLE" if platform == "linux" else "TCP_KEEPALIVE", 100, raising=False)
        expected.append((socket.IPPROTO_TCP, 100, 60))
        if platform != "macos_old":
            monkeypatch.setattr(socket, "TCP_KEEPINTVL", 101, raising=False)
            monkeypatch.setattr(socket, "TCP_KEEPCNT", 102, raising=False)
            expected += [(socket.IPPROTO_TCP, 101, 30), (socket.IPPROTO_TCP, 102, 5)]
    assert transport.resolve_tcp_keepalive().socket_options() == expected


@pytest.mark.parametrize("value", ["0", "false", "False", " FALSE "])
def test_unit_disabled(monkeypatch, value):
    monkeypatch.setenv("UNSTRUCTURED_CLIENT_TCP_KEEPALIVE", value)
    assert transport.resolve_tcp_keepalive().socket_options() == []


@pytest.mark.parametrize("suffix,default", [("IDLE", 60), ("INTERVAL", 30), ("COUNT", 5)])
@pytest.mark.parametrize("value", ["0", "-1", "bad", "1.5", ""])
def test_unit_invalid_value(monkeypatch, caplog, suffix, default, value):
    monkeypatch.setenv("UNSTRUCTURED_CLIENT_TCP_KEEPALIVE_" + suffix, value)
    assert getattr(transport.resolve_tcp_keepalive(), suffix.lower()) == default
    assert "using default" in caplog.text


@pytest.mark.parametrize("suffix,maximum,default", [
    ("IDLE", 32767, 60), ("INTERVAL", 32767, 30), ("COUNT", 127, 5),
])
@pytest.mark.parametrize("above_maximum", [False, True])
def test_unit_value_bounds(monkeypatch, caplog, suffix, maximum, default, above_maximum):
    monkeypatch.setenv("UNSTRUCTURED_CLIENT_TCP_KEEPALIVE_" + suffix,
                       str(maximum + int(above_maximum)))
    expected = default if above_maximum else maximum
    assert getattr(transport.resolve_tcp_keepalive(), suffix.lower()) == expected
    assert ("using default" in caplog.text) == above_maximum


@pytest.mark.parametrize("asynchronous", [False, True])
def test_unit_missing_proxy_helper_client_options(monkeypatch, asynchronous):
    monkeypatch.setattr(transport, "get_environment_proxies", None)
    if asynchronous:
        options = {"verify": False, "cert": None, "limits": httpx.Limits(max_connections=3)}
        with patch.object(httpx, "AsyncClient") as constructor:
            transport.create_async_http_client(timeout=42, transport_options=options)
        constructor.assert_called_once_with(timeout=42, **options)
    else:
        with patch.object(httpx, "Client") as constructor:
            transport.create_http_client()
        constructor.assert_called_once_with()


def test_unit_missing_proxy_helper_logs_once(monkeypatch, caplog):
    monkeypatch.setattr(transport, "get_environment_proxies", None)
    caplog.set_level("DEBUG", logger=transport.logger.name)
    with transport.create_http_client():
        pass
    asyncio.run(transport.create_async_http_client().aclose())
    messages = [record for record in caplog.records if "TCP keepalive is unavailable" in record.message]
    assert len(messages) == 1
    assert messages[0].levelname == "DEBUG"


def test_unit_custom_values(monkeypatch):
    for suffix, value in (("IDLE", "5"), ("INTERVAL", "6"), ("COUNT", "7")):
        monkeypatch.setenv("UNSTRUCTURED_CLIENT_TCP_KEEPALIVE_" + suffix, value)
    assert transport.resolve_tcp_keepalive() == transport.TCPKeepAlive(True, 5, 6, 7)


def test_unit_sdk_owned_clients():
    sdk = UnstructuredClient()
    options = transport.resolve_tcp_keepalive().socket_options()
    assert sdk.sdk_configuration.client._transport.base_transport._pool._socket_options == options
    assert sdk.sdk_configuration.async_client._transport._pool._socket_options == options
    sdk.sdk_configuration.client.close()
    asyncio.run(sdk.sdk_configuration.async_client.aclose())


def test_unit_supplied_clients_untouched():
    sync = httpx.Client()
    asynchronous = httpx.AsyncClient()
    sync_transport = sync._transport
    async_transport = asynchronous._transport
    sdk = UnstructuredClient(client=sync, async_client=asynchronous)
    assert sdk.sdk_configuration.client is sync
    assert sdk.sdk_configuration.async_client is asynchronous
    assert sync._transport.base_transport is sync_transport
    assert asynchronous._transport is async_transport
    assert sync_transport._pool._socket_options is None
    assert asynchronous._transport._pool._socket_options is None
    sync.close()
    asyncio.run(asynchronous.aclose())


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
    if missing_proxy_helper:
        assert client._transport._pool._socket_options is None
        assert proxied._pool._socket_options is None
    assert client._transport_for_url(httpx.URL("https://excluded.example")) is client._transport
    if asynchronous:
        asyncio.run(client.aclose())
    else:
        client.close()


@pytest.mark.parametrize("asynchronous", [False, True])
def test_unit_real_socket_keepalive(asynchronous):
    if not hasattr(socket, "SO_KEEPALIVE"):
        pytest.skip("SO_KEEPALIVE unavailable")

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"ok")

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}"

    def check(response):
        stream = response.extensions["network_stream"]
        sock = stream.get_extra_info("socket")
        enabled = sock.getsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE)
        # Darwin reports the option bit mask rather than a normalized boolean.
        if sys.platform == "darwin":
            assert enabled != 0
        else:
            assert enabled == 1

    async def request():
        async with transport.create_async_http_client() as client:
            async with client.stream("GET", url) as response:
                check(response)
                await response.aread()

    try:
        if asynchronous:
            asyncio.run(request())
        else:
            with transport.create_http_client() as client:
                with client.stream("GET", url) as response:
                    check(response)
                    response.read()
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.mark.parametrize("asynchronous", [False, True])
def test_unit_https_proxy_receives_connect(monkeypatch, asynchronous):
    destinations = []

    class ProxyHandler(BaseHTTPRequestHandler):
        def do_CONNECT(self):
            destinations.append(self.path)
            self.send_error(502)

    server = ThreadingHTTPServer(("127.0.0.1", 0), ProxyHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("HTTPS_PROXY", f"http://127.0.0.1:{server.server_port}")
    monkeypatch.setenv("NO_PROXY", "")

    async def request():
        async with transport.create_async_http_client() as client:
            await client.get("https://proxy-target.invalid/")

    try:
        with pytest.raises(httpx.ProxyError, match="502"):
            if asynchronous:
                asyncio.run(request())
            else:
                with transport.create_http_client() as client:
                    client.get("https://proxy-target.invalid/")
        assert destinations == ["proxy-target.invalid:443"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
