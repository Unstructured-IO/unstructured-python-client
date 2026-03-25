"""Tests for retry logic covering all TransportError subclasses."""

import asyncio
from unittest.mock import MagicMock

import httpx
import pytest

from unstructured_client.utils.retries import (
    BackoffStrategy,
    PermanentError,
    Retries,
    RetryConfig,
    retry,
    retry_async,
)


def _make_retries(retry_connection_errors: bool) -> Retries:
    return Retries(
        config=RetryConfig(
            strategy="backoff",
            backoff=BackoffStrategy(
                initial_interval=100,
                max_interval=200,
                exponent=1.5,
                max_elapsed_time=5000,
            ),
            retry_connection_errors=retry_connection_errors,
        ),
        status_codes=[],
    )


# All TransportError subclasses that should be retried
TRANSPORT_ERRORS = [
    (httpx.ConnectError, "Connection refused"),
    (httpx.RemoteProtocolError, "Server disconnected without sending a response."),
    (httpx.ReadError, ""),
    (httpx.WriteError, ""),
    (httpx.ConnectTimeout, "Timed out"),
    (httpx.ReadTimeout, "Timed out"),
]


class TestTransportErrorRetry:
    """All httpx.TransportError subclasses should be retried when retry_connection_errors=True."""

    @pytest.mark.parametrize("exc_class,msg", TRANSPORT_ERRORS)
    def test_transport_error_retried_when_enabled(self, exc_class, msg):
        retries_config = _make_retries(retry_connection_errors=True)

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200

        call_count = 0

        def func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise exc_class(msg)
            return mock_response

        result = retry(func, retries_config)
        assert result.status_code == 200
        assert call_count == 2

    @pytest.mark.parametrize("exc_class,msg", TRANSPORT_ERRORS)
    def test_transport_error_not_retried_when_disabled(self, exc_class, msg):
        retries_config = _make_retries(retry_connection_errors=False)

        def func():
            raise exc_class(msg)

        with pytest.raises(exc_class):
            retry(func, retries_config)


class TestTransportErrorRetryAsync:
    """Async: All httpx.TransportError subclasses should be retried."""

    @pytest.mark.parametrize("exc_class,msg", TRANSPORT_ERRORS)
    def test_transport_error_retried_async(self, exc_class, msg):
        retries_config = _make_retries(retry_connection_errors=True)

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200

        call_count = 0

        async def func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise exc_class(msg)
            return mock_response

        result = asyncio.run(retry_async(func, retries_config))
        assert result.status_code == 200
        assert call_count == 2

    @pytest.mark.parametrize("exc_class,msg", TRANSPORT_ERRORS)
    def test_transport_error_not_retried_async_when_disabled(self, exc_class, msg):
        retries_config = _make_retries(retry_connection_errors=False)

        async def func():
            raise exc_class(msg)

        with pytest.raises(exc_class):
            asyncio.run(retry_async(func, retries_config))
