from __future__ import annotations

import functools
import io
import logging
import math
import platform
import asyncio
from typing import Optional, Tuple, Union

# import requests
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


import copy
import io
import json
import logging
from typing import Optional, Tuple

# import requests
# from requests.structures import CaseInsensitiveDict
from requests_toolbelt.multipart.encoder import MultipartEncoder

from unstructured_client._hooks.custom.common import UNSTRUCTURED_CLIENT_LOGGER_NAME
from unstructured_client._hooks.custom.form_utils import (
    PARTITION_FORM_FILES_KEY,
    PARTITION_FORM_SPLIT_PDF_PAGE_KEY,
    PARTITION_FORM_STARTING_PAGE_NUMBER_KEY,
    FormData,
)

from httpx import Request, Headers, QueryParams
import httpx

logger = logging.getLogger(UNSTRUCTURED_CLIENT_LOGGER_NAME)


def create_httpx_request(
    request: httpx.Request,
    form_data: FormData,
    page_content: io.BytesIO,
    filename: str,
    page_number: int,
) -> httpx.Request:
    headers = prepare_request_headers(request.headers)
    payload = prepare_request_payload(form_data)
    body = MultipartEncoder(
        fields={
            **payload,
            PARTITION_FORM_FILES_KEY: (
                filename,
                page_content,
                "application/pdf",
            ),
            PARTITION_FORM_STARTING_PAGE_NUMBER_KEY: str(page_number),
        }
    )
    return httpx.Request(
        method="POST",
        url=request.url or "",
        content=body.to_string(),
        headers={**headers, "Content-Type": body.content_type},
    )


async def call_api(
    client: Optional[httpx.AsyncClient],
    page: Tuple[io.BytesIO, int],
    request: httpx.Request,
    form_data: FormData,
    filename: str,
) -> tuple[int, dict]:
    """Calls the API with the provided parameters.

    This function can be executed in parallel using e.g ProcessPoolExecutor.

    Args:
        client: The HTTP client.
        page: A tuple containing the page content and page number.
        request: The prepared request object.
        form_data: The form data to include in the request.
        filename: The name of the original file.

    Returns:
        The response from the API.

    """
    if client is None:
        raise RuntimeError("HTTP client not accessible!")

    page_content, page_number = page
    new_request = create_httpx_request(request, form_data, page_content, filename, page_number)

    try:
        response = await client.send(new_request)
        return response.status_code, response.json()
    except Exception:
        logger.error("Failed to send request for page %d", page_number)
        return 500, {}


def prepare_request_headers(headers: Headers) -> Headers:
    """Prepare the request headers by removing the 'Content-Type' and 'Content-Length' headers.

    Note: httpx uses CaseInsensitiveDict for headers.

    Args:
        headers: The original request headers.

    Returns:
        The modified request headers.
    """
    headers = Headers(headers)
    headers.pop("Content-Type", None)
    headers.pop("Content-Length", None)
    return headers


def prepare_request_payload(form_data: FormData) -> FormData:
    """Prepares the request payload by removing unnecessary keys and updating the file.

    Args:
        form_data: The original form data.

    Returns:
        The updated request payload.
    """
    payload = copy.deepcopy(form_data)
    payload.pop(PARTITION_FORM_SPLIT_PDF_PAGE_KEY, None)
    payload.pop(PARTITION_FORM_FILES_KEY, None)
    payload.pop(PARTITION_FORM_STARTING_PAGE_NUMBER_KEY, None)
    updated_parameters = {
        PARTITION_FORM_SPLIT_PDF_PAGE_KEY: "false",
    }
    payload.update(updated_parameters)
    return payload


def get_optimal_split_size(num_pages: int, concurrency_level: int) -> int:
    """Distributes pages to workers evenly based on the number of pages and desired concurrency level."""
    if num_pages < MAX_PAGES_PER_SPLIT * concurrency_level:
        split_size = math.ceil(num_pages / concurrency_level)
    else:
        split_size = MAX_PAGES_PER_SPLIT

    return max(split_size, MIN_PAGES_PER_SPLIT)


import requests


def create_response(response: requests.Response, elements: list) -> requests.Response:
    """
    Creates a modified response object with updated content.

    Args:
        response: The original response object.
        elements: The list of elements to be serialized and added to
        the response.

    Returns:
        The modified response object with updated content.
    """
    response_copy = copy.deepcopy(response)
    content = json.dumps(elements).encode()
    content_length = str(len(content))
    response_copy.headers.update({"Content-Length": content_length})
    setattr(response_copy, "_content", content)
    return response_copy


def create_request(
    request: requests.PreparedRequest,
    form_data: FormData,
    page_content: io.BytesIO,
    filename: str,
    page_number: int,
) -> requests.Request:
    """Creates a request object for a part of a splitted PDF file.

    Args:
        request: The original request object.
        form_data : The form data for the request.
        page_content: Page content in bytes.
        filename: The original filename of the PDF file.
        page_number: Number of the page in the original PDF file.

    Returns:
        The request object for a splitted part of the
        original file.
    """
    headers = request_utils.prepare_request_headers(request.headers)
    payload = request_utils.prepare_request_payload(form_data)
    body = MultipartEncoder(
        fields={
            **payload,
            PARTITION_FORM_FILES_KEY: (
                filename,
                page_content,
                "application/pdf",
            ),
            PARTITION_FORM_STARTING_PAGE_NUMBER_KEY: str(page_number),
        }
    )
    return requests.Request(
        method="POST",
        url=request.url or "",
        data=body,
        headers={**headers, "Content-Type": body.content_type},
    )


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
        self.partition_responses: dict[str, tuple] = {}
        self.elements: dict[str, list] = {}
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

        async def call_api_partial(page):
            async with httpx.AsyncClient() as client:
                return await call_api(
                    client=client,
                    request=request,
                    form_data=form_data,
                    filename=file.file_name,
                    page=page,
                )

        last_page_content = io.BytesIO()
        last_page_number = 0

        tasks = []
        for page_content, page_index, all_pages_number in pages:
            page_number = page_index + starting_page_number
            # Check if this page is the last one
            if page_index == all_pages_number - 1:
                last_page_content = page_content
                last_page_number = page_number
                break
            coroutine = call_api_partial((page_content, page_number))
            tasks.append(coroutine)

        elements = []

        async def gather_tasks():
            return await asyncio.gather(*tasks)

        responses = asyncio.run(gather_tasks())
        for idx, (status_code, json_response) in enumerate(responses):
            if status_code == 200:
                elements.extend(json_response)
        self.elements[operation_id] = elements
        self.partition_responses[operation_id] = responses

        # `before_request` method needs to return a request so we skip sending the last page in parallel
        # and return that last page at the end of this method
        last_page_request = create_request(
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
            response (httpx.Response): The response object returned from the API
            request.

        Returns:
            Union[httpx.Response, Exception]: If requests were run in parallel, a
            combined response object; otherwise, the original response. Can return
            exception if it ocurred during the execution.
        """
        operation_id = hook_ctx.operation_id
        # Because in `before_request` method we skipped sending last page in parallel
        elements = self.elements[operation_id]

        if elements is None:
            return response

        updated_response = create_response(response, elements)
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
        responses = self.partition_responses.get(operation_id)
        elements = self.elements.get(operation_id)

        if elements is None or responses is None:
            return (response, error)

        if len(responses) == 0:
            if error is not None:
                logger.error(error)
            self._clear_operation(operation_id)
            return (response, error)

        # updated_response = create_response(responses[-1], elements)
        self._clear_operation(operation_id)
        # return (updated_response, None)
        return (response, None)

    def _clear_operation(self, operation_id: str) -> None:
        """
        Clears the operation data associated with the given operation ID.

        Args:
            operation_id (str): The ID of the operation to clear.
        """
        self.partition_responses.pop(operation_id, None)
        self.partition_requests.pop(operation_id, None)
        self.elements.pop(operation_id, None)
