"""Shared helpers for exercising token-exchange auth callables.

The mock transports here let tests script a sequence of responses / exceptions
for the ``POST /auth/token-exchange`` endpoint without standing up a real
account-service.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Iterable, List, Optional, Union

import httpx


ResponseStep = Union[httpx.Response, Exception, Callable[[httpx.Request], httpx.Response]]


class ScriptedTransport(httpx.MockTransport):
    """A MockTransport that walks through a scripted sequence of responses.

    Each element can be an :class:`httpx.Response`, an ``Exception`` instance
    (raised instead of returned), or a callable that accepts the request and
    returns a response. Tests can inspect :attr:`requests` to assert how many
    exchanges took place and what bodies were sent.
    """

    def __init__(self, steps: Iterable[ResponseStep]) -> None:
        self._steps: List[ResponseStep] = list(steps)
        self.requests: List[httpx.Request] = []
        super().__init__(self._handler)

    def _handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if not self._steps:
            raise AssertionError(
                "ScriptedTransport exhausted; unexpected extra request to "
                f"{request.url}",
            )
        step = self._steps.pop(0)
        if isinstance(step, Exception):
            raise step
        if callable(step):
            return step(request)
        return step


class AsyncScriptedTransport(httpx.MockTransport):
    """Async counterpart to :class:`ScriptedTransport`."""

    def __init__(self, steps: Iterable[ResponseStep]) -> None:
        self._steps: List[ResponseStep] = list(steps)
        self.requests: List[httpx.Request] = []

        async def _handler(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            if not self._steps:
                raise AssertionError(
                    "AsyncScriptedTransport exhausted; unexpected extra "
                    f"request to {request.url}",
                )
            step = self._steps.pop(0)
            if isinstance(step, Exception):
                raise step
            if callable(step):
                return step(request)
            return step

        super().__init__(_handler)


def exchange_response(
    access_token: Optional[str] = "jwt-1",
    *,
    expires_in: int = 900,
    token_exchange_enabled: bool = True,
    token_type: str = "bearer",
    status_code: int = 200,
    extra: Optional[dict] = None,
) -> httpx.Response:
    """Build a canned ``/auth/token-exchange`` response body."""
    body: dict[str, Any] = {
        "access_token": access_token,
        "token_type": token_type,
        "expires_in": expires_in,
        "token_exchange_enabled": token_exchange_enabled,
    }
    if extra:
        body.update(extra)
    return httpx.Response(status_code, json=body)


def body_of(request: httpx.Request) -> dict:
    """Decode the JSON body from an outgoing exchange request."""
    return json.loads(request.content.decode("utf-8"))
