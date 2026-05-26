import asyncio
import time as time_module
from unittest.mock import MagicMock

import httpx
import pytest

from unstructured_client.utils import retries as retries_module
from unstructured_client.utils.retries import (
    BackoffStrategy,
    PermanentError,
    Retries,
    RetryConfig,
    TemporaryError,
    retry,
    retry_async,
)


class FakeClock:
    def __init__(self):
        self.now_ms = 0

    def time(self) -> float:
        return self.now_ms / 1000.0

    def advance(self, milliseconds: int) -> None:
        self.now_ms += int(milliseconds)


@pytest.fixture
def fake_clock(monkeypatch):
    clock = FakeClock()

    def fake_time():
        return clock.time()

    def fake_sync_sleep(seconds):
        clock.advance(int(seconds * 1000))

    async def fake_async_sleep(seconds):
        clock.advance(int(seconds * 1000))

    monkeypatch.setattr(retries_module.time, "time", fake_time)
    monkeypatch.setattr(retries_module.time, "sleep", fake_sync_sleep)
    monkeypatch.setattr(retries_module.asyncio, "sleep", fake_async_sleep)
    monkeypatch.setattr(retries_module.random, "uniform", lambda a, b: 0.0)
    return clock


def _retries(
    *,
    initial_interval: int = 100,
    max_interval: int = 200,
    exponent: float = 1.5,
    max_elapsed_time: int = 5_000,
    min_attempts: int = 0,
    absolute_max_elapsed_time_ms=None,
    retry_connection_errors: bool = True,
    status_codes=None,
) -> Retries:
    return Retries(
        config=RetryConfig(
            strategy="backoff",
            backoff=BackoffStrategy(
                initial_interval=initial_interval,
                max_interval=max_interval,
                exponent=exponent,
                max_elapsed_time=max_elapsed_time,
                min_attempts=min_attempts,
                absolute_max_elapsed_time_ms=absolute_max_elapsed_time_ms,
            ),
            retry_connection_errors=retry_connection_errors,
        ),
        status_codes=status_codes or [],
    )


def _make_ok_response(status_code: int = 200) -> httpx.Response:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    return resp


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


TRANSPORT_ERRORS = [
    (httpx.ConnectError, "Connection refused"),
    (httpx.RemoteProtocolError, "Server disconnected without sending a response."),
    (httpx.ReadError, ""),
    (httpx.WriteError, ""),
    (httpx.ConnectTimeout, "Timed out"),
    (httpx.ReadTimeout, "Timed out"),
]


class TestTransportErrorRetry:

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


class TestBackoffStrategyValidation:
    def test_t12_negative_min_attempts_rejected(self):
        with pytest.raises(ValueError, match="min_attempts must be >= 0"):
            BackoffStrategy(
                initial_interval=100,
                max_interval=200,
                exponent=1.5,
                max_elapsed_time=5_000,
                min_attempts=-1,
            )

    def test_t13_zero_absolute_max_rejected(self):
        with pytest.raises(ValueError, match="absolute_max_elapsed_time_ms must be > 0"):
            BackoffStrategy(
                initial_interval=100,
                max_interval=200,
                exponent=1.5,
                max_elapsed_time=5_000,
                absolute_max_elapsed_time_ms=0,
            )

    def test_t14_absolute_max_below_soft_max_rejected(self):
        with pytest.raises(
            ValueError,
            match="absolute_max_elapsed_time_ms must be >= max_elapsed_time",
        ):
            BackoffStrategy(
                initial_interval=100,
                max_interval=200,
                exponent=1.5,
                max_elapsed_time=10_000,
                absolute_max_elapsed_time_ms=5_000,
            )

    def test_min_attempts_zero_accepted(self):
        BackoffStrategy(
            initial_interval=100,
            max_interval=200,
            exponent=1.5,
            max_elapsed_time=5_000,
            min_attempts=0,
        )

    def test_absolute_max_equal_to_soft_max_accepted(self):
        BackoffStrategy(
            initial_interval=100,
            max_interval=200,
            exponent=1.5,
            max_elapsed_time=5_000,
            absolute_max_elapsed_time_ms=5_000,
        )


class TestBackwardCompat:
    def test_t1_no_failures_sync(self, fake_clock):
        retries_config = _retries()
        call_count = 0

        def func():
            nonlocal call_count
            call_count += 1
            return _make_ok_response()

        result = retry(func, retries_config)
        assert result.status_code == 200
        assert call_count == 1

    def test_t1_no_failures_async(self, fake_clock):
        retries_config = _retries()
        call_count = 0

        async def func():
            nonlocal call_count
            call_count += 1
            return _make_ok_response()

        result = asyncio.run(retry_async(func, retries_config))
        assert result.status_code == 200
        assert call_count == 1

    def test_t2_one_transient_then_success_sync(self, fake_clock):
        retries_config = _retries()
        call_count = 0

        def func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise httpx.ConnectError("transient")
            return _make_ok_response()

        result = retry(func, retries_config)
        assert result.status_code == 200
        assert call_count == 2

    def test_t2_one_transient_then_success_async(self, fake_clock):
        retries_config = _retries()
        call_count = 0

        async def func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise httpx.ConnectError("transient")
            return _make_ok_response()

        result = asyncio.run(retry_async(func, retries_config))
        assert result.status_code == 200
        assert call_count == 2


class TestSoftCapFloor:
    def test_t3_slow_first_attempt_then_success_sync(self, fake_clock):
        retries_config = _retries(
            max_elapsed_time=5_000,
            min_attempts=2,
        )
        call_count = 0

        def func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                fake_clock.advance(6_000)  # 6s
                raise httpx.ReadTimeout("slow")
            return _make_ok_response()

        result = retry(func, retries_config)
        assert result.status_code == 200
        assert call_count == 2

    def test_t3_slow_first_attempt_then_success_async(self, fake_clock):
        retries_config = _retries(
            max_elapsed_time=5_000,
            min_attempts=2,
        )
        call_count = 0

        async def func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                fake_clock.advance(6_000)
                raise httpx.ReadTimeout("slow")
            return _make_ok_response()

        result = asyncio.run(retry_async(func, retries_config))
        assert result.status_code == 200
        assert call_count == 2

    def test_t3_baseline_pre_fix_behavior(self, fake_clock):
        retries_config = _retries(
            max_elapsed_time=5_000,
            min_attempts=0,
        )
        call_count = 0

        def func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                fake_clock.advance(6_000)
                raise httpx.ReadTimeout("slow")
            return _make_ok_response()

        # Without the floor, soft cap fires on attempt 1's failure and
        # the loop raises the wrapped ReadTimeout.
        with pytest.raises(httpx.ReadTimeout):
            retry(func, retries_config)
        assert call_count == 1


class TestFloorIsNotCeiling:
    def test_t4_floor_does_not_cap_attempts_sync(self, fake_clock):
        retries_config = _retries(
            initial_interval=100,
            max_interval=200,
            exponent=1.5,
            max_elapsed_time=60_000,  # generous budget
            min_attempts=2,
        )
        call_count = 0

        def func():
            nonlocal call_count
            call_count += 1
            if call_count <= 5:
                raise httpx.ConnectError("transient")
            return _make_ok_response()

        result = retry(func, retries_config)
        assert result.status_code == 200
        assert call_count == 6

    def test_t5_floor_then_soft_cap_sync(self, fake_clock):
        retries_config = _retries(
            initial_interval=100,
            max_interval=200,
            exponent=1.5,
            max_elapsed_time=10_000,
            min_attempts=2,
        )
        call_count = 0

        def func():
            nonlocal call_count
            call_count += 1
            # sleep advances the fake clock.
            raise httpx.ConnectError("transient")

        with pytest.raises(httpx.ConnectError):
            retry(func, retries_config)
        assert call_count >= 3


class TestHardCap:
    def test_t6_hard_cap_overrides_floor_sync(self, fake_clock):
        retries_config = _retries(
            max_elapsed_time=5_000,
            min_attempts=2,
            absolute_max_elapsed_time_ms=10_000,
        )
        call_count = 0

        def func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                fake_clock.advance(11_000)  # 11s > 10s hard cap
                raise httpx.ReadTimeout("slow")
            return _make_ok_response()

        with pytest.raises(httpx.ReadTimeout):
            retry(func, retries_config)
        assert call_count == 1

    def test_t6_hard_cap_overrides_floor_async(self, fake_clock):
        retries_config = _retries(
            max_elapsed_time=5_000,
            min_attempts=2,
            absolute_max_elapsed_time_ms=10_000,
        )
        call_count = 0

        async def func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                fake_clock.advance(11_000)
                raise httpx.ReadTimeout("slow")
            return _make_ok_response()

        with pytest.raises(httpx.ReadTimeout):
            asyncio.run(retry_async(func, retries_config))
        assert call_count == 1

    def test_t7_sleep_truncation_prevents_doomed_retry_sync(self, fake_clock):
        # Sleep starts at 100ms * 1.5^0 = 100ms (no jitter in tests),
        # but we want to assert the sleep+elapsed > hard_cap path
        # fires. Use larger initial_interval to make the calculation
        # land deterministically.
        retries_config = _retries(
            initial_interval=200,  # 200ms initial
            max_interval=1_000,
            exponent=2.0,
            max_elapsed_time=5_000,
            min_attempts=2,  # floor is unsatisfied; only hard cap can cut
            absolute_max_elapsed_time_ms=10_000,
        )
        call_count = 0

        def func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # attempt 1 lasts 9.95s -> elapsed = 9.95s, sleep would be
                # 200ms -> projected = 10.15s >= hard cap 10s -> raise.
                fake_clock.advance(9_950)
                raise httpx.ReadTimeout("slow")
            return _make_ok_response()

        with pytest.raises(httpx.ReadTimeout):
            retry(func, retries_config)
        assert call_count == 1


class TestTemporaryErrorEarlyReturn:
    def test_t8_soft_cap_5xx_returns_last_response_sync(self, fake_clock):
        retries_config = _retries(
            initial_interval=100,
            max_interval=200,
            exponent=1.5,
            max_elapsed_time=500,
            min_attempts=0,
            status_codes=["5xx"],
        )
        bad_response = _make_ok_response(status_code=503)
        call_count = 0

        def func():
            nonlocal call_count
            call_count += 1
            return bad_response

        result = retry(func, retries_config)
        assert result.status_code == 503
        assert call_count >= 1

    def test_t9_floor_then_soft_cap_5xx_returns_last_response_sync(self, fake_clock):
        retries_config = _retries(
            initial_interval=100,
            max_interval=200,
            exponent=1.5,
            max_elapsed_time=1_000,
            min_attempts=2,
            status_codes=["5xx"],
        )
        bad_response = _make_ok_response(status_code=503)
        call_count = 0

        def func():
            nonlocal call_count
            call_count += 1
            return bad_response

        result = retry(func, retries_config)
        assert result.status_code == 503
        assert call_count >= 3

    def test_t10_hard_cap_5xx_returns_last_response_sync(self, fake_clock):
        retries_config = _retries(
            initial_interval=100,
            max_interval=200,
            exponent=1.5,
            max_elapsed_time=5_000,
            min_attempts=2,
            absolute_max_elapsed_time_ms=10_000,
            status_codes=["5xx"],
        )
        bad_response = _make_ok_response(status_code=503)
        call_count = 0

        def func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                fake_clock.advance(11_000)  # past hard cap
            return bad_response

        result = retry(func, retries_config)
        assert result.status_code == 503
        assert call_count == 1


class TestPermanentErrorShortCircuit:

    def test_t11_permanent_error_one_attempt_sync(self, fake_clock):
        retries_config = _retries(min_attempts=10)
        call_count = 0

        def func():
            nonlocal call_count
            call_count += 1
            raise ValueError("permanent")

        with pytest.raises(ValueError, match="permanent"):
            retry(func, retries_config)
        assert call_count == 1

    def test_t11_permanent_error_one_attempt_async(self, fake_clock):
        retries_config = _retries(min_attempts=10)
        call_count = 0

        async def func():
            nonlocal call_count
            call_count += 1
            raise ValueError("permanent")

        with pytest.raises(ValueError, match="permanent"):
            asyncio.run(retry_async(func, retries_config))
        assert call_count == 1
