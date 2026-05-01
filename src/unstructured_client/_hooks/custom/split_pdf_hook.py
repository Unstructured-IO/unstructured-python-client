from __future__ import annotations

import asyncio
import io
import json
import logging
import math
import time
import os
import tempfile
import threading
import uuid
from collections.abc import Awaitable, Iterable
from concurrent import futures
from functools import partial
from pathlib import Path
from typing import Any, Coroutine, Optional, Tuple, Union, cast, Generator, BinaryIO

import aiofiles
import httpx
from httpx import AsyncClient
from pypdf import PdfReader, PdfWriter
import pypdfium2 as pdfium  # type: ignore[import-untyped]

from unstructured_client._hooks.custom import form_utils, pdf_utils, request_utils
from unstructured_client._hooks.custom.common import UNSTRUCTURED_CLIENT_LOGGER_NAME
from unstructured_client._hooks.custom.form_utils import (
    PARTITION_FORM_CONCURRENCY_LEVEL_KEY,
    PARTITION_FORM_FILES_KEY,
    PARTITION_FORM_PAGE_RANGE_KEY,
    PARTITION_FORM_SPLIT_CACHE_TMP_DATA_DIR_KEY,
    PARTITION_FORM_SPLIT_CACHE_TMP_DATA_KEY,
    PARTITION_FORM_SPLIT_PDF_ALLOW_FAILED_KEY,
    PARTITION_FORM_SPLIT_PDF_PAGE_KEY,
    PARTITION_FORM_STARTING_PAGE_NUMBER_KEY,
)
from unstructured_client._hooks.custom.request_utils import get_base_url
from unstructured_client._hooks.types import (
    AfterErrorContext,
    AfterErrorHook,
    AfterSuccessContext,
    AfterSuccessHook,
    BeforeRequestContext,
    BeforeRequestHook,
    SDKInitHook,
)
from unstructured_client.httpclient import HttpClient, AsyncHttpClient
from unstructured_client.utils import RetryConfig

logger = logging.getLogger(UNSTRUCTURED_CLIENT_LOGGER_NAME)

DEFAULT_STARTING_PAGE_NUMBER = 1
DEFAULT_ALLOW_FAILED = False
DEFAULT_CONCURRENCY_LEVEL = 10
DEFAULT_CACHE_TMP_DATA = False
DEFAULT_CACHE_TMP_DATA_DIR = tempfile.gettempdir()
MAX_CONCURRENCY_LEVEL = 50
MIN_PAGES_PER_SPLIT = 2
MAX_PAGES_PER_SPLIT = 20
HI_RES_STRATEGY = 'hi_res'
MAX_PAGE_LENGTH = 4000
TIMEOUT_BUFFER_SECONDS = 5
DEFAULT_FUTURE_TIMEOUT_MINUTES = 60
OPERATION_ID_EXTENSION_KEY = "split_pdf_operation_id"
SPLIT_PDF_HEADER_PREFIX = "X-Unstructured-Split-"


class ChunkExecutionError(Exception):
    def __init__(self, index: int, inner: BaseException):
        super().__init__(str(inner))
        self.index = index
        self.inner = inner


def _get_request_timeout_seconds(request: httpx.Request) -> Optional[float]:
    timeout = request.extensions.get("timeout")
    if timeout is None:
        return None

    if isinstance(timeout, (int, float)):
        return float(timeout)

    if isinstance(timeout, dict):
        timeout_values = [
            float(value)
            for value in timeout.values()
            if isinstance(value, (int, float))
        ]
        if timeout_values:
            return max(timeout_values)

    return None

def _run_coroutines_in_separate_thread(
        coroutines_task: Coroutine[Any, Any, list[tuple[int, httpx.Response]]],
        loop_holder: dict[str, Optional[asyncio.AbstractEventLoop]],
) -> list[tuple[int, httpx.Response]]:
    async def runner() -> list[tuple[int, httpx.Response]]:
        loop_holder["loop"] = asyncio.get_running_loop()
        try:
            return await coroutines_task
        finally:
            loop_holder["loop"] = None

    return asyncio.run(runner())


async def _order_keeper(index: int, coro: Awaitable) -> Tuple[int, httpx.Response]:
    try:
        response = await coro
    except asyncio.CancelledError:
        raise
    except BaseException as exc:
        raise ChunkExecutionError(index, exc) from exc
    return index, response


async def run_tasks(
    coroutines: list[partial[Coroutine[Any, Any, httpx.Response]]],
    allow_failed: bool = False,
    concurrency_level: int = 10,
    client_timeout: Optional[httpx.Timeout] = None,
    operation_id: Optional[str] = None,
) -> list[tuple[int, httpx.Response]]:
    """Run a list of coroutines in parallel and return the results in order.

    Args:
        coroutines (list[Callable[[Coroutine], Awaitable]): A list of fuctions
            parametrized with async_client that return Awaitable objects.
        allow_failed (bool, optional): If True, failed responses will be included
            in the results. Otherwise, the first failed request breaks the
            process. Defaults to False.
    """


    limiter = asyncio.Semaphore(concurrency_level)
    if client_timeout is None:
        # Use a variable to adjust the httpx client timeout, or default to 60 minutes.
        # When we're able to reuse the SDK to make these calls, we can remove this var
        # and let the SDK timeout flow through directly.
        client_timeout_minutes = 60
        if timeout_var := os.getenv("UNSTRUCTURED_CLIENT_TIMEOUT_MINUTES"):
            client_timeout_minutes = int(timeout_var)
        client_timeout = httpx.Timeout(60 * client_timeout_minutes)

    logger.debug(
        "split_pdf event=batch_async_start operation_id=%s chunk_count=%d concurrency=%d client_timeout=%s allow_failed=%s",
        operation_id,
        len(coroutines),
        concurrency_level,
        client_timeout,
        allow_failed,
    )

    async with httpx.AsyncClient(timeout=client_timeout) as client:
        armed_coroutines = [coro(async_client=client, limiter=limiter) for coro in coroutines] # type: ignore
        tasks = [
            asyncio.create_task(_order_keeper(index, coro))
            for index, coro in enumerate(armed_coroutines, 1)
        ]
        try:
            return await _collect_task_responses(
                tasks,
                allow_failed=allow_failed,
                operation_id=operation_id,
            )
        except asyncio.CancelledError:
            for task in tasks:
                task.cancel()
            remaining_tasks = sum(1 for task in tasks if not task.done())
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.warning(
                "split_pdf event=batch_cancel_remaining operation_id=%s reason=caller_cancelled remaining_tasks=%d",
                operation_id,
                remaining_tasks,
            )
            raise


async def _collect_task_responses(
    tasks: list[asyncio.Task[Tuple[int, httpx.Response]]],
    *,
    allow_failed: bool,
    operation_id: Optional[str],
) -> list[tuple[int, httpx.Response]]:
    if allow_failed:
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        normalized_responses: list[tuple[int, httpx.Response]] = []
        for index, result in enumerate(responses, 1):
            if isinstance(result, ChunkExecutionError):
                logger.error(
                    "split_pdf event=chunk_transport_error operation_id=%s chunk_index=%d error_type=%s error=%s",
                    operation_id,
                    result.index,
                    type(result.inner).__name__,
                    result.inner,
                    exc_info=result.inner,
                )
                normalized_responses.append(
                    (
                        result.index,
                        _create_transport_error_response(result.inner),
                    )
                )
            elif isinstance(result, asyncio.CancelledError):
                logger.error(
                    "split_pdf event=chunk_transport_error operation_id=%s chunk_index=%d error_type=%s error=%s",
                    operation_id,
                    index,
                    type(result).__name__,
                    result,
                    exc_info=result,
                )
                normalized_responses.append((index, _create_transport_error_response(result)))
            elif isinstance(result, BaseException):
                logger.error(
                    "split_pdf event=chunk_transport_error operation_id=%s chunk_index=%d error_type=%s error=%s",
                    operation_id,
                    index,
                    type(result).__name__,
                    result,
                    exc_info=result,
                )
                normalized_responses.append((index, _create_transport_error_response(result)))
            else:
                normalized_responses.append(cast(tuple[int, httpx.Response], result))
        return normalized_responses

    results = []
    remaining_tasks = dict(enumerate(tasks, 1))
    for future in asyncio.as_completed(tasks):
        try:
            index, response = await future
        except ChunkExecutionError as exc:
            logger.error(
                "split_pdf event=chunk_transport_error operation_id=%s chunk_index=%d error_type=%s error=%s",
                operation_id,
                exc.index,
                type(exc.inner).__name__,
                exc.inner,
                exc_info=exc.inner,
            )
            for remaining_task in remaining_tasks.values():
                remaining_task.cancel()
            logger.warning(
                "split_pdf event=batch_cancel_remaining operation_id=%s reason=transport_exception failed_chunk_index=%d remaining_tasks=%d",
                operation_id,
                exc.index,
                len(remaining_tasks),
            )
            await asyncio.gather(*remaining_tasks.values(), return_exceptions=True)
            if isinstance(exc.inner, Exception):
                raise exc.inner
            raise RuntimeError("Split PDF chunk cancelled") from exc.inner
        if response.status_code != 200:
            # cancel all remaining tasks
            for remaining_task in remaining_tasks.values():
                remaining_task.cancel()
            logger.warning(
                "split_pdf event=batch_cancel_remaining operation_id=%s reason=http_error failed_chunk_index=%d status_code=%d remaining_tasks=%d",
                operation_id,
                index,
                response.status_code,
                len(remaining_tasks),
            )
            await asyncio.gather(*remaining_tasks.values(), return_exceptions=True)
            results.append((index, response))
            break
        results.append((index, response))
        # remove task from remaining_tasks that should be cancelled in case of failure
        del remaining_tasks[index]
    # return results in the original order
    return sorted(results, key=lambda x: x[0])


def _create_transport_error_response(error: BaseException) -> httpx.Response:
    request = getattr(error, "request", None)
    if not isinstance(request, httpx.Request):
        request = httpx.Request("GET", "http://split-pdf.invalid")
    return httpx.Response(
        status_code=500,
        request=request,
        content=str(error).encode(),
        extensions={"transport_exception": error},
    )


def _cancel_running_tasks() -> None:
    for task in asyncio.all_tasks():
        if not task.done():
            task.cancel()


def _request_task_cancellation(
    loop: Optional[asyncio.AbstractEventLoop],
    *,
    operation_id: str,
) -> bool:
    if loop is None:
        return False
    try:
        # This loop is private to the split-PDF worker thread, so all_tasks()
        # only targets chunk requests for the current split operation.
        loop.call_soon_threadsafe(_cancel_running_tasks)
        return True
    except RuntimeError as exc:
        if "Event loop is closed" in str(exc):
            logger.warning(
                "split_pdf event=loop_closed_during_cancel operation_id=%s",
                operation_id,
            )
            return False
        raise


def get_optimal_split_size(num_pages: int, concurrency_level: int) -> int:
    """Distributes pages to workers evenly based on the number of pages and desired concurrency level."""
    if num_pages < MAX_PAGES_PER_SPLIT * concurrency_level:
        split_size = math.ceil(num_pages / concurrency_level)
    else:
        split_size = MAX_PAGES_PER_SPLIT

    return max(split_size, MIN_PAGES_PER_SPLIT)


def load_elements_from_response(response: httpx.Response) -> list[dict]:
    """Loads elements from the response content - the response was modified
    to keep the path for the json file that should be loaded and returned

    Args:
        response (httpx.Response): The response object, which contains the path
            to the json file that should be loaded.

    Returns:
        list[dict]: The elements loaded from the response content cached in the json file.
    """
    with open(response.text, mode="r", encoding="utf-8") as file:
        return json.load(file)


class SplitPdfHook(SDKInitHook, BeforeRequestHook, AfterSuccessHook, AfterErrorHook):
    """
    A hook class that splits a PDF file into multiple pages and sends each page as
    a separate request. This hook is designed to be used with an Speakeasy SDK.

    Usage:
    1. Create an instance of the `SplitPdfHook` class.
    2. Register SDK Init, Before Request, After Success and After Error hooks.
    """
    _split_pdf_setup_lock = threading.Lock()
    _split_pdf_setup_executor = futures.ThreadPoolExecutor(
        max_workers=1,
        thread_name_prefix="split-pdf-setup",
    )
    _split_pdf_setup_gate = threading.BoundedSemaphore(value=1)
    _split_pdf_setup_poll_interval_seconds = 0.01
    _split_pdf_setup_state = threading.local()

    def __init__(self) -> None:
        self.client: Optional[HttpClient] = None
        self.async_client: Optional[AsyncHttpClient] = None
        self.coroutines_to_execute: dict[
            str, list[partial[Coroutine[Any, Any, httpx.Response]]]
        ] = {}
        self.concurrency_level: dict[str, int] = {}
        self.api_successful_responses: dict[str, list[httpx.Response]] = {}
        self.api_failed_responses: dict[str, list[httpx.Response]] = {}
        self.executors: dict[str, futures.ThreadPoolExecutor] = {}
        self.operation_futures: dict[str, futures.Future[list[tuple[int, httpx.Response]]]] = {}
        self.tempdirs: dict[str, tempfile.TemporaryDirectory] = {}
        self.operation_timeouts: dict[str, Optional[float]] = {}
        self.operation_retry_configs: dict[str, Optional[RetryConfig]] = {}
        self.operation_loops: dict[str, dict[str, Optional[asyncio.AbstractEventLoop]]] = {}
        self.pending_operation_ids: dict[str, str] = {}
        self.allow_failed: dict[str, bool] = {}
        self.cache_tmp_data_feature: dict[str, bool] = {}
        self.cache_tmp_data_dir: dict[str, str] = {}

    @staticmethod
    def _get_operation_id_from_request(request: Optional[httpx.Request]) -> Optional[str]:
        if request is None:
            return None
        extension_operation_id = request.extensions.get(OPERATION_ID_EXTENSION_KEY)
        if isinstance(extension_operation_id, str):
            return extension_operation_id
        header_operation_id = request.headers.get("operation_id")
        if header_operation_id:
            return header_operation_id
        return None

    def _get_operation_id(
        self,
        response: Optional[httpx.Response] = None,
        error: Optional[Exception] = None,
    ) -> Optional[str]:
        if response is not None:
            operation_id = self._get_operation_id_from_request(response.request)
            if operation_id is not None:
                return operation_id

        error_request = getattr(error, "request", None)
        if isinstance(error_request, httpx.Request):
            return self._get_operation_id_from_request(error_request)

        return None

    @staticmethod
    def _retry_config_observability_mode(retry_config: Optional[RetryConfig]) -> str:
        return "sdk_custom" if retry_config is not None else "sdk_default_or_unset"

    @staticmethod
    def _cache_mode_observability_value(
        cache_enabled: bool,
        cache_dir: str,
    ) -> str:
        if not cache_enabled:
            return "disabled"
        if Path(cache_dir).resolve() == Path(DEFAULT_CACHE_TMP_DATA_DIR).resolve():
            return "default"
        return "custom"

    @staticmethod
    def _is_transport_failure_response(response: httpx.Response) -> bool:
        return "transport_exception" in response.extensions

    def _build_split_failure_metadata(
        self,
        operation_id: str,
        *,
        failed_chunk_index: int,
        successful_count: int,
        failed_count: int,
        total_chunks: int,
        response: httpx.Response,
    ) -> dict[str, str]:
        metadata = {
            f"{SPLIT_PDF_HEADER_PREFIX}Operation-Id": operation_id,
            f"{SPLIT_PDF_HEADER_PREFIX}Chunk-Index": str(failed_chunk_index),
            f"{SPLIT_PDF_HEADER_PREFIX}Chunk-Count": str(total_chunks),
            f"{SPLIT_PDF_HEADER_PREFIX}Success-Count": str(successful_count),
            f"{SPLIT_PDF_HEADER_PREFIX}Failure-Count": str(failed_count),
            f"{SPLIT_PDF_HEADER_PREFIX}Transport-Failure": str(
                self._is_transport_failure_response(response)
            ).lower(),
        }
        return metadata

    def _annotate_failure_response(
        self,
        operation_id: str,
        *,
        failed_chunk_index: int,
        successful_count: int,
        failed_count: int,
        total_chunks: int,
        response: httpx.Response,
    ) -> httpx.Response:
        metadata = self._build_split_failure_metadata(
            operation_id,
            failed_chunk_index=failed_chunk_index,
            successful_count=successful_count,
            failed_count=failed_count,
            total_chunks=total_chunks,
            response=response,
        )
        response.headers.update(metadata)
        response.extensions["split_pdf_failure_metadata"] = metadata
        return response

    def sdk_init(
            self, base_url: str, client: HttpClient
    ) -> Tuple[str, HttpClient]:
        """Initializes Split PDF Hook.

        Adds a mock transport layer to the httpx client. This will return an
        empty 200 response whenever the specified "dummy host" is used. The before_request
        hook returns this request so the SDK always succeeds and jumps straight to
        after_success, where we can await the split results.

        Args:
            base_url (str): URL of the API.
            client (HttpClient): HTTP Client.

        Returns:
            Tuple[str, HttpClient]: The initialized SDK options.
        """
        class DummyTransport(httpx.BaseTransport):
            def __init__(self, base_transport: httpx.BaseTransport):
                self.base_transport = base_transport

            def handle_request(self, request: httpx.Request) -> httpx.Response:
                # Return an empty 200 response if we send a request to this dummy host
                if request.method == "GET" and request.url.host == "no-op":
                    return httpx.Response(status_code=200, content=b'')

                # Otherwise, pass the request to the default transport
                return self.base_transport.handle_request(request)

        # Note(austin) - This hook doesn't have access to the async_client
        # So, we can't do the same no-op trick for partition_async
        # class AsyncDummyTransport(httpx.AsyncBaseTransport):
        #     def __init__(self, base_transport: httpx.AsyncBaseTransport):
        #         self.base_transport = base_transport

        #     async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        #         # Return an empty 200 response if we send a request to this dummy host
        #         if request.method == "GET" and request.url.host == "no-op":
        #             return httpx.Response(status_code=200, content=b'')

        #         # Otherwise, pass the request to the default transport
        #         return await self.base_transport.handle_async_request(request)

        # Explicit cast to httpx.Client to avoid a typing error
        httpx_client = cast(httpx.Client, client)
        # async_httpx_client = cast(httpx.AsyncClient, async_client)

        # pylint: disable=protected-access
        httpx_client._transport = DummyTransport(httpx_client._transport)

        # pylint: disable=protected-access
        # async_httpx_client._transport = AsyncDummyTransport(async_httpx_client._transport)

        self.client = httpx_client
        return base_url, self.client

    # pylint: disable=too-many-return-statements
    def _before_request_unlocked(
            self, hook_ctx: BeforeRequestContext, request: httpx.Request
    ) -> Union[httpx.Request, Exception]:
        """If `splitPdfPage` is set to `true` in the request, the PDF file is split into
        chunks and the chunk requests are prepared for later execution. The split
        path returns a synthetic request carrying the split operation ID so
        after_success can collect chunk results. It returns the original request
        when `splitPdfPage` is `false`, the file is not a PDF, or the HTTP client
        has not been initialized.

        Args:
            hook_ctx (BeforeRequestContext): The hook context containing information about
            the operation.
            request (httpx.Request): The request object.

        Returns:
            Union[httpx.Request, Exception]: If `splitPdfPage` is set to `true`,
            the synthetic collection request; otherwise, the original request.
        """

        # Actually the general.partition operation overwrites the default client's base url (as
        # the platform operations do). Here we need to get the base url from the request object.
        if hook_ctx.operation_id != "partition":
            return request
        partition_base_url = get_base_url(request.url)

        if self.client is None:
            logger.warning("HTTP client not accessible! Continuing without splitting.")
            return request

        # This is our key into coroutines_to_execute
        # We need to pass it on to after_success so
        # we know which results are ours
        operation_id = str(uuid.uuid4())

        content_type = request.headers.get("Content-Type")
        if content_type is None:
            return request

        form_data = request_utils.get_multipart_stream_fields(request)
        if not form_data:
            return request

        split_pdf_page = form_data.get(PARTITION_FORM_SPLIT_PDF_PAGE_KEY)
        if split_pdf_page is None or split_pdf_page == "false":
            return request

        pdf_file_meta = form_data.get(PARTITION_FORM_FILES_KEY)
        if (
                pdf_file_meta is None or not all(metadata in pdf_file_meta for metadata in
                                            ["filename", "content_type", "file"])
        ):
            return request
        pdf_file = pdf_file_meta.get("file")
        if pdf_file is None:
            return request

        pdf = pdf_utils.read_pdf(pdf_file)
        if pdf is None:
            return request

        pdf = pdf_utils.check_pdf(pdf)

        starting_page_number = form_utils.get_starting_page_number(
            form_data,
            key=PARTITION_FORM_STARTING_PAGE_NUMBER_KEY,
            fallback_value=DEFAULT_STARTING_PAGE_NUMBER,
        )

        allow_failed = form_utils.get_split_pdf_allow_failed_param(
            form_data,
            key=PARTITION_FORM_SPLIT_PDF_ALLOW_FAILED_KEY,
            fallback_value=DEFAULT_ALLOW_FAILED,
        )

        concurrency_level = form_utils.get_split_pdf_concurrency_level_param(
            form_data,
            key=PARTITION_FORM_CONCURRENCY_LEVEL_KEY,
            fallback_value=DEFAULT_CONCURRENCY_LEVEL,
            max_allowed=MAX_CONCURRENCY_LEVEL,
        )

        cache_tmp_data_feature = form_utils.get_split_pdf_cache_tmp_data(
            form_data,
            key=PARTITION_FORM_SPLIT_CACHE_TMP_DATA_KEY,
            fallback_value=DEFAULT_CACHE_TMP_DATA,
        )

        cache_tmp_data_dir = form_utils.get_split_pdf_cache_tmp_data_dir(
            form_data,
            key=PARTITION_FORM_SPLIT_CACHE_TMP_DATA_DIR_KEY,
            fallback_value=DEFAULT_CACHE_TMP_DATA_DIR,
        )

        page_range_start, page_range_end = form_utils.get_page_range(
            form_data,
            key=PARTITION_FORM_PAGE_RANGE_KEY.replace("[]", ""),
            max_pages=pdf.get_num_pages(),
        )

        page_count = page_range_end - page_range_start + 1

        split_size = get_optimal_split_size(
            num_pages=page_count, concurrency_level=concurrency_level
        )

        # If the doc is small enough, and we aren't slicing it with a page range:
        # do not split, just continue with the original request
        if split_size >= page_count and page_count == len(pdf.pages):
            return request

        self.allow_failed[operation_id] = allow_failed
        self.cache_tmp_data_feature[operation_id] = cache_tmp_data_feature
        self.cache_tmp_data_dir[operation_id] = cache_tmp_data_dir
        self.concurrency_level[operation_id] = concurrency_level

        timeout_seconds = _get_request_timeout_seconds(request)
        if timeout_seconds is None and hook_ctx.config.timeout_ms is not None:
            timeout_seconds = hook_ctx.config.timeout_ms / 1000
        self.operation_timeouts[operation_id] = timeout_seconds
        self.operation_retry_configs[operation_id] = (
            hook_ctx.config.retry_config
            if isinstance(hook_ctx.config.retry_config, RetryConfig)
            else None
        )

        try:
            pdf = self._trim_large_pages(pdf, form_data)

            pdf.stream.seek(0)
            pdf_bytes = pdf.stream.read()

            temp_dir_path = None
            pdf_chunks: Iterable[Tuple[BinaryIO, int]]
            if cache_tmp_data_feature:
                pdf_chunk_paths = self._get_pdf_chunk_paths(
                    pdf_bytes,
                    operation_id=operation_id,
                    cache_tmp_data_dir=cache_tmp_data_dir,
                    split_size=split_size,
                    page_start=page_range_start,
                    page_end=page_range_end
                )
                temp_dir = self.tempdirs.get(operation_id)
                temp_dir_path = temp_dir.name if temp_dir is not None else None
                # force free PDF object memory
                del pdf
                pdf_chunks = self._get_pdf_chunk_files(pdf_chunk_paths)
            else:
                pdf_chunks = self._get_pdf_chunks_in_memory(
                    pdf_bytes,
                    split_size=split_size,
                    page_start=page_range_start,
                    page_end=page_range_end
                )

            self.coroutines_to_execute[operation_id] = []
            for pdf_chunk_file, page_index in pdf_chunks:
                chunk_index = len(self.coroutines_to_execute[operation_id]) + 1
                page_number = page_index + starting_page_number
                pdf_chunk_request = request_utils.create_pdf_chunk_request(
                    form_data=form_data,
                    pdf_chunk=(pdf_chunk_file, page_number),
                    filename=pdf_file_meta["filename"],
                    original_request=request,
                )
                # using partial as the shared client parameter must be passed in `run_tasks` function
                # in `after_success`.
                coroutine = partial(
                    self.call_api_partial,
                    _operation_id=operation_id,
                    chunk_index=chunk_index,
                    page_number=page_number,
                    pdf_chunk_request=pdf_chunk_request,
                    pdf_chunk_file=pdf_chunk_file,
                    retry_config=self.operation_retry_configs.get(operation_id),
                    cache_tmp_data_feature=cache_tmp_data_feature,
                    temp_dir_path=temp_dir_path,
                )
                self.coroutines_to_execute[operation_id].append(coroutine)

            logger.info(
                "split_pdf event=plan_created operation_id=%s filename=%s strategy=%s page_range=%s-%s page_count=%d split_size=%d chunk_count=%d concurrency=%d allow_failed=%s cache_mode=%s timeout_seconds=%s retry_config_mode=%s",
                operation_id,
                Path(pdf_file_meta["filename"]).name,
                form_data.get("strategy"),
                page_range_start,
                page_range_end,
                page_count,
                split_size,
                len(self.coroutines_to_execute[operation_id]),
                concurrency_level,
                allow_failed,
                self._cache_mode_observability_value(
                    cache_tmp_data_feature,
                    cache_tmp_data_dir,
                ),
                timeout_seconds,
                self._retry_config_observability_mode(
                    self.operation_retry_configs.get(operation_id),
                ),
            )

            self.pending_operation_ids[operation_id] = operation_id

            dummy_request_extensions = request.extensions.copy()
            dummy_request_extensions[OPERATION_ID_EXTENSION_KEY] = operation_id
            return httpx.Request(
                "GET",
                f"{partition_base_url}/general/docs",
                headers={"operation_id": operation_id},
                extensions=dummy_request_extensions,
            )
        except Exception:
            self._clear_operation(operation_id)
            raise

    def before_request(
            self, hook_ctx: BeforeRequestContext, request: httpx.Request
    ) -> Union[httpx.Request, Exception]:
        # pypdfium is process-global and not thread-safe; serialize split setup across clients.
        with self._split_pdf_setup_lock:
            self._split_pdf_setup_state.locked = True
            try:
                return self._before_request_unlocked(hook_ctx, request)
            finally:
                self._split_pdf_setup_state.locked = False

    async def before_request_async(
            self, hook_ctx: BeforeRequestContext, request: httpx.Request
    ) -> Union[httpx.Request, Exception]:
        # Keep pypdfium setup off the event loop while preserving a single process-wide
        # admission lane. pypdfium is not thread-safe, so cancelled callers must not
        # leave queued setup work piling up behind the worker.
        await self._acquire_split_pdf_setup_slot()
        loop = asyncio.get_running_loop()
        setup_future = loop.run_in_executor(
            self._split_pdf_setup_executor,
            self.before_request,
            hook_ctx,
            request,
        )
        try:
            return await asyncio.shield(setup_future)
        except asyncio.CancelledError:
            result = await self._finish_cancelled_split_setup(setup_future)
            if isinstance(result, httpx.Request):
                self._clear_prepared_split_request(result)
            raise
        finally:
            self._split_pdf_setup_gate.release()

    @classmethod
    async def _acquire_split_pdf_setup_slot(cls) -> None:
        while not cls._split_pdf_setup_gate.acquire(blocking=False):
            await asyncio.sleep(cls._split_pdf_setup_poll_interval_seconds)

    async def _finish_cancelled_split_setup(
        self,
        setup_future: asyncio.Future[Union[httpx.Request, Exception]],
    ) -> Optional[Union[httpx.Request, Exception]]:
        while True:
            try:
                return await asyncio.shield(setup_future)
            except asyncio.CancelledError:
                if setup_future.cancelled():
                    return None
                continue
            except Exception:
                logger.debug("Cancelled split-PDF setup failed before cleanup", exc_info=True)
                return None

    def _clear_prepared_split_request(self, request: httpx.Request) -> None:
        operation_id = self._get_operation_id_from_request(request)
        if operation_id is None:
            return
        logger.warning(
            "split_pdf event=before_request_cancel_cleanup operation_id=%s",
            operation_id,
        )
        self._clear_operation(operation_id)

    async def call_api_partial(
            self,
            pdf_chunk_request: httpx.Request,
            pdf_chunk_file: BinaryIO,
            limiter: asyncio.Semaphore,
            _operation_id: str,
            chunk_index: int,
            page_number: int,
            async_client: AsyncClient,
            retry_config: Optional[RetryConfig],
            cache_tmp_data_feature: bool,
            temp_dir_path: Optional[str],
    ) -> httpx.Response:
        logger.debug(
            "split_pdf event=chunk_start operation_id=%s chunk_index=%d page_number=%d cache_mode=%s",
            _operation_id,
            chunk_index,
            page_number,
            "cached" if cache_tmp_data_feature else "memory",
        )
        response = await request_utils.call_api_async(
            client=async_client,
            limiter=limiter,
            pdf_chunk_request=pdf_chunk_request,
            pdf_chunk_file=pdf_chunk_file,
            retry_config=retry_config,
            operation_id=_operation_id,
            chunk_index=chunk_index,
            page_number=page_number,
        )

        if response.status_code == 200:
            if cache_tmp_data_feature:
                if temp_dir_path is None:
                    raise RuntimeError("Temp directory path not found for cached split PDF operation")
                # If we get 200, dump the contents to a file and return the path
                temp_file_name = f"{temp_dir_path}/{uuid.uuid4()}.json"
                async with aiofiles.open(temp_file_name, mode='wb') as temp_file:
                    # Avoid reading the entire response into memory
                    async for bytes_chunk in response.aiter_bytes():
                        await temp_file.write(bytes_chunk)
                # we save the path in content attribute to be used in after_success
                response._content = temp_file_name.encode()  # pylint: disable=protected-access
                logger.debug(
                    "split_pdf event=chunk_cached operation_id=%s chunk_index=%d page_number=%d cache_file=%s",
                    _operation_id,
                    chunk_index,
                    page_number,
                    Path(temp_file_name).name,
                )
                response = httpx.Response(
                    status_code=response.status_code,
                    headers=response.headers,
                    content=temp_file_name.encode(),
                    extensions=response.extensions,
                )
            else:
                response = httpx.Response(
                    status_code=response.status_code,
                    headers=response.headers,
                    content=response.content,
                    extensions=response.extensions,
                )
        else:
            response = httpx.Response(
                status_code=response.status_code,
                headers=response.headers,
                content=response.content,
                extensions=response.extensions,
            )

        logger.debug(
            "split_pdf event=chunk_complete operation_id=%s chunk_index=%d page_number=%d status_code=%d",
            _operation_id,
            chunk_index,
            page_number,
            response.status_code,
        )

        return response

    def _trim_large_pages(self, pdf: PdfReader, form_data: dict[str, Any]) -> PdfReader:
        if form_data.get("strategy") != HI_RES_STRATEGY:
            return pdf

        max_page_length = MAX_PAGE_LENGTH
        any_page_over_maximum_length = False
        for page in pdf.pages:
            if page.mediabox.height >= max_page_length:
                any_page_over_maximum_length = True

        # early exit if all pages are safely under the max page length
        if not any_page_over_maximum_length:
            return pdf

        w = PdfWriter()

        # trims large pages that exceed the maximum supported height for processing
        for page in pdf.pages:
            if page.mediabox.height >= max_page_length:
                page.mediabox.top = page.mediabox.height
                page.mediabox.bottom = page.mediabox.top - max_page_length
            w.add_page(page)

        chunk_buffer = io.BytesIO()
        w.write(chunk_buffer)
        chunk_buffer.seek(0)
        return PdfReader(chunk_buffer)

    def _get_pdf_chunks_in_memory(
            self,
            pdf_bytes: bytes,
            split_size: int = 1,
            page_start: int = 1,
            page_end: Optional[int] = None
    ) -> list[Tuple[BinaryIO, int]]:
        """Reads given bytes of a pdf file and split it into n pdf-chunks, each
        with `split_size` pages. The chunks are returned as in-memory buffers.

        Args:
            file_content: Content of the PDF file.
            split_size: Split size, e.g. if the given file has 10 pages
                and this value is set to 2 it will yield 5 documents, each containing 2 pages
                of the original document. By default it will split each page to a separate file.
            page_start: Begin splitting at this page number
            page_end: If provided, split up to and including this page number

        Returns:
            The list of chunk buffers and their zero-based page offsets.
        """
        self._assert_split_pdf_setup_locked()

        pdf_chunks: list[Tuple[BinaryIO, int]] = []
        with pdfium.PdfDocument(pdf_bytes) as pdf:
            offset = page_start - 1
            offset_end = page_end if page_end else len(pdf)

            while offset < offset_end:
                end = min(offset + split_size, offset_end)

                new_pdf = pdfium.PdfDocument.new()
                try:
                    page_indices = list(range(offset, end))
                    new_pdf.import_pages(pdf, pages=page_indices)

                    chunk_buffer = io.BytesIO()
                    new_pdf.save(chunk_buffer)
                    chunk_buffer.seek(0)
                finally:
                    new_pdf.close()

                pdf_chunks.append((chunk_buffer, offset))
                offset += split_size

        return pdf_chunks

    def _get_pdf_chunk_paths(
        self,
        pdf_bytes: bytes,
        operation_id: str,
        cache_tmp_data_dir: str,
        split_size: int = 1,
        page_start: int = 1,
        page_end: Optional[int] = None
    ) -> list[Tuple[Path, int]]:
        """Reads given bytes of a pdf file and split it into n pdf-chunks, each
        with `split_size` pages. The chunks are written into temporary files in
        a temporary directory corresponding to the operation_id.

        Args:
            file_content: Content of the PDF file.
            split_size: Split size, e.g. if the given file has 10 pages
                and this value is set to 2 it will yield 5 documents, each containing 2 pages
                of the original document. By default it will split each page to a separate file.
            page_start: Begin splitting at this page number
            page_end: If provided, split up to and including this page number

        Returns:
            The list of temporary file paths.
        """
        self._assert_split_pdf_setup_locked()

        # Create temporary directory
        tempdir = tempfile.TemporaryDirectory(  # pylint: disable=consider-using-with
            dir=cache_tmp_data_dir,
            prefix="unstructured_client_"
        )
        self.tempdirs[operation_id] = tempdir
        tempdir_path = Path(tempdir.name)

        pdf_chunk_paths: list[Tuple[Path, int]] = []
        with pdfium.PdfDocument(pdf_bytes) as pdf:
            offset = page_start - 1
            offset_end = page_end if page_end else len(pdf)

            chunk_no = 0

            while offset < offset_end:
                chunk_no += 1
                end = min(offset + split_size, offset_end)

                new_pdf = pdfium.PdfDocument.new()
                try:
                    page_indices = list(range(offset, end))
                    new_pdf.import_pages(pdf, pages=page_indices)

                    chunk_path = tempdir_path / f"chunk_{chunk_no}.pdf"
                    new_pdf.save(str(chunk_path))  # Convert Path to string
                finally:
                    new_pdf.close()

                pdf_chunk_paths.append((chunk_path, offset))
                offset += split_size

        return pdf_chunk_paths

    def _assert_split_pdf_setup_locked(self) -> None:
        if not getattr(self._split_pdf_setup_state, "locked", False):
            raise RuntimeError("pypdfium split setup must run under the split-PDF setup lock")

    def _get_pdf_chunk_files(
        self, pdf_chunks: list[Tuple[Path, int]]
    ) -> Generator[Tuple[BinaryIO, int], None, None]:
        """Yields the file objects for the given pdf chunk paths.

        Args:
            pdf_chunks (list[Tuple[Path, int]]): The list of pdf chunk paths and
                their page offsets.

        Yields:
            Tuple[BinaryIO, int]: The file object and the page offset.

        Raises:
            Exception: If the file cannot be opened.
        """
        for pdf_chunk_filename, offset in pdf_chunks:
            pdf_chunk_file = None
            try:
                pdf_chunk_file = open(  # pylint: disable=consider-using-with
                    pdf_chunk_filename,
                    mode="rb"
                )
            except (FileNotFoundError, IOError):
                if pdf_chunk_file and not pdf_chunk_file.closed:
                    pdf_chunk_file.close()
                raise
            yield pdf_chunk_file, offset

    def _await_elements(self, operation_id: str) -> Optional[list]:
        """
        Waits for the partition requests to complete and returns the flattened
        elements.

        When `split_pdf_allow_failed=True`, chunk-level non-200 responses and
        transport failures are recorded in `api_failed_responses` and omitted
        from the returned element list. If every chunk fails, the combined
        result is an empty list.

        Args:
            operation_id (str): The ID of the operation.

        Returns:
            Optional[list]: The flattened elements if the partition requests are
            completed, otherwise None.
        """
        tasks = self.coroutines_to_execute.get(operation_id)
        if tasks is None:
            return None

        started_at = time.perf_counter()
        concurrency_level = self.concurrency_level.get(operation_id, DEFAULT_CONCURRENCY_LEVEL)
        timeout_seconds = self.operation_timeouts.get(operation_id)
        client_timeout = httpx.Timeout(timeout_seconds) if timeout_seconds is not None else None
        allow_failed = self.allow_failed.get(operation_id, DEFAULT_ALLOW_FAILED)
        coroutines = run_tasks(
            tasks,
            allow_failed=allow_failed,
            concurrency_level=concurrency_level,
            client_timeout=client_timeout,
            operation_id=operation_id,
        )

        # sending the coroutines to a separate thread to avoid blocking the current event loop
        executor = self.executors.get(operation_id)
        if executor is None:
            executor = futures.ThreadPoolExecutor(max_workers=1)
            self.executors[operation_id] = executor
        loop_holder: dict[str, Optional[asyncio.AbstractEventLoop]] = {"loop": None}
        self.operation_loops[operation_id] = loop_holder
        try:
            task_responses_future = executor.submit(
                _run_coroutines_in_separate_thread,
                coroutines,
                loop_holder,
            )
            self.operation_futures[operation_id] = task_responses_future

            # The per-chunk timeout bounds each HTTP call, but the batch may run in
            # multiple waves (ceil(chunks / concurrency)).  Scale the outer future
            # timeout accordingly so healthy multi-wave batches aren't killed early.
            num_waves = max(1, math.ceil(len(tasks) / concurrency_level))
            per_chunk = timeout_seconds or DEFAULT_FUTURE_TIMEOUT_MINUTES * 60
            future_timeout = per_chunk * num_waves + TIMEOUT_BUFFER_SECONDS
            logger.info(
                "split_pdf event=batch_start operation_id=%s chunk_count=%d concurrency=%d allow_failed=%s client_timeout_seconds=%s future_timeout_seconds=%s num_waves=%d",
                operation_id,
                len(tasks),
                concurrency_level,
                allow_failed,
                timeout_seconds,
                future_timeout,
                num_waves,
            )
            task_responses = task_responses_future.result(timeout=future_timeout)
        except futures.TimeoutError:
            loop = loop_holder.get("loop")
            logger.error(
                "split_pdf event=batch_timeout operation_id=%s chunk_count=%d concurrency=%d allow_failed=%s client_timeout_seconds=%s future_timeout_seconds=%s",
                operation_id,
                len(tasks),
                concurrency_level,
                allow_failed,
                timeout_seconds,
                future_timeout,
            )
            cancellation_requested = _request_task_cancellation(
                loop,
                operation_id=operation_id,
            )
            if not cancellation_requested:
                coroutines.close()
            raise
        except Exception:
            if loop_holder.get("loop") is None:
                coroutines.close()
            raise
        finally:
            if loop_holder.get("loop") is None:
                coroutines.close()

        if task_responses is None:
            return None

        return self._elements_from_task_responses(
            operation_id,
            task_responses,
            started_at=started_at,
        )

    async def _await_elements_async(self, operation_id: str) -> Optional[list]:
        tasks = self.coroutines_to_execute.get(operation_id)
        if tasks is None:
            return None

        started_at = time.perf_counter()
        concurrency_level = self.concurrency_level.get(operation_id, DEFAULT_CONCURRENCY_LEVEL)
        timeout_seconds = self.operation_timeouts.get(operation_id)
        client_timeout = httpx.Timeout(timeout_seconds) if timeout_seconds is not None else None
        allow_failed = self.allow_failed.get(operation_id, DEFAULT_ALLOW_FAILED)
        coroutines = run_tasks(
            tasks,
            allow_failed=allow_failed,
            concurrency_level=concurrency_level,
            client_timeout=client_timeout,
            operation_id=operation_id,
        )
        num_waves = max(1, math.ceil(len(tasks) / concurrency_level))
        per_chunk = timeout_seconds or DEFAULT_FUTURE_TIMEOUT_MINUTES * 60
        future_timeout = per_chunk * num_waves + TIMEOUT_BUFFER_SECONDS
        logger.info(
            "split_pdf event=batch_start operation_id=%s chunk_count=%d concurrency=%d allow_failed=%s client_timeout_seconds=%s future_timeout_seconds=%s num_waves=%d",
            operation_id,
            len(tasks),
            concurrency_level,
            allow_failed,
            timeout_seconds,
            future_timeout,
            num_waves,
        )
        try:
            task_responses = await asyncio.wait_for(coroutines, timeout=future_timeout)
        except TimeoutError:
            logger.error(
                "split_pdf event=batch_timeout operation_id=%s chunk_count=%d concurrency=%d allow_failed=%s client_timeout_seconds=%s future_timeout_seconds=%s",
                operation_id,
                len(tasks),
                concurrency_level,
                allow_failed,
                timeout_seconds,
                future_timeout,
            )
            raise

        return await asyncio.to_thread(
            self._elements_from_task_responses,
            operation_id,
            task_responses,
            started_at=started_at,
        )

    def _elements_from_task_responses(
        self,
        operation_id: str,
        task_responses: list[tuple[int, httpx.Response]],
        *,
        started_at: float,
    ) -> Optional[list]:
        if task_responses is None:
            return None

        successful_responses = []
        failed_responses: list[tuple[int, httpx.Response]] = []
        transport_failure_count = 0
        elements = []
        for response_number, res in task_responses:
            if res.status_code == 200:
                logger.debug(
                    "split_pdf event=chunk_success operation_id=%s chunk_index=%d",
                    operation_id,
                    response_number,
                )
                successful_responses.append(res)
                if self.cache_tmp_data_feature.get(operation_id, DEFAULT_CACHE_TMP_DATA):
                    elements.append(load_elements_from_response(res))
                else:
                    elements.append(res.json())
            else:
                error_message = f"Failed to partition set {response_number}."

                if self.allow_failed.get(operation_id, DEFAULT_ALLOW_FAILED):
                    error_message += " Its elements will be omitted from the result."

                if self._is_transport_failure_response(res):
                    transport_failure_count += 1
                logger.error(
                    "%s operation_id=%s status_code=%d transport_failure=%s",
                    error_message,
                    operation_id,
                    res.status_code,
                    self._is_transport_failure_response(res),
                )
                failed_responses.append((response_number, res))

        self.api_successful_responses[operation_id] = successful_responses
        self.api_failed_responses[operation_id] = [response for _, response in failed_responses]
        elapsed_ms = round((time.perf_counter() - started_at) * 1000)
        logger.info(
            "split_pdf event=batch_complete operation_id=%s chunk_count=%d success_count=%d failure_count=%d transport_failure_count=%d elapsed_ms=%d allow_failed=%s",
            operation_id,
            len(task_responses),
            len(successful_responses),
            len(failed_responses),
            transport_failure_count,
            elapsed_ms,
            self.allow_failed.get(operation_id, DEFAULT_ALLOW_FAILED),
        )
        for failed_chunk_index, response in failed_responses:
            self._annotate_failure_response(
                operation_id,
                failed_chunk_index=failed_chunk_index,
                successful_count=len(successful_responses),
                failed_count=len(failed_responses),
                total_chunks=len(task_responses),
                response=response,
            )
        flattened_elements = [element for sublist in elements for element in sublist]
        return flattened_elements

    def _build_after_success_response(
        self,
        operation_id: str,
        response: httpx.Response,
        elements: Optional[list],
    ) -> httpx.Response:
        # if fails are disallowed, return the first failed response
        if (
            not self.allow_failed.get(operation_id, DEFAULT_ALLOW_FAILED)
            and self.api_failed_responses.get(operation_id)
        ):
            logger.warning(
                "split_pdf event=top_level_failure operation_id=%s mode=strict failed_response_selected=true",
                operation_id,
            )
            return self.api_failed_responses[operation_id][0]

        if (
            self.allow_failed.get(operation_id, DEFAULT_ALLOW_FAILED)
            and not self.api_successful_responses.get(operation_id)
            and self.api_failed_responses.get(operation_id)
        ):
            logger.warning(
                "split_pdf event=top_level_failure operation_id=%s mode=allow_failed reason=no_successful_chunks",
                operation_id,
            )
            return self.api_failed_responses[operation_id][0]

        if elements is None:
            return response

        return request_utils.create_response(elements)

    @staticmethod
    def _finalize_operation_resources(
        executor: Optional[futures.ThreadPoolExecutor],
        tempdir: Optional[tempfile.TemporaryDirectory],
        operation_id: Optional[str] = None,
    ) -> None:
        if executor is not None:
            executor.shutdown(wait=False, cancel_futures=True)
        if tempdir is not None:
            tempdir.cleanup()
        logger.debug(
            "split_pdf event=resources_finalized operation_id=%s executor_shutdown=%s tempdir_cleaned=%s",
            operation_id,
            executor is not None,
            tempdir is not None,
        )

    def after_success(
            self, hook_ctx: AfterSuccessContext, response: httpx.Response
    ) -> Union[httpx.Response, Exception]:
        """Executes after a successful API request. Awaits all parallel requests and
        combines the responses into a single response object.

        Partial-failure policy:
        - `allow_failed=False`: return the first failed chunk response.
        - `allow_failed=True`: return a synthetic 200 response containing only
          successful chunk elements when at least one chunk succeeds; if no
          chunk succeeds, return the first failed chunk response.

        Args:
            hook_ctx (AfterSuccessContext): The context object containing information
            about the hook execution.
            response (httpx.Response): The response object from the SDK call. This was a dummy
            request just to get us to the AfterSuccessHook.

        Returns:
            Union[httpx.Response, Exception]: If requests were run in parallel, a
            combined response object; otherwise, the original response. Can return
            exception if it ocurred during the execution.
        """
        operation_id = self._get_operation_id(response=response)
        if operation_id is None or operation_id not in self.coroutines_to_execute:
            return response

        try:
            elements = self._await_elements(operation_id)
            return self._build_after_success_response(operation_id, response, elements)
        finally:
            if operation_id is not None:
                self._clear_operation(operation_id)

    async def after_success_async(
            self, hook_ctx: AfterSuccessContext, response: httpx.Response
    ) -> Union[httpx.Response, Exception]:
        """Async equivalent of `after_success` for `partition_async`.

        This path awaits split chunk requests directly on the caller's event loop
        instead of creating a nested event loop in a worker thread.
        """
        del hook_ctx
        operation_id = self._get_operation_id(response=response)
        if operation_id is None or operation_id not in self.coroutines_to_execute:
            return response

        try:
            elements = await self._await_elements_async(operation_id)
            return await asyncio.to_thread(
                self._build_after_success_response,
                operation_id,
                response,
                elements,
            )
        finally:
            if operation_id is not None:
                self._clear_operation(operation_id)

    def after_error(
            self,
            hook_ctx: AfterErrorContext,
            response: Optional[httpx.Response],
            error: Optional[Exception],
    ) -> Union[Tuple[Optional[httpx.Response], Optional[Exception]], Exception]:
        """Clean up split-PDF state when the dummy request fails.

        If `before_request` prepared a split operation but the subsequent
        dummy request errored (e.g. network failure on GET /general/docs),
        we must release the executor, temp files, and coroutine list that
        were allocated for that operation.
        """
        operation_id = self._get_operation_id(response=response, error=error)
        if operation_id is not None:
            logger.warning(
                "split_pdf event=after_error_cleanup operation_id=%s response_present=%s error_type=%s",
                operation_id,
                response is not None,
                type(error).__name__ if error is not None else None,
            )
            self._clear_operation(operation_id)
        return (response, error)

    def _clear_operation(self, operation_id: str) -> None:
        """
        Clears the operation data associated with the given operation ID.

        Args:
            operation_id (str): The ID of the operation to clear.
        """
        tasks = self.coroutines_to_execute.pop(operation_id, None)
        closed_chunk_files = self._close_unconsumed_chunk_files(tasks)
        self.api_successful_responses.pop(operation_id, None)
        self.api_failed_responses.pop(operation_id, None)
        self.concurrency_level.pop(operation_id, None)
        self.operation_timeouts.pop(operation_id, None)
        self.operation_retry_configs.pop(operation_id, None)
        self.allow_failed.pop(operation_id, None)
        self.cache_tmp_data_feature.pop(operation_id, None)
        self.cache_tmp_data_dir.pop(operation_id, None)
        self.pending_operation_ids.pop(operation_id, None)
        future = self.operation_futures.pop(operation_id, None)
        loop_holder = self.operation_loops.pop(operation_id, None)
        executor = self.executors.pop(operation_id, None)
        tempdir = self.tempdirs.pop(operation_id, None)
        logger.debug(
            "split_pdf event=clear_operation operation_id=%s has_future=%s future_done=%s has_executor=%s has_tempdir=%s closed_chunk_files=%d",
            operation_id,
            future is not None,
            future.done() if future is not None else None,
            executor is not None,
            tempdir is not None,
            closed_chunk_files,
        )
        if future is not None and not future.done():
            loop = loop_holder.get("loop") if loop_holder is not None else None
            cancellation_requested = _request_task_cancellation(
                loop,
                operation_id=operation_id,
            )
            if not cancellation_requested:
                logger.warning(
                    "split_pdf event=clear_operation_deferred_no_loop operation_id=%s reason=worker_still_running",
                    operation_id,
                )
            else:
                logger.warning(
                    "split_pdf event=clear_operation_deferred operation_id=%s reason=worker_still_running",
                    operation_id,
                )
            future.add_done_callback(
                lambda _: self._finalize_operation_resources(executor, tempdir, operation_id)
            )
            return
        self._finalize_operation_resources(executor, tempdir, operation_id)

    @staticmethod
    def _close_unconsumed_chunk_files(
        tasks: Optional[list[partial[Coroutine[Any, Any, httpx.Response]]]],
    ) -> int:
        if tasks is None:
            return 0

        closed_count = 0
        seen_files: set[int] = set()
        for task in tasks:
            keywords = getattr(task, "keywords", None) or {}
            pdf_chunk_file = keywords.get("pdf_chunk_file")
            if pdf_chunk_file is None or id(pdf_chunk_file) in seen_files:
                continue
            seen_files.add(id(pdf_chunk_file))
            close = getattr(pdf_chunk_file, "close", None)
            if close is None or getattr(pdf_chunk_file, "closed", False) is True:
                continue
            try:
                close()
                closed_count += 1
            except Exception:
                logger.debug("Failed to close split-PDF chunk file during cleanup", exc_info=True)
        return closed_count
