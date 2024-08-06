from __future__ import annotations

import asyncio
import io
import json
import logging
import math
from collections.abc import Awaitable
from typing import Any, Coroutine, Optional, Tuple, Union

import httpx
import nest_asyncio
import requests
from pypdf import PdfReader
from requests_toolbelt.multipart.decoder import MultipartDecoder

from unstructured_client._hooks.custom import form_utils, pdf_utils, request_utils
from unstructured_client._hooks.custom.common import UNSTRUCTURED_CLIENT_LOGGER_NAME
from unstructured_client._hooks.custom.form_utils import (
    PARTITION_FORM_CONCURRENCY_LEVEL_KEY,
    PARTITION_FORM_FILES_KEY,
    PARTITION_FORM_PAGE_RANGE_KEY,
    PARTITION_FORM_SPLIT_PDF_PAGE_KEY,
    PARTITION_FORM_SPLIT_PDF_ALLOW_FAILED_KEY,
    PARTITION_FORM_STARTING_PAGE_NUMBER_KEY,
)
from unstructured_client._hooks.types import (
    AfterErrorContext,
    AfterErrorHook,
    AfterSuccessContext,
    AfterSuccessHook,
    BeforeRequestContext,
    BeforeRequestHook,
    SDKInitHook,
)
from unstructured_client.models import shared

logger = logging.getLogger(UNSTRUCTURED_CLIENT_LOGGER_NAME)

DEFAULT_STARTING_PAGE_NUMBER = 1
DEFAULT_ALLOW_FAILED = False
DEFAULT_CONCURRENCY_LEVEL = 8
MAX_CONCURRENCY_LEVEL = 15
MIN_PAGES_PER_SPLIT = 2
MAX_PAGES_PER_SPLIT = 20


async def _order_keeper(index: int, coro: Awaitable) -> Tuple[int, requests.Response]:
    response = await coro
    return index, response


async def run_tasks(coroutines: list[Awaitable], allow_failed: bool = False) -> list[tuple[int, requests.Response]]:
    if allow_failed:
        responses = await asyncio.gather(*coroutines, return_exceptions=False)
        return list(enumerate(responses, 1))
    # TODO: replace with asyncio.TaskGroup for python >3.11 # pylint: disable=fixme
    tasks = [asyncio.create_task(_order_keeper(index, coro)) for index, coro in enumerate(coroutines, 1)]
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


def context_is_uvloop():
    """Return true if uvloop is installed and we're currently in a uvloop context. Our asyncio splitting code currently doesn't work under uvloop."""
    try:
        import uvloop  # pylint: disable=import-outside-toplevel
        loop = asyncio.get_event_loop()
        return isinstance(loop, uvloop.Loop)
    except (ImportError, RuntimeError):
        return False

def get_optimal_split_size(num_pages: int, concurrency_level: int) -> int:
    """Distributes pages to workers evenly based on the number of pages and desired concurrency level."""
    if num_pages < MAX_PAGES_PER_SPLIT * concurrency_level:
        split_size = math.ceil(num_pages / concurrency_level)
    else:
        split_size = MAX_PAGES_PER_SPLIT

    return max(split_size, MIN_PAGES_PER_SPLIT)


class SplitPdfHook(SDKInitHook, BeforeRequestHook, AfterSuccessHook, AfterErrorHook):
    """
    A hook class that splits a PDF file into multiple pages and sends each page as
    a separate request. This hook is designed to be used with an Speakeasy SDK.

    Usage:
    1. Create an instance of the `SplitPdfHook` class.
    2. Register SDK Init, Before Request, After Success and After Error hooks.
    """

    def __init__(self) -> None:
        self.client: Optional[requests.Session] = None
        self.coroutines_to_execute: dict[
            str, list[Coroutine[Any, Any, requests.Response]]
        ] = {}
        self.api_successful_responses: dict[str, list[requests.Response]] = {}
        self.api_failed_responses: dict[str, list[requests.Response]] = {}
        self.allow_failed: bool = DEFAULT_ALLOW_FAILED

    def sdk_init(
            self, base_url: str, client: requests.Session
    ) -> Tuple[str, requests.Session]:
        """Initializes Split PDF Hook.

        Args:
            base_url (str): URL of the API.
            client (requests.Session): HTTP Client.

        Returns:
            Tuple[str, requests.Session]: The initialized SDK options.
        """
        self.client = client
        return base_url, client


    # pylint: disable=too-many-return-statements
    def before_request(
            self, hook_ctx: BeforeRequestContext, request: requests.PreparedRequest
    ) -> Union[requests.PreparedRequest, Exception]:
        """If `splitPdfPage` is set to `true` in the request, the PDF file is split into
        separate pages. Each page is sent as a separate request in parallel. The last
        page request is returned by this method. It will return the original request
        when: `splitPdfPage` is set to `false`, the file is not a PDF, or the HTTP
        has not been initialized.

        Args:
            hook_ctx (BeforeRequestContext): The hook context containing information about
            the operation.
            request (requests.PreparedRequest): The request object.

        Returns:
            Union[requests.PreparedRequest, Exception]: If `splitPdfPage` is set to `true`,
            the last page request; otherwise, the original request.
        """
        if self.client is None:
            logger.warning("HTTP client not accessible! Continuing without splitting.")
            return request

        if context_is_uvloop():
            logger.warning("Splitting is currently incompatible with uvloop. Continuing without splitting.")
            return request

        # This allows us to use an event loop in an env with an existing loop
        # Temporary fix until we can improve the async splitting behavior
        nest_asyncio.apply()
        operation_id = hook_ctx.operation_id
        content_type = request.headers.get("Content-Type")
        body = request.body
        if not isinstance(body, bytes) or content_type is None:
            return request

        decoded_body = MultipartDecoder(body, content_type)
        form_data = form_utils.parse_form_data(decoded_body)
        split_pdf_page = form_data.get(PARTITION_FORM_SPLIT_PDF_PAGE_KEY)
        if split_pdf_page is None or split_pdf_page == "false":
            logger.info("Partitioning without split.")
            return request

        logger.info("Preparing to split document for partition.")
        file = form_data.get(PARTITION_FORM_FILES_KEY)
        if (
                file is None
                or not isinstance(file, shared.Files)
                or not pdf_utils.is_pdf(file)
        ):
            logger.info("Partitioning without split.")
            return request

        starting_page_number = form_utils.get_starting_page_number(
            form_data,
            key=PARTITION_FORM_STARTING_PAGE_NUMBER_KEY,
            fallback_value=DEFAULT_STARTING_PAGE_NUMBER,
        )
        if starting_page_number > 1:
            logger.info("Starting page number set to %d", starting_page_number)
        logger.info("Starting page number set to %d", starting_page_number)

        self.allow_failed = form_utils.get_split_pdf_allow_failed_param(
            form_data,
            key=PARTITION_FORM_SPLIT_PDF_ALLOW_FAILED_KEY,
            fallback_value=DEFAULT_ALLOW_FAILED,
        )
        logger.info("Allow failed set to %d", self.allow_failed)

        concurrency_level = form_utils.get_split_pdf_concurrency_level_param(
            form_data,
            key=PARTITION_FORM_CONCURRENCY_LEVEL_KEY,
            fallback_value=DEFAULT_CONCURRENCY_LEVEL,
            max_allowed=MAX_CONCURRENCY_LEVEL,
        )
        logger.info("Concurrency level set to %d", concurrency_level)
        limiter = asyncio.Semaphore(concurrency_level)

        pdf = PdfReader(io.BytesIO(file.content))

        page_range_start, page_range_end = form_utils.get_page_range(
            form_data,
            key=PARTITION_FORM_PAGE_RANGE_KEY,
            max_pages=len(pdf.pages),
        )

        page_count = page_range_end - page_range_start + 1
        logger.info(
            "Splitting pages %d to %d (%d total)",
            page_range_start,
            page_range_end,
            page_count,
        )

        split_size = get_optimal_split_size(
            num_pages=page_count, concurrency_level=concurrency_level
        )
        logger.info("Determined optimal split size of %d pages.", split_size)

        # If the doc is small enough, and we aren't slicing it with a page range:
        # do not split, just continue with the original request
        if split_size >= page_count and page_count == len(pdf.pages):
            logger.info(
                "Document has too few pages (%d) to be split efficiently. Partitioning without split.",
                page_count,
            )
            return request

        pages = pdf_utils.get_pdf_pages(pdf, split_size=split_size, page_start=page_range_start, page_end=page_range_end)
        logger.info(
            "Partitioning %d files with %d page(s) each.",
            math.floor(page_count / split_size),
            split_size,
        )

        # Log the remainder pages if there are any
        if page_count % split_size > 0:
            logger.info(
                "Partitioning 1 file with %d page(s).",
                page_count % split_size,
            )

        async def call_api_partial(page):
            async with httpx.AsyncClient() as client:
                status_code, json_response = await request_utils.call_api_async(
                    client=client,
                    original_request=request,
                    form_data=form_data,
                    filename=file.file_name,
                    page=page,
                    limiter=limiter,
                )

                # convert httpx response to requests.Response to preserve
                # compatibility with the synchronous SDK generated by speakeasy
                response = requests.Response()
                response.status_code = status_code
                response._content = json.dumps(  # pylint: disable=W0212
                    json_response
                ).encode()
                response.headers["Content-Type"] = "application/json"
                return response

        self.coroutines_to_execute[operation_id] = []
        last_page_content = io.BytesIO()
        last_page_number = 0
        set_index = 1
        for page_content, page_index, all_pages_number in pages:
            page_number = page_index + starting_page_number
            logger.info(
                "Partitioning set #%d (pages %d-%d).",
                set_index,
                page_number,
                min(page_number + split_size - 1, all_pages_number),
            )
            # Check if this set of pages is the last one
            if page_index + split_size >= all_pages_number:
                last_page_content = page_content
                last_page_number = page_number
                break
            coroutine = call_api_partial((page_content, page_number))
            self.coroutines_to_execute[operation_id].append(coroutine)
            set_index += 1
        # `before_request` method needs to return a request so we skip sending the last page in parallel
        # and return that last page at the end of this method

        body = request_utils.create_request_body(
            form_data, last_page_content, file.file_name, last_page_number
        )
        last_page_request = request_utils.create_request(request, body)
        last_page_prepared_request = self.client.prepare_request(last_page_request)
        return last_page_prepared_request

    def _await_elements(
            self, operation_id: str, response: requests.Response
    ) -> Optional[list]:
        """
        Waits for the partition requests to complete and returns the flattened
        elements.

        Args:
            operation_id (str): The ID of the operation.
            response (requests.Response): The response object.

        Returns:
            Optional[list]: The flattened elements if the partition requests are
            completed, otherwise None.
        """
        tasks = self.coroutines_to_execute.get(operation_id)
        if tasks is None:
            return None

        ioloop = asyncio.get_event_loop()
        task_responses: list[tuple[int, requests.Response]] = ioloop.run_until_complete(
            run_tasks(tasks, allow_failed=self.allow_failed)
        )

        if task_responses is None:
            return None

        successful_responses = []
        failed_responses = []
        elements = []
        for response_number, res in task_responses:
            request_utils.log_after_split_response(res.status_code, response_number)
            if res.status_code == 200:
                successful_responses.append(res)
                elements.append(res.json())
            else:
                failed_responses.append(res)

        if self.allow_failed or not failed_responses:
            last_response_number = len(task_responses) + 1
            request_utils.log_after_split_response(
                response.status_code, last_response_number
            )
            if response.status_code == 200:
                elements.append(response.json())
                successful_responses.append(response)
            else:
                failed_responses.append(response)

        self.api_successful_responses[operation_id] = successful_responses
        self.api_failed_responses[operation_id] = failed_responses
        flattened_elements = [element for sublist in elements for element in sublist]
        return flattened_elements

    def after_success(
            self, hook_ctx: AfterSuccessContext, response: requests.Response
    ) -> Union[requests.Response, Exception]:
        """Executes after a successful API request. Awaits all parallel requests and
        combines the responses into a single response object.

        Args:
            hook_ctx (AfterSuccessContext): The context object containing information
            about the hook execution.
            response (requests.Response): The response object returned from the API
            request.

        Returns:
            Union[requests.Response, Exception]: If requests were run in parallel, a
            combined response object; otherwise, the original response. Can return
            exception if it ocurred during the execution.
        """
        operation_id = hook_ctx.operation_id
        # Because in `before_request` method we skipped sending last page in parallel
        # we need to pass response, which contains last page, to `_await_elements` method
        elements = self._await_elements(operation_id, response)

        # if fails are disallowed, return the first failed response
        if not self.allow_failed and self.api_failed_responses.get(operation_id):
            return self.api_failed_responses[operation_id][0]

        if elements is None:
            return response

        updated_response = request_utils.create_response(response, elements)
        self._clear_operation(operation_id)
        return updated_response

    def after_error(
            self,
            hook_ctx: AfterErrorContext,
            response: Optional[requests.Response],
            error: Optional[Exception],
    ) -> Union[Tuple[Optional[requests.Response], Optional[Exception]], Exception]:
        """Executes after an unsuccessful API request. Awaits all parallel requests,
        if at least one request was successful, combines the responses into a single
        response object and doesn't throw an error. It will return an error only if
        all requests failed, or there was no PDF split.

        Args:
            hook_ctx (AfterErrorContext): The AfterErrorContext object containing
            information about the hook context.
            response (Optional[requests.Response]): The Response object representing
            the response received before the exception occurred.
            error (Optional[Exception]): The exception object that was thrown.

        Returns:
            Union[Tuple[Optional[requests.Response], Optional[Exception]], Exception]:
            If requests were run in parallel, and at least one was successful, a combined
            response object; otherwise, the original response and exception.
        """

        # if fails are disallowed - return response and error objects immediately
        if not self.allow_failed:
            return (response, error)

        operation_id = hook_ctx.operation_id
        # We know that this request failed so we pass a failed or empty response to `_await_elements` method
        # where it checks if at least on of the other requests succeeded
        elements = self._await_elements(operation_id, response or requests.Response())
        successful_responses = self.api_successful_responses.get(operation_id)

        if elements is None or successful_responses is None:
            return (response, error)

        if len(successful_responses) == 0:
            self._clear_operation(operation_id)
            return (response, error)

        updated_response = request_utils.create_response(
            successful_responses[0], elements
        )
        self._clear_operation(operation_id)
        return (updated_response, None)

    def _clear_operation(self, operation_id: str) -> None:
        """
        Clears the operation data associated with the given operation ID.

        Args:
            operation_id (str): The ID of the operation to clear.
        """
        self.coroutines_to_execute.pop(operation_id, None)
        self.api_successful_responses.pop(operation_id, None)
