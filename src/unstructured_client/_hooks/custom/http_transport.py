"""Single factory for every HTTP client the SDK constructs.

TCP keepalive applies to direct connections; environment proxy routing is preserved.
"""

import logging
import os
import socket
from dataclasses import dataclass
from typing import Any

import httpx

from .common import UNSTRUCTURED_CLIENT_LOGGER_NAME

logger = logging.getLogger(UNSTRUCTURED_CLIENT_LOGGER_NAME)

try:
    from httpx._utils import get_environment_proxies
except ImportError:
    get_environment_proxies = None  # type: ignore[assignment]
    logger.debug("TCP keepalive is unavailable with this httpx version")

DEFAULT_IDLE = 60
DEFAULT_INTERVAL = 30
DEFAULT_COUNT = 5
MAX_IDLE = 32767
MAX_INTERVAL = 32767
MAX_COUNT = 127


def _bounded_int(name: str, default: int, maximum: int) -> int:
    value = os.getenv(name, str(default))
    try:
        parsed = int(value)
        if 1 <= parsed <= maximum:
            return parsed
    except ValueError:
        pass
    logger.warning("Invalid %s=%r; using default %d", name, value, default)
    return default


@dataclass(frozen=True)
class TCPKeepAlive:
    """Resolved TCP probe settings, in seconds and number of probes."""

    enabled: bool
    idle: int = DEFAULT_IDLE
    interval: int = DEFAULT_INTERVAL
    count: int = DEFAULT_COUNT

    def describe(self) -> str:
        """Summarize the resolved probe settings for logging."""
        if not self.enabled:
            return "off"
        return f"idle={self.idle}s interval={self.interval}s count={self.count}"

    def socket_options(self) -> list[tuple[int, int, int]]:
        """Use only the TCP options available on the current platform."""
        if not self.enabled:
            return []
        options = [(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)]
        idle_option = getattr(socket, "TCP_KEEPIDLE", None) or getattr(socket, "TCP_KEEPALIVE", None)
        for option, value in (
            (idle_option, self.idle),
            (getattr(socket, "TCP_KEEPINTVL", None), self.interval),
            (getattr(socket, "TCP_KEEPCNT", None), self.count),
        ):
            if option is not None:
                options.append((socket.IPPROTO_TCP, option, value))
        return options


def resolve_tcp_keepalive() -> TCPKeepAlive:
    """Read keepalive settings, falling back on values outside the supported bounds."""
    prefix = "UNSTRUCTURED_CLIENT_TCP_KEEPALIVE"
    if os.getenv(prefix, "1").strip().lower() in ("0", "false"):
        return TCPKeepAlive(enabled=False)
    return TCPKeepAlive(
        enabled=True,
        idle=_bounded_int(prefix + "_IDLE", DEFAULT_IDLE, MAX_IDLE),
        interval=_bounded_int(prefix + "_INTERVAL", DEFAULT_INTERVAL, MAX_INTERVAL),
        count=_bounded_int(prefix + "_COUNT", DEFAULT_COUNT, MAX_COUNT),
    )


def _client_transport_options(
    transport_type: Any,
    transport_options: dict[str, Any],
) -> dict[str, Any]:
    if get_environment_proxies is None:
        return transport_options
    options = dict(transport_options, socket_options=resolve_tcp_keepalive().socket_options())
    # HTTPX disables automatic environment proxy discovery with a custom transport.
    # Reuse its URL patterns, including None mounts for NO_PROXY exclusions.
    # Proxied connections are not given keepalive.
    mounts = {
        pattern: transport_type(proxy=proxy, **transport_options) if proxy else None
        for pattern, proxy in get_environment_proxies().items()
    }
    return {"transport": transport_type(**options), "mounts": mounts}


def create_http_client() -> httpx.Client:
    """Construct the SDK's synchronous client with HTTPX defaults."""
    return httpx.Client(**_client_transport_options(httpx.HTTPTransport, {}))


def create_async_http_client(
    *,
    timeout: Any = None,
    limits: httpx.Limits | None = None,
    verify: Any = True,
    cert: Any = None,
) -> httpx.AsyncClient:
    """Construct an async client, applying TLS and pool settings to every route.

    A None timeout leaves HTTPX's default timeout in place.
    """
    transport_options: dict[str, Any] = {}
    if limits is not None:
        transport_options["limits"] = limits
    if verify is not True:
        transport_options["verify"] = verify
    if cert is not None:
        transport_options["cert"] = cert
    client_options = {} if timeout is None else {"timeout": timeout}
    return httpx.AsyncClient(
        **client_options,
        **_client_transport_options(httpx.AsyncHTTPTransport, transport_options),
    )
