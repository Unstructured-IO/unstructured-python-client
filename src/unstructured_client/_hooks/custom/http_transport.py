"""HTTP clients with TCP keepalive and HTTPX environment proxy routing."""

import logging
import os
import socket
from dataclasses import dataclass
from typing import Any

import httpx
from httpx._utils import get_environment_proxies

from .common import UNSTRUCTURED_CLIENT_LOGGER_NAME

logger = logging.getLogger(UNSTRUCTURED_CLIENT_LOGGER_NAME)


def _positive_int(name: str, default: int) -> int:
    value = os.getenv(name, str(default))
    try:
        parsed = int(value)
        if parsed > 0:
            return parsed
    except ValueError:
        pass
    logger.warning("Invalid %s=%r; using default %d", name, value, default)
    return default


@dataclass(frozen=True)
class TCPKeepAlive:
    """Resolved TCP probe settings, in seconds and number of probes."""

    enabled: bool
    idle: int
    interval: int
    count: int

    def socket_options(self) -> list[tuple[int, int, int]]:
        """Use only the TCP options available on the current platform."""
        if not self.enabled:
            return []
        options = [(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)]
        idle_option = getattr(socket, "TCP_KEEPIDLE", None)
        if idle_option is None:
            idle_option = getattr(socket, "TCP_KEEPALIVE", None)
        for option, value in (
            (idle_option, self.idle),
            (getattr(socket, "TCP_KEEPINTVL", None), self.interval),
            (getattr(socket, "TCP_KEEPCNT", None), self.count),
        ):
            if option is not None:
                options.append((socket.IPPROTO_TCP, option, value))
        return options


def resolve_tcp_keepalive() -> TCPKeepAlive:
    """Read keepalive settings, falling back on invalid positive integers."""
    prefix = "UNSTRUCTURED_CLIENT_TCP_KEEPALIVE"
    return TCPKeepAlive(
        enabled=os.getenv(prefix, "1").strip().lower() not in ("0", "false"),
        idle=_positive_int(prefix + "_IDLE", 60),
        interval=_positive_int(prefix + "_INTERVAL", 30),
        count=_positive_int(prefix + "_COUNT", 5),
    )


def _client_transport_options(
    transport_type: Any,
    keepalive: TCPKeepAlive | None,
    transport_options: dict[str, Any],
) -> dict[str, Any]:
    settings = keepalive if keepalive is not None else resolve_tcp_keepalive()
    options = dict(transport_options, socket_options=settings.socket_options())
    # HTTPX disables automatic environment proxy discovery with a custom transport.
    # Reuse its URL patterns, including None mounts for NO_PROXY exclusions.
    mounts = {
        pattern: transport_type(proxy=proxy, **options) if proxy else None
        for pattern, proxy in get_environment_proxies().items()
    }
    return {"transport": transport_type(**options), "mounts": mounts}


def create_http_client() -> httpx.Client:
    """Construct the SDK's synchronous client with HTTPX defaults."""
    return httpx.Client(**_client_transport_options(httpx.HTTPTransport, None, {}))


def create_async_http_client(
    *,
    keepalive: TCPKeepAlive | None = None,
    transport_options: dict[str, Any] | None = None,
    **client_options: Any,
) -> httpx.AsyncClient:
    """Construct an async client, applying TLS and pool settings to every route."""
    return httpx.AsyncClient(
        **client_options,
        **_client_transport_options(
            httpx.AsyncHTTPTransport, keepalive, transport_options or {}
        ),
    )
