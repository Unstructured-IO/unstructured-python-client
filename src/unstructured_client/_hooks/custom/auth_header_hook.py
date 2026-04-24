"""Before-request hook that promotes exchanged JWTs to ``Authorization: Bearer``.

Speakeasy's generated ``Security`` model places ``api_key_auth`` in the
``unstructured-api-key`` header. When the user supplies a token-exchange
callable (``ClientCredentials`` or ``LegacyKeyExchange``) the value is a JWT
and must be sent as ``Authorization: Bearer <jwt>`` so the service-side
``utic-jwt-auth`` validator picks it up (see ``core-product`` auth_context
and ``platform-api`` public_api/dependencies).

Plain-string ``api_key_auth`` is untouched.
"""

from __future__ import annotations

from typing import Union

import httpx

from unstructured_client._hooks.types import BeforeRequestContext, BeforeRequestHook


class AuthHeaderBeforeRequestHook(BeforeRequestHook):
    """Rewrite ``unstructured-api-key`` -> ``Authorization: Bearer`` when the
    active security source is a known token-exchange callable."""

    def before_request(
        self, hook_ctx: BeforeRequestContext, request: httpx.Request
    ) -> Union[httpx.Request, Exception]:
        if not self._is_exchange_callable(hook_ctx.security_source):
            return request

        token = request.headers.get("unstructured-api-key")
        if not token:
            return request

        del request.headers["unstructured-api-key"]
        request.headers["Authorization"] = f"Bearer {token}"
        return request

    @staticmethod
    def _is_exchange_callable(security_source: object) -> bool:
        """Return True when ``security_source`` was built from one of our
        token-exchange callables.

        The SDK wraps a user-supplied callable into an internal factory and
        attaches ``__wrapped_callable__`` to it (see ``sdk.py``). We import
        the base class lazily to avoid any cycle at module load.
        """
        from unstructured_client.auth._base import _ExchangeCallableBase

        if security_source is None:
            return False

        candidate = getattr(security_source, "__wrapped_callable__", security_source)
        return isinstance(candidate, _ExchangeCallableBase)
