from __future__ import annotations

import asyncio
import io
import json
import logging
import math
import os
import tempfile
import uuid
from collections.abc import Awaitable
from concurrent import futures
from functools import partial
from pathlib import Path
from typing import Any, Coroutine, Optional, Tuple, Union, cast, Generator, BinaryIO

import aiofiles
import httpx
from httpx import AsyncClient
from pypdf import PdfReader, PdfWriter

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

def _run_coroutines_in_separate_thread(
        coroutines_task: Coroutine[Any, Any, list[tuple[int, httpx.Response]]],
) -> list[tuple[int, httpx.Response]]:
    return asyncio.run(coroutines_task)


async def _order_keeper(index: int, coro: Awaitable) -> Tuple[int, httpx.Response]:
    response = await coro
    return index, response


async def run_tasks(
    coroutines: list[partial[Coroutine[Any, Any, httpx.Response]]],
    allow_failed: bool = False,
    concurrency_level: int = 10,
) -> list[tuple[int, httpx.Response]]:
    """Run a list of coroutines in parallel and return the results in order.

    Args:
        coroutines (list[Callable[[Coroutine], Awaitable]): A list of fuctions
            parametrized with async_client that return Awaitable objects.
        allow_failed (bool, optional): If True, failed responses will be included
            in the results. Otherwise, the first failed request breaks the
            process. Defaults to False.
    """


    # Use a variable to adjust the httpx client timeout, or default to 30 minutes
    # When we're able to reuse the SDK to make these calls, we can remove this var
    # The SDK timeout will be controlled by parameter
    limiter = asyncio.Semaphore(concurrency_level)
    client_timeout_minutes = 60
    if timeout_var := os.getenv("UNSTRUCTURED_CLIENT_TIMEOUT_MINUTES"):
        client_timeout_minutes = int(timeout_var)
    client_timeout = httpx.Timeout(60 * client_timeout_minutes)

    async with httpx.AsyncClient(timeout=client_timeout) as client:
        armed_coroutines = [coro(async_client=client, limiter=limiter) for coro in coroutines] # type: ignore
        if allow_failed:
            responses = await asyncio.gather(*armed_coroutines, return_exceptions=False)
            return list(enumerate(responses, 1))
        # TODO: replace with asyncio.TaskGroup for python >3.11 # pylint: disable=fixme
        tasks = [asyncio.create_task(_order_keeper(index, coro))
                 for index, coro in enumerate(armed_coroutines, 1)]
        results = []
        remaining_tasks = dict(enumerate(tasks, 1))
        for future in asyncio.as_completed(tasks):
            index, response = await future
            if response.status_code != 200:
                # cancel all remaining tasks
                for remaining_task in remaining_tasks.values():
                    remaining_task.cancel()
                results.append((index, response))
                break
            results.append((index, response))
            # remove task from remaining_tasks that should be cancelled in case of failure
            del remaining_tasks[index]
        # return results in the original order
        return sorted(results, key=lambda x: x[0])


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

    def __init__(self) -> None:
        self.client: Optional[HttpClient] = None
        self.partition_base_url: Optional[str] = None
        self.is_partition_request: bool = False
        self.async_client: Optional[AsyncHttpClient] = None
        self.coroutines_to_execute: dict[
            str, list[partial[Coroutine[Any, Any, httpx.Response]]]
        ] = {}
        self.concurrency_level: dict[str, int] = {}
        self.api_successful_responses: dict[str, list[httpx.Response]] = {}
        self.api_failed_responses: dict[str, list[httpx.Response]] = {}
        self.executors: dict[str, futures.ThreadPoolExecutor] = {}
        self.tempdirs: dict[str, tempfile.TemporaryDirectory] = {}
        self.allow_failed: bool = DEFAULT_ALLOW_FAILED
        self.cache_tmp_data_feature: bool = DEFAULT_CACHE_TMP_DATA
        self.cache_tmp_data_dir: str = DEFAULT_CACHE_TMP_DATA_DIR

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

        # Instead, save the base url so we can use it for our dummy request
        # As this can be overwritten with Platform API URL, we need to get it again in
        # `before_request` hook from the request object as the real URL is not available here.
        self.partition_base_url = base_url

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
    def before_request(
            self, hook_ctx: BeforeRequestContext, request: httpx.Request
    ) -> Union[httpx.Request, Exception]:
        """If `splitPdfPage` is set to `true` in the request, the PDF file is split into
        separate pages. Each page is sent as a separate request in parallel. The last
        page request is returned by this method. It will return the original request
        when: `splitPdfPage` is set to `false`, the file is not a PDF, or the HTTP
        has not been initialized.

        Args:
            hook_ctx (BeforeRequestContext): The hook context containing information about
            the operation.
            request (httpx.PreparedRequest): The request object.

        Returns:
            Union[httpx.PreparedRequest, Exception]: If `splitPdfPage` is set to `true`,
            the last page request; otherwise, the original request.
        """

        # Actually the general.partition operation overwrites the default client's base url (as
        # the platform operations do). Here we need to get the base url from the request object.
        if hook_ctx.operation_id == "partition":
            self.partition_base_url = get_base_url(request.url)
            self.is_partition_request = True
        else:
            self.is_partition_request = False
            return request

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

        self.allow_failed = form_utils.get_split_pdf_allow_failed_param(
            form_data,
            key=PARTITION_FORM_SPLIT_PDF_ALLOW_FAILED_KEY,
            fallback_value=DEFAULT_ALLOW_FAILED,
        )

        self.concurrency_level[operation_id] = form_utils.get_split_pdf_concurrency_level_param(
            form_data,
            key=PARTITION_FORM_CONCURRENCY_LEVEL_KEY,
            fallback_value=DEFAULT_CONCURRENCY_LEVEL,
            max_allowed=MAX_CONCURRENCY_LEVEL,
        )

        executor = futures.ThreadPoolExecutor(max_workers=1)
        self.executors[operation_id] = executor

        self.cache_tmp_data_feature = form_utils.get_split_pdf_cache_tmp_data(
            form_data,
            key=PARTITION_FORM_SPLIT_CACHE_TMP_DATA_KEY,
            fallback_value=DEFAULT_CACHE_TMP_DATA,
        )

        self.cache_tmp_data_dir = form_utils.get_split_pdf_cache_tmp_data_dir(
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
            num_pages=page_count, concurrency_level=self.concurrency_level[operation_id]
        )

        # If the doc is small enough, and we aren't slicing it with a page range:
        # do not split, just continue with the original request
        if split_size >= page_count and page_count == len(pdf.pages):
            return request

        pdf = self._trim_large_pages(pdf, form_data)

        if self.cache_tmp_data_feature:
            pdf_chunk_paths = self._get_pdf_chunk_paths(
                pdf,
                operation_id=operation_id,
                split_size=split_size,
                page_start=page_range_start,
                page_end=page_range_end
            )
            # force free PDF object memory
            del pdf
            pdf_chunks = self._get_pdf_chunk_files(pdf_chunk_paths)
        else:
            pdf_chunks = self._get_pdf_chunks_in_memory(
                pdf,
                split_size=split_size,
                page_start=page_range_start,
                page_end=page_range_end
            )

        self.coroutines_to_execute[operation_id] = []
        set_index = 1
        for pdf_chunk_file, page_index in pdf_chunks:
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
                operation_id=operation_id,
                pdf_chunk_request=pdf_chunk_request,
                pdf_chunk_file=pdf_chunk_file,
            )
            self.coroutines_to_execute[operation_id].append(coroutine)
            set_index += 1

        # Return a dummy request for the SDK to use
        # This allows us to skip right to the AfterRequestHook and await all the calls
        # Also, pass the operation_id so after_success can await the right results

        # Note: We need access to the async_client from the sdk_init hook in order to set
        # up a mock request like this.
        # For now, just make an extra request against our api, which should return 200.
        # dummy_request = httpx.Request("GET",  "http://no-op")
        return httpx.Request(
            "GET",
            f"{self.partition_base_url}/general/docs",
            headers={"operation_id": operation_id},
        )

    async def call_api_partial(
            self,
            pdf_chunk_request: httpx.Request,
            pdf_chunk_file: BinaryIO,
            limiter: asyncio.Semaphore,
            operation_id: str,
            async_client: AsyncClient,
    ) -> httpx.Response:
        response = await request_utils.call_api_async(
            client=async_client,
            limiter=limiter,
            pdf_chunk_request=pdf_chunk_request,
            pdf_chunk_file=pdf_chunk_file,
        )

        # Immediately delete request to save memory
        del response._request  # pylint: disable=protected-access
        response._request = None  # pylint: disable=protected-access


        if response.status_code == 200:
            if self.cache_tmp_data_feature:
                # If we get 200, dump the contents to a file and return the path
                temp_dir = self.tempdirs[operation_id]
                temp_file_name = f"{temp_dir.name}/{uuid.uuid4()}.json"
                async with aiofiles.open(temp_file_name, mode='wb') as temp_file:
                    # Avoid reading the entire response into memory
                    async for bytes_chunk in response.aiter_bytes():
                        await temp_file.write(bytes_chunk)
                # we save the path in content attribute to be used in after_success
                response._content = temp_file_name.encode()  # pylint: disable=protected-access

        return response

    def _trim_large_pages(self, pdf: PdfReader, form_data: dict[str, Any]) -> PdfReader:
        if form_data['strategy'] != HI_RES_STRATEGY:
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
            pdf: PdfReader,
            split_size: int = 1,
            page_start: int = 1,
            page_end: Optional[int] = None
    ) -> Generator[Tuple[BinaryIO, int], None, None]:
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

        offset = page_start - 1
        offset_end = page_end or len(pdf.pages)

        chunk_no = 0
        while offset < offset_end:
            chunk_no += 1
            new_pdf = PdfWriter()
            chunk_buffer = io.BytesIO()

            end = min(offset + split_size, offset_end)

            for page in list(pdf.pages[offset:end]):
                new_pdf.add_page(page)
            new_pdf.write(chunk_buffer)
            chunk_buffer.seek(0)
            yield chunk_buffer, offset
            offset += split_size

    def _get_pdf_chunk_paths(
        self,
        pdf: PdfReader,
        operation_id: str,
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

        offset = page_start - 1
        offset_end = page_end or len(pdf.pages)

        tempdir = tempfile.TemporaryDirectory(  # pylint: disable=consider-using-with
            dir=self.cache_tmp_data_dir,
            prefix="unstructured_client_"
        )
        self.tempdirs[operation_id] = tempdir
        tempdir_path = Path(tempdir.name)
        pdf_chunk_paths: list[Tuple[Path, int]] = []
        chunk_no = 0
        while offset < offset_end:
            chunk_no += 1
            new_pdf = PdfWriter()

            end = min(offset + split_size, offset_end)

            for page in list(pdf.pages[offset:end]):
                new_pdf.add_page(page)
            with open(tempdir_path / f"chunk_{chunk_no}.pdf", "wb") as pdf_chunk:
                new_pdf.write(pdf_chunk)
                pdf_chunk_paths.append((Path(pdf_chunk.name), offset))
            offset += split_size
        return pdf_chunk_paths

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

        Args:
            operation_id (str): The ID of the operation.

        Returns:
            Optional[list]: The flattened elements if the partition requests are
            completed, otherwise None.
        """
        tasks = self.coroutines_to_execute.get(operation_id)
        if tasks is None:
            return None

        concurrency_level = self.concurrency_level.get(operation_id, DEFAULT_CONCURRENCY_LEVEL)
        coroutines = run_tasks(tasks, allow_failed=self.allow_failed, concurrency_level=concurrency_level)

        # sending the coroutines to a separate thread to avoid blocking the current event loop
        # this operation should be removed when the SDK is updated to support async hooks
        executor = self.executors.get(operation_id)
        if executor is None:
            raise RuntimeError("Executor not found for operation_id")
        task_responses_future = executor.submit(_run_coroutines_in_separate_thread, coroutines)
        task_responses = task_responses_future.result()

        if task_responses is None:
            return None

        successful_responses = []
        failed_responses = []
        elements = []
        for response_number, res in task_responses:
            if res.status_code == 200:
                logger.debug(
                    "Successfully partitioned set #%d, elements added to the final result.",
                    response_number,
                )
                successful_responses.append(res)
                if self.cache_tmp_data_feature:
                    elements.append(load_elements_from_response(res))
                else:
                    elements.append(res.json())
            else:
                error_message = f"Failed to partition set {response_number}."

                if self.allow_failed:
                    error_message += " Its elements will be omitted from the result."

                logger.error(error_message)
                failed_responses.append(res)

        self.api_successful_responses[operation_id] = successful_responses
        self.api_failed_responses[operation_id] = failed_responses
        flattened_elements = [element for sublist in elements for element in sublist]
        return flattened_elements

    def after_success(
            self, hook_ctx: AfterSuccessContext, response: httpx.Response
    ) -> Union[httpx.Response, Exception]:
        """Executes after a successful API request. Awaits all parallel requests and
        combines the responses into a single response object.

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
        if not self.is_partition_request:
            return response

        # Grab the correct id out of the dummy request
        operation_id = response.request.headers.get("operation_id")

        elements = self._await_elements(operation_id)

        # if fails are disallowed, return the first failed response
        if not self.allow_failed and self.api_failed_responses.get(operation_id):
            failure_response = self.api_failed_responses[operation_id][0]

            self._clear_operation(operation_id)
            return failure_response

        if elements is None:
            return response

        new_response = request_utils.create_response(elements)
        self._clear_operation(operation_id)

        return new_response

    def after_error(
            self,
            hook_ctx: AfterErrorContext,
            response: Optional[httpx.Response],
            error: Optional[Exception],
    ) -> Union[Tuple[Optional[httpx.Response], Optional[Exception]], Exception]:
        """This hook is unused. In the before hook, we return a mock request
        for the SDK to run. This will take us right to the after_success hook
        to await the split results.

        Args:
            hook_ctx (AfterErrorContext): The AfterErrorContext object containing
            information about the hook context.
            response (Optional[httpx.Response]): The Response object representing
            the response received before the exception occurred.
            error (Optional[Exception]): The exception object that was thrown.

        Returns:
            Union[Tuple[Optional[httpx.Response], Optional[Exception]], Exception]:
        """
        return (response, error)

    def _clear_operation(self, operation_id: str) -> None:
        """
        Clears the operation data associated with the given operation ID.

        Args:
            operation_id (str): The ID of the operation to clear.
        """
        self.coroutines_to_execute.pop(operation_id, None)
        self.api_successful_responses.pop(operation_id, None)
        self.concurrency_level.pop(operation_id, None)
        executor = self.executors.pop(operation_id, None)
        if executor is not None:
            executor.shutdown(wait=True)
        tempdir = self.tempdirs.pop(operation_id, None)
        if tempdir:
            tempdir.cleanup()
