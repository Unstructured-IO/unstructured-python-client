from __future__ import annotations

import asyncio
import io
import logging
import threading
from collections import Counter
from functools import partial
from unittest.mock import MagicMock, patch

import httpx
import pytest

from unstructured_client._hooks.custom.split_pdf_hook import (
    DEFAULT_CONCURRENCY_LEVEL,
    SplitPdfHook,
)
from unstructured_client._hooks.sdkhooks import SDKHooks
from unstructured_client.basesdk import BaseSDK
from unstructured_client.sdkconfiguration import SDKConfiguration


def _httpx_json_response(payload: list[dict], status_code: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        json=payload,
        request=httpx.Request("POST", "http://localhost:8888/general/v0/general"),
    )


def _make_sdk_hook_context():
    hook_ctx = MagicMock()
    hook_ctx.config = MagicMock()
    hook_ctx.base_url = "http://localhost:8888"
    hook_ctx.operation_id = "partition"
    hook_ctx.oauth2_scopes = None
    hook_ctx.security_source = None
    return hook_ctx


def _make_base_sdk_with_hooks(hooks: SDKHooks, async_client: object) -> BaseSDK:
    config = SDKConfiguration(
        client=None,
        client_supplied=False,
        async_client=async_client,  # type: ignore[arg-type]
        async_client_supplied=True,
        debug_logger=logging.getLogger("test"),
    )
    config.__dict__["_hooks"] = hooks
    return BaseSDK(config)


def _make_split_hooks(split_hook: SplitPdfHook) -> SDKHooks:
    hooks = SDKHooks()
    hooks.before_request_hooks = [split_hook]
    hooks.after_success_hooks = [split_hook]
    hooks.after_error_hooks = [split_hook]
    return hooks


def _prepare_sdk_split_operation(
    split_hook: SplitPdfHook,
    *,
    operation_id: str,
    coroutines: list,
    allow_failed: bool = False,
    concurrency_level: int = DEFAULT_CONCURRENCY_LEVEL,
    timeout_seconds: float | None = 12.0,
) -> None:
    split_hook.coroutines_to_execute[operation_id] = coroutines
    split_hook.pending_operation_ids[operation_id] = operation_id
    split_hook.allow_failed[operation_id] = allow_failed
    split_hook.cache_tmp_data_feature[operation_id] = False
    split_hook.concurrency_level[operation_id] = concurrency_level
    split_hook.operation_timeouts[operation_id] = timeout_seconds

    def _prepared_split_request(hook_ctx, request):
        del hook_ctx, request
        return httpx.Request(
            "GET",
            "http://localhost:8888/general/docs",
            headers={"operation_id": operation_id},
            extensions={"split_pdf_operation_id": operation_id},
        )

    split_hook.before_request = _prepared_split_request  # type: ignore[method-assign]


def _make_dummy_request_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(status_code=200, request=request)
        )
    )


def _make_sdk_split_task(
    sdk: BaseSDK,
    *,
    error_status_codes: list | None = None,
) -> asyncio.Task[httpx.Response]:
    return asyncio.create_task(
        sdk.do_request_async(
            _make_sdk_hook_context(),
            httpx.Request("POST", "http://localhost:8888/general/v0/general"),
            error_status_codes=error_status_codes or [],
        )
    )


@pytest.mark.asyncio
async def test_partition_async_split_collects_chunks_in_order_without_executor():
    operation_id = "integration-happy"
    split_hook = SplitPdfHook()
    active_chunks = 0
    max_active_chunks = 0
    active_lock = asyncio.Lock()

    async def _chunk_transport(request: httpx.Request) -> httpx.Response:
        nonlocal active_chunks, max_active_chunks
        async with active_lock:
            active_chunks += 1
            max_active_chunks = max(max_active_chunks, active_chunks)
        try:
            if request.url.path.endswith("/1"):
                await asyncio.sleep(0.02)
                payload = [{"page_number": 1}]
            else:
                payload = [{"page_number": 3}]
            return httpx.Response(status_code=200, json=payload, request=request)
        finally:
            async with active_lock:
                active_chunks -= 1

    original_async_client = httpx.AsyncClient

    def _chunk_client_factory(*args, **kwargs):
        return original_async_client(
            transport=httpx.MockTransport(_chunk_transport),
            timeout=kwargs.get("timeout"),
        )

    coroutines = [
        partial(
            split_hook.call_api_partial,
            _operation_id=operation_id,
            chunk_index=1,
            page_number=1,
            pdf_chunk_request=httpx.Request("POST", "http://chunks.local/chunk/1"),
            pdf_chunk_file=io.BytesIO(b"chunk-1"),
            retry_config=None,
            cache_tmp_data_feature=False,
            temp_dir_path=None,
        ),
        partial(
            split_hook.call_api_partial,
            _operation_id=operation_id,
            chunk_index=2,
            page_number=3,
            pdf_chunk_request=httpx.Request("POST", "http://chunks.local/chunk/2"),
            pdf_chunk_file=io.BytesIO(b"chunk-2"),
            retry_config=None,
            cache_tmp_data_feature=False,
            temp_dir_path=None,
        ),
    ]
    _prepare_sdk_split_operation(
        split_hook,
        operation_id=operation_id,
        coroutines=coroutines,
        concurrency_level=2,
    )

    async with _make_dummy_request_client() as top_level_client:
        sdk = _make_base_sdk_with_hooks(_make_split_hooks(split_hook), top_level_client)
        with patch(
            "unstructured_client._hooks.custom.split_pdf_hook.httpx.AsyncClient",
            side_effect=_chunk_client_factory,
        ):
            response = await sdk.do_request_async(
                _make_sdk_hook_context(),
                httpx.Request("POST", "http://localhost:8888/general/v0/general"),
                error_status_codes=[],
            )

    assert response.json() == [{"page_number": 1}, {"page_number": 3}]
    assert max_active_chunks == 2
    assert operation_id not in split_hook.executors
    assert operation_id not in split_hook.coroutines_to_execute


@pytest.mark.asyncio
async def test_partition_async_cancellation_cleans_split_state_and_tempdir():
    operation_id = "integration-cancel"
    split_hook = SplitPdfHook()
    started = asyncio.Event()
    cancelled_counter = Counter()
    tempdir = MagicMock()
    split_hook.tempdirs[operation_id] = tempdir

    async def _hanging_chunk(
        async_client: httpx.AsyncClient,
        limiter: asyncio.Semaphore,
    ) -> httpx.Response:
        del async_client, limiter
        try:
            started.set()
            await asyncio.Event().wait()
            return _httpx_json_response([])
        except asyncio.CancelledError:
            cancelled_counter.update(["cancelled"])
            raise

    _prepare_sdk_split_operation(
        split_hook,
        operation_id=operation_id,
        coroutines=[partial(_hanging_chunk)],
        timeout_seconds=60.0,
    )

    async with _make_dummy_request_client() as top_level_client:
        sdk = _make_base_sdk_with_hooks(_make_split_hooks(split_hook), top_level_client)
        task = _make_sdk_split_task(sdk)
        await started.wait()
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

    assert cancelled_counter["cancelled"] == 1
    assert operation_id not in split_hook.coroutines_to_execute
    assert operation_id not in split_hook.pending_operation_ids
    assert operation_id not in split_hook.tempdirs
    tempdir.cleanup.assert_called_once()


@pytest.mark.asyncio
async def test_partition_async_strict_failure_drains_sibling_chunks_before_close():
    operation_id = "integration-strict-failure"
    split_hook = SplitPdfHook()
    sibling_started = asyncio.Event()
    sibling_cancelled = asyncio.Event()
    sibling_finished = asyncio.Event()

    async def _chunk_transport(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/failure"):
            return httpx.Response(status_code=400, content=b"bad chunk", request=request)
        sibling_started.set()
        try:
            await asyncio.Event().wait()
            return httpx.Response(status_code=200, json=[], request=request)
        except asyncio.CancelledError:
            sibling_cancelled.set()
            raise
        finally:
            sibling_finished.set()

    original_async_client = httpx.AsyncClient

    def _chunk_client_factory(*args, **kwargs):
        return original_async_client(
            transport=httpx.MockTransport(_chunk_transport),
            timeout=kwargs.get("timeout"),
        )

    coroutines = [
        partial(
            split_hook.call_api_partial,
            _operation_id=operation_id,
            chunk_index=1,
            page_number=1,
            pdf_chunk_request=httpx.Request("POST", "http://chunks.local/chunk/wait"),
            pdf_chunk_file=io.BytesIO(b"chunk-1"),
            retry_config=None,
            cache_tmp_data_feature=False,
            temp_dir_path=None,
        ),
        partial(
            split_hook.call_api_partial,
            _operation_id=operation_id,
            chunk_index=2,
            page_number=3,
            pdf_chunk_request=httpx.Request("POST", "http://chunks.local/chunk/failure"),
            pdf_chunk_file=io.BytesIO(b"chunk-2"),
            retry_config=None,
            cache_tmp_data_feature=False,
            temp_dir_path=None,
        ),
    ]
    _prepare_sdk_split_operation(
        split_hook,
        operation_id=operation_id,
        coroutines=coroutines,
        concurrency_level=2,
    )

    async with _make_dummy_request_client() as top_level_client:
        sdk = _make_base_sdk_with_hooks(_make_split_hooks(split_hook), top_level_client)
        with patch(
            "unstructured_client._hooks.custom.split_pdf_hook.httpx.AsyncClient",
            side_effect=_chunk_client_factory,
        ):
            response = await sdk.do_request_async(
                _make_sdk_hook_context(),
                httpx.Request("POST", "http://localhost:8888/general/v0/general"),
                error_status_codes=[],
            )

    assert response.status_code == 400
    assert response.content == b"bad chunk"
    assert sibling_started.is_set()
    assert sibling_cancelled.is_set()
    assert sibling_finished.is_set()
    assert "transport_exception" not in response.extensions
    assert operation_id not in split_hook.coroutines_to_execute


@pytest.mark.asyncio
async def test_async_hook_chain_runs_sync_fallback_without_blocking_loop():
    loop_progress_released_hook = threading.Event()
    sync_hook_started = threading.Event()
    sync_hook_was_released_by_loop = []
    calls: list[str] = []

    class AsyncSuccessHook:
        async def after_success_async(self, hook_ctx, response):
            del hook_ctx
            calls.append("async")
            response.headers["X-Async-Hook"] = "called"
            return response

        def after_success(self, hook_ctx, response):  # pragma: no cover - dispatch guard
            raise AssertionError("async hook should be awaited")

    class SyncSuccessHook:
        def after_success(self, hook_ctx, response):
            del hook_ctx
            calls.append("sync")
            sync_hook_started.set()
            sync_hook_was_released_by_loop.append(loop_progress_released_hook.wait(timeout=0.5))
            response.headers["X-Sync-Hook"] = "called"
            return response

    hooks = SDKHooks()
    hooks.before_request_hooks = []
    hooks.after_error_hooks = []
    hooks.after_success_hooks = [AsyncSuccessHook(), SyncSuccessHook()]  # type: ignore[list-item]

    async def _release_sync_hook_from_loop() -> None:
        while not sync_hook_started.is_set():
            await asyncio.sleep(0)
        loop_progress_released_hook.set()

    async with _make_dummy_request_client() as top_level_client:
        sdk = _make_base_sdk_with_hooks(hooks, top_level_client)
        response, _ = await asyncio.gather(
            sdk.do_request_async(
                _make_sdk_hook_context(),
                httpx.Request("POST", "http://localhost:8888/general/v0/general"),
                error_status_codes=[],
            ),
            _release_sync_hook_from_loop(),
        )

    assert calls == ["async", "sync"]
    assert response.headers["X-Async-Hook"] == "called"
    assert response.headers["X-Sync-Hook"] == "called"
    assert sync_hook_was_released_by_loop == [True]


@pytest.mark.asyncio
async def test_partition_async_reassembly_does_not_block_event_loop():
    operation_id = "integration-offload"
    split_hook = SplitPdfHook()
    reassembly_started = threading.Event()
    reassembly_released = threading.Event()
    reassembly_was_released_by_loop = []

    async def _successful_chunk(
        async_client: httpx.AsyncClient,
        limiter: asyncio.Semaphore,
    ) -> httpx.Response:
        del async_client, limiter
        return _httpx_json_response([{"page_number": 1}])

    _prepare_sdk_split_operation(
        split_hook,
        operation_id=operation_id,
        coroutines=[partial(_successful_chunk)],
    )

    def _slow_reassembly(operation_id_arg, task_responses, *, started_at):
        del operation_id_arg, task_responses, started_at
        reassembly_started.set()
        reassembly_was_released_by_loop.append(reassembly_released.wait(timeout=0.5))
        return [{"page_number": 1}]

    split_hook._elements_from_task_responses = _slow_reassembly  # type: ignore[method-assign]

    async def _release_when_started(started: threading.Event, release: threading.Event) -> None:
        while not started.is_set():
            await asyncio.sleep(0)
        release.set()

    async with _make_dummy_request_client() as top_level_client:
        sdk = _make_base_sdk_with_hooks(_make_split_hooks(split_hook), top_level_client)
        response, _ = await asyncio.gather(
            sdk.do_request_async(
                _make_sdk_hook_context(),
                httpx.Request("POST", "http://localhost:8888/general/v0/general"),
                error_status_codes=[],
            ),
            _release_when_started(reassembly_started, reassembly_released),
        )

    assert response.json() == [{"page_number": 1}]
    assert reassembly_was_released_by_loop == [True]
    assert operation_id not in split_hook.coroutines_to_execute
