from __future__ import annotations

import copy
import functools
import io
import json
import logging
import math
import os
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Optional, Tuple, Union, Generator

import requests
from requests.structures import CaseInsensitiveDict
from requests_toolbelt.multipart.decoder import MultipartDecoder
from requests_toolbelt.multipart.encoder import MultipartEncoder
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError

from unstructured_client._hooks.custom.common import UNSTRUCTURED_CLIENT_LOGGER_NAME
from unstructured_client._hooks.types import (
    BeforeRequestContext,
    AfterSuccessContext,
    AfterErrorContext,
    SDKInitHook,
    BeforeRequestHook,
    AfterSuccessHook,
    AfterErrorHook,
)
from unstructured_client.models import shared

logger = logging.getLogger(UNSTRUCTURED_CLIENT_LOGGER_NAME)

PARTITION_FORM_FILES_KEY = "files"
PARTITION_FORM_SPLIT_PDF_PAGE_KEY = "split_pdf_page"
PARTITION_FORM_STARTING_PAGE_NUMBER_KEY = "starting_page_number"
PARTITION_FORM_NUM_THREADS_KEY = "split_pdf_threads"

DEFAULT_STARTING_PAGE_NUMBER = 1
DEFAULT_NUM_THREADS = 5
MAX_THREADS = 15
MIN_PAGES_PER_THREAD = 2
MAX_PAGES_PER_THREAD = 20


FormData = dict[str, Union[str, shared.Files]]


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
        form_data = self._parse_form_data(decoded_body)
        split_pdf_page = form_data.get(PARTITION_FORM_SPLIT_PDF_PAGE_KEY)
        if split_pdf_page is None or split_pdf_page == "false":
            return request

        file = form_data.get(PARTITION_FORM_FILES_KEY)
        if file is None or not isinstance(file, shared.Files) or not self._is_pdf(file):
            return request

        starting_page_number = self._get_starting_page_number(form_data)
        call_threads = self._get_split_pdf_call_threads(form_data)

        pdf = PdfReader(io.BytesIO(file.content))
        split_size = self._get_optimal_split_size(
            num_pages=len(pdf.pages), num_threads=call_threads
        )
        pages = self._get_pdf_pages(pdf, split_size)

        call_api_partial = functools.partial(
            self._call_api,
            request=request,
            form_data=form_data,
            filename=file.file_name,
        )
        self.partition_requests[operation_id] = []
        last_page_content = io.BytesIO()
        last_page_number = 0
        with ThreadPoolExecutor(max_workers=call_threads) as executor:
            for page_content, page_index, all_pages_number in pages:
                page_number = page_index + starting_page_number
                # Check if this page is the last one
                if page_index == all_pages_number - 1:
                    last_page_content = page_content
                    last_page_number = page_number
                    break
                self.partition_requests[operation_id].append(
                    executor.submit(call_api_partial, (page_content, page_number))
                )

        # `before_request` method needs to return a request so we skip sending the last page in parallel
        # and return that last page at the end of this method
        last_page_request = self._create_request(
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

        updated_response = self._create_response(response, elements)
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

        updated_response = self._create_response(responses[0], elements)
        self._clear_operation(operation_id)
        return (updated_response, None)

    def _is_pdf(self, file: shared.Files) -> bool:
        """
        Check if the given file is a PDF. First it checks the file extension and if
        it is equal to `.pdf` then it tries to read that file. If there is no error
        then we assume it is a proper PDF.

        Args:
            file (File): The file to be checked.

        Returns:
            bool: True if the file is a PDF, False otherwise.
        """
        if not file.file_name.endswith(".pdf"):
            logger.warning(
                "Given file doesn't have '.pdf' extension. Continuing without splitting."
            )
            return False

        try:
            PdfReader(io.BytesIO(file.content), strict=True)
        except (PdfReadError, UnicodeDecodeError) as exc:
            logger.error(exc)
            logger.warning(
                "Attempted to interpret file as pdf, but error arose when splitting by pages. "
                "Reverting to non-split pdf handling path."
            )
            return False

        return True

    def _get_optimal_split_size(self, num_pages: int, num_threads: int) -> int:
        """Distributes pages to threads evenly based on the number of pages and threads."""
        if num_pages < MAX_PAGES_PER_THREAD * num_threads:
            split_size = math.ceil(num_pages / num_threads)
        else:
            split_size = MAX_PAGES_PER_THREAD

        return max(split_size, MIN_PAGES_PER_THREAD)

    def _get_pdf_pages(
        self,
        pdf: PdfReader,
        split_size: int = 1,
    ) -> Generator[Tuple[io.BytesIO, int, int], None, None]:
        """Reads given bytes of a pdf file and split it into n file-like objects, each
        with `split_size` pages.

        Args:
            file_content (bytes): Content of the PDF file.
            split_size (int, optional): Split size, e.g. if the given file has 10 pages
            and this value is set to 2 it will yield 5 documents, each containing 2 pages
            of the original document. By default it will split each page to a separate file.

        Yields:
            Generator[Tuple[io.BytesIO, int, int], None, None]: Yield the file contents with
            their page number and overall pages number of the original document.
        """

        offset = 0
        offset_end = len(pdf.pages)

        while offset < offset_end:
            new_pdf = PdfWriter()
            pdf_buffer = io.BytesIO()

            end = min(offset + split_size, offset_end)

            for page in list(pdf.pages[offset:end]):
                new_pdf.add_page(page)

            new_pdf.write(pdf_buffer)
            pdf_buffer.seek(0)

            yield pdf_buffer, offset, offset_end
            offset += split_size

    def _parse_form_data(self, decoded_data: MultipartDecoder) -> FormData:
        """
        Parses the form data from the decoded multipart data.

        Args:
            decoded_data (MultipartDecoder): The decoded multipart data.

        Returns:
            FormData: The parsed form data.
        """
        form_data: FormData = {}

        for part in decoded_data.parts:
            content_disposition = part.headers.get(b"Content-Disposition")
            if content_disposition is None:
                raise RuntimeError(
                    "Content-Disposition header not found. Can't split pdf file."
                )
            part_params = self._decode_content_disposition(content_disposition)
            name = part_params.get("name")

            if name is None:
                continue

            if name == PARTITION_FORM_FILES_KEY:
                filename = part_params.get("filename")
                if filename is None or not filename.strip():
                    raise ValueError("Filename can't be an empty string.")
                form_data[PARTITION_FORM_FILES_KEY] = shared.Files(
                    part.content, filename
                )
            else:
                form_data[name] = part.content.decode()

        return form_data

    def _decode_content_disposition(self, content_disposition: bytes) -> dict[str, str]:
        """
        Decode the `Content-Disposition` header and return the parameters as a dictionary.

        Args:
            content_disposition (bytes): The `Content-Disposition` header as bytes.

        Returns:
            dict[str, str]: A dictionary containing the parameters extracted from the
            `Content-Disposition` header.
        """
        data = content_disposition.decode().split("; ")[1:]
        parameters = [d.split("=") for d in data]
        parameters_dict = {p[0]: p[1].strip('"') for p in parameters}
        return parameters_dict

    def _call_api(
        self,
        page: Tuple[io.BytesIO, int],
        request: requests.PreparedRequest,
        form_data: FormData,
        filename: str,
    ) -> requests.Response:
        """
        Calls the API with the provided parameters.

        Args:
            page_content (Tuple[io.BytesIO, int]): A tuple containing the page content and
            page number.
            func (Callable): The function to call the API.
            request (requests.PreparedRequest): The prepared request object.
            form_data (FormData): The form data to include in the request.
            filename (str): The name of the original file.

        Returns:
            requests.Response: The response from the API.

        """
        if self.client is None:
            raise RuntimeError("HTTP client not accessible!")
        page_content, page_number = page

        new_request = self._create_request(
            request, form_data, page_content, filename, page_number
        )
        prepared_request = self.client.prepare_request(new_request)

        try:
            return self.client.send(prepared_request)
        except Exception:
            logger.error("Failed to send request for page %d", page_number)
            return requests.Response()

    def _create_request(
        self,
        request: requests.PreparedRequest,
        form_data: FormData,
        page_content: io.BytesIO,
        filename: str,
        page_number: int,
    ) -> requests.Request:
        """
        Creates a request object for a part of a splitted PDF file.

        Args:
            request (requests.PreparedRequest): The original request object.
            form_data (FormData): The form data for the request.
            page_content (io.BytesIO): Page content in bytes.
            filename (str): The original filename of the PDF file.
            page_number (int): Number of the page in the original PDF file.

        Returns:
            requests.Request: The request object for a splitted part of the
            original file.
        """
        headers = self._prepare_request_headers(request.headers)
        payload = self._prepare_request_payload(form_data)
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

    def _prepare_request_headers(
        self, headers: CaseInsensitiveDict[str]
    ) -> CaseInsensitiveDict[str]:
        """
        Prepare the request headers by removing the 'Content-Type' and
        'Content-Length' headers.

        Args:
            headers (CaseInsensitiveDict[str]): The original request headers.

        Returns:
            CaseInsensitiveDict[str]: The modified request headers.
        """
        headers = copy.deepcopy(headers)
        headers.pop("Content-Type", None)
        headers.pop("Content-Length", None)
        return headers

    def _prepare_request_payload(self, form_data: FormData) -> FormData:
        """
        Prepares the request payload by removing unnecessary keys and updating the
        file.

        Args:
            form_data (FormData): The original form data.

        Returns:
            FormData: The updated request payload.
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

    def _create_response(
        self, response: requests.Response, elements: list
    ) -> requests.Response:
        """
        Creates a modified response object with updated content.

        Args:
            response (requests.Response): The original response object.
            elements (list): The list of elements to be serialized and added to
            the response.

        Returns:
            requests.Response: The modified response object with updated content.
        """
        response_copy = copy.deepcopy(response)
        content = json.dumps(elements).encode()
        content_length = str(len(content))
        response_copy.headers.update({"Content-Length": content_length})
        setattr(response_copy, "_content", content)
        return response_copy

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

    def _get_starting_page_number(self, form_data: FormData) -> int:
        """
        Retrieves the starting page number from the given form data. In case given
        starting page number is not a valid integer or less than 1, it will use the
        default value.

        Args:
            form_data (FormData): The form data containing the starting page number.

        Returns:
            int: The starting page number.
        """
        starting_page_number = DEFAULT_STARTING_PAGE_NUMBER
        try:
            _starting_page_number = (
                form_data.get(PARTITION_FORM_STARTING_PAGE_NUMBER_KEY)
                or DEFAULT_STARTING_PAGE_NUMBER
            )
            starting_page_number = int(_starting_page_number)  # type: ignore
        except ValueError:
            logger.warning(
                "'%s' is not a valid integer. Using default value '%d'.",
                PARTITION_FORM_STARTING_PAGE_NUMBER_KEY,
                DEFAULT_STARTING_PAGE_NUMBER,
            )

        if starting_page_number < 1:
            logger.warning(
                "'%s' is less than 1. Using default value '%d'.",
                PARTITION_FORM_STARTING_PAGE_NUMBER_KEY,
                DEFAULT_STARTING_PAGE_NUMBER,
            )
            starting_page_number = DEFAULT_STARTING_PAGE_NUMBER

        return starting_page_number

    def _get_split_pdf_call_threads(self, form_data: FormData) -> int:
        """Retrieves the number of threads that should be used for splitting pdf.

        In case given the number is not a valid integer or less than 1, it will use the
        default value.

        Args:
            form_data (FormData): The form data containing the number of threads.

        Returns:
            int: The number of threads to use.
        """
        num_threads_str = form_data.get(PARTITION_FORM_NUM_THREADS_KEY)

        if num_threads_str is None:
            return DEFAULT_NUM_THREADS

        try:
            num_threads = int(num_threads_str)
        except ValueError:
            logger.warning(
                f"'{PARTITION_FORM_NUM_THREADS_KEY}' is not a valid integer. "
                f"Using default value '{DEFAULT_NUM_THREADS}'.",
            )
            return DEFAULT_NUM_THREADS

        if num_threads < 1:
            logger.warning(
                f"'{PARTITION_FORM_NUM_THREADS_KEY}' is less than 1. "
                f"Using the default value ={DEFAULT_NUM_THREADS}.",
            )
            return DEFAULT_NUM_THREADS
        elif num_threads > MAX_THREADS:
            logger.warning(
                f"'{PARTITION_FORM_NUM_THREADS_KEY}' is greater than {MAX_THREADS}. "
                f"Using the maximum allowed value ={MAX_THREADS}.",
            )
            return MAX_THREADS

        return num_threads
