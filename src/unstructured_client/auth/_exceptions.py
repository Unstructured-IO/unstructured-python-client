"""Exceptions raised by the token-exchange auth callables."""

from __future__ import annotations


class TokenExchangeError(Exception):
    """Base error for failures during `/auth/token-exchange` calls."""


class TokenExchangeDisabledError(TokenExchangeError):
    """Raised when account-service responds with `token_exchange_enabled=False`.

    The user explicitly opted into `ClientCredentials` / `LegacyKeyExchange`, so
    the server not supporting exchange is treated as a misconfiguration rather
    than silently returning a null token.
    """


class InvalidCredentialError(TokenExchangeError):
    """Raised when account-service returns 401 Unauthorized.

    The supplied client secret or legacy API key was not recognized. Retrying
    will not help, so the exchange callable raises immediately.
    """
