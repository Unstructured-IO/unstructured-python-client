from __future__ import annotations

import functools
import io
import logging
import math
import platform
from concurrent.futures import Future, ProcessPoolExecutor
from typing import Optional, Tuple, Union

import requests
from pypdf import PdfReader
from requests_toolbelt.multipart.decoder import MultipartDecoder

from unstructured_client._hooks.custom import form_utils, pdf_utils, request_utils
from unstructured_client._hooks.custom.common import UNSTRUCTURED_CLIENT_LOGGER_NAME
from unstructured_client._hooks.custom.form_utils import (
    PARTITION_FORM_CONCURRENCY_LEVEL_KEY,
    PARTITION_FORM_FILES_KEY,
    PARTITION_FORM_SPLIT_PDF_PAGE_KEY,
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
DEFAULT_CONCURRENCY_LEVEL = 5
MAX_CONCURRENCY_LEVEL = 15
MIN_PAGES_PER_SPLIT = 2
MAX_PAGES_PER_SPLIT = 20


if platform.system() == "Darwin":
    import multiprocessing

    multiprocessing.set_start_method("fork", force=True)


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
        self.partition_responses: dict[str, list[requests.Response]] = {}
        self.partition_requests: dict[str, list[Future[requests.Response]]] = {}

    def sdk_init(self, base_url: str, client: requests.Session) -> Tuple[str, requests.Session]:
        """Initializes Split PDF Hook.

        Args:
            base_url (str): URL of the API.
            client (requests.Session): HTTP Client.

        Returns:
            Tuple[str, requests.Session]: The initialized SDK options.
        """
        self.client = client
        return base_url, client

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

        operation_id = hook_ctx.operation_id
        content_type = request.headers.get("Content-Type")
        body = request.body
        if not isinstance(body, bytes) or content_type is None:
            return request

        decoded_body = MultipartDecoder(body, content_type)
        form_data = form_utils.parse_form_data(decoded_body)
        split_pdf_page = form_data.get(PARTITION_FORM_SPLIT_PDF_PAGE_KEY)
        if split_pdf_page is None or split_pdf_page == "false":
            return request

        file = form_data.get(PARTITION_FORM_FILES_KEY)
        if file is None or not isinstance(file, shared.Files) or not pdf_utils.is_pdf(file):
            logger.warning("Reverting to non-split pdf handling path.")
            return request

        starting_page_number = form_utils.get_starting_page_number(
            form_data,
            key=PARTITION_FORM_STARTING_PAGE_NUMBER_KEY,
            fallback_value=DEFAULT_STARTING_PAGE_NUMBER,
        )
        concurrency_level = form_utils.get_split_pdf_concurrency_level_param(
            form_data,
            key=PARTITION_FORM_CONCURRENCY_LEVEL_KEY,
            fallback_value=DEFAULT_CONCURRENCY_LEVEL,
            max_allowed=MAX_CONCURRENCY_LEVEL,
        )

        pdf = PdfReader(io.BytesIO(file.content))
        split_size = get_optimal_split_size(
            num_pages=len(pdf.pages), concurrency_level=concurrency_level
        )
        pages = pdf_utils.get_pdf_pages(pdf, split_size)

        call_api_partial = functools.partial(
            request_utils.call_api,
            client=self.client,
            request=request,
            form_data=form_data,
            filename=file.file_name,
        )
        self.partition_requests[operation_id] = []
        last_page_content = io.BytesIO()
        last_page_number = 0
        with ProcessPoolExecutor(max_workers=concurrency_level) as executor:
            for page_content, page_index, all_pages_number in pages:
                page_number = page_index + starting_page_number
                # Check if this page is the last one
                if page_index == all_pages_number - 1:
                    last_page_content = page_content
                    last_page_number = page_number
                    break
                self.partition_requests[operation_id].append(
                    executor.submit(call_api_partial, page=(page_content, page_number))
                )

        # `before_request` method needs to return a request so we skip sending the last page in parallel
        # and return that last page at the end of this method
        last_page_request = request_utils.create_request(
            request, form_data, last_page_content, file.file_name, last_page_number
        )
        last_page_prepared_request = self.client.prepare_request(last_page_request)
        return last_page_prepared_request

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
        operation_id = hook_ctx.operation_id
        # We know that this request failed so we pass a failed or empty response to `_await_elements` method
        # where it checks if at least on of the other requests succeeded
        elements = self._await_elements(operation_id, response or requests.Response())
        responses = self.partition_responses.get(operation_id)

        if elements is None or responses is None:
            return (response, error)

        if len(responses) == 0:
            if error is not None:
                logger.error(error)
            self._clear_operation(operation_id)
            return (response, error)

        updated_response = request_utils.create_response(responses[0], elements)
        self._clear_operation(operation_id)
        return (updated_response, None)

    def _await_elements(self, operation_id: str, response: requests.Response) -> Optional[list]:
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
        prt_requests = self.partition_requests.get(operation_id)

        if prt_requests is None:
            return None

        responses = []
        elements = []
        for future in prt_requests:
            res = future.result()
            if res.status_code == 200:
                responses.append(res)
                elements.append(res.json())

        if response.status_code == 200:
            elements.append(response.json())

        self.partition_responses[operation_id] = responses
        flattened_elements = [element for sublist in elements for element in sublist]
        return flattened_elements

    def _clear_operation(self, operation_id: str) -> None:
        """
        Clears the operation data associated with the given operation ID.

        Args:
            operation_id (str): The ID of the operation to clear.
        """
        self.partition_responses.pop(operation_id, None)
        self.partition_requests.pop(operation_id, None)
