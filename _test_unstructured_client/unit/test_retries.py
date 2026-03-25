"""Tests for retry logic, specifically covering RemoteProtocolError retry behavior."""

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


class TestRemoteProtocolErrorRetry:
    """Test that RemoteProtocolError (e.g. 'Server disconnected without sending a response')
    is retried when retry_connection_errors=True."""

    def test_remote_protocol_error_retried_when_enabled(self):
        """RemoteProtocolError should be retried and succeed on subsequent attempt."""
        retries_config = _make_retries(retry_connection_errors=True)

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200

        call_count = 0

        def func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise httpx.RemoteProtocolError(
                    "Server disconnected without sending a response."
                )
            return mock_response

        result = retry(func, retries_config)
        assert result.status_code == 200
        assert call_count == 2

    def test_remote_protocol_error_not_retried_when_disabled(self):
        """RemoteProtocolError should raise PermanentError when retry_connection_errors=False."""
        retries_config = _make_retries(retry_connection_errors=False)

        def func():
            raise httpx.RemoteProtocolError(
                "Server disconnected without sending a response."
            )

        with pytest.raises(httpx.RemoteProtocolError):
            retry(func, retries_config)

    def test_connect_error_still_retried(self):
        """Existing ConnectError retry behavior should be preserved."""
        retries_config = _make_retries(retry_connection_errors=True)

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200

        call_count = 0

        def func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise httpx.ConnectError("Connection refused")
            return mock_response

        result = retry(func, retries_config)
        assert result.status_code == 200
        assert call_count == 2


class TestRemoteProtocolErrorRetryAsync:
    """Async versions of the RemoteProtocolError retry tests."""

    def test_remote_protocol_error_retried_async(self):
        """Async: RemoteProtocolError should be retried when retry_connection_errors=True."""
        retries_config = _make_retries(retry_connection_errors=True)

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200

        call_count = 0

        async def func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise httpx.RemoteProtocolError(
                    "Server disconnected without sending a response."
                )
            return mock_response

        result = asyncio.run(retry_async(func, retries_config))
        assert result.status_code == 200
        assert call_count == 2

    def test_remote_protocol_error_not_retried_async_when_disabled(self):
        """Async: RemoteProtocolError should not be retried when retry_connection_errors=False."""
        retries_config = _make_retries(retry_connection_errors=False)

        async def func():
            raise httpx.RemoteProtocolError(
                "Server disconnected without sending a response."
            )

        with pytest.raises(httpx.RemoteProtocolError):
            asyncio.run(retry_async(func, retries_config))
