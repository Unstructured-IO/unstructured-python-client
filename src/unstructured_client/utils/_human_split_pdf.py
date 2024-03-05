import copy
import io
import logging
import os
import functools
from typing import Optional, Tuple, Callable, Any, List
from concurrent.futures import ThreadPoolExecutor

import pypdf
from pypdf import PdfReader, PdfWriter

from unstructured_client import utils
from unstructured_client.models import errors  # pylint: disable=C0415
from unstructured_client.models import shared, operations

logger = logging.getLogger('unstructured-client')

SELF_ARG_IDX = 0
REQUEST_ARG_IDX = 1
RETRIES_ARG_IDX = 2


def handle_split_pdf_page(func: Callable) -> Callable:
    """
    A decorator for splitting PDF by pages and sending each of them separately to backend.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> operations.PartitionResponse:
        if len(args) > 1:
            request = args[REQUEST_ARG_IDX]
        elif kwargs.get("request"):
            request = kwargs.get("request")
        else:
            raise ValueError("Expected a request argument for the partition function.")

        is_pdf_by_extension = request.files.file_name.endswith(".pdf") if request.files.file_name else False
        split_pdf_page = request.split_pdf_page and is_pdf_by_extension
        if not split_pdf_page:
            return func(*args, **kwargs)

        try:
            PdfReader(io.BytesIO(request.files.content), strict=True)
        except (pypdf.errors.PdfReadError, UnicodeDecodeError) as exc:
            logger.error(exc)
            logger.warning("Attempted to interpret file as pdf, but error arose when splitting by pages. "
                           "Reverting to non-split pdf handling path.")
            return func(*args, **kwargs)

        pages = get_pdf_pages(request.files.content)
        call_threads = get_split_pdf_call_threads()

        self = args[SELF_ARG_IDX]
        if len(args) > 2:
            retries = args[RETRIES_ARG_IDX]
        elif kwargs.get("retries"):
            retries = kwargs.get("retries")
        else:
            retries = None

        call_api_partial = functools.partial(
            call_api,
            func=func,
            self=self,
            request=request,
            retries=retries
        )

        results: List[operations.PartitionResponse] = []
        with ThreadPoolExecutor(max_workers=call_threads) as executor:
            for result in executor.map(call_api_partial, pages):
                results.append(result)

        if all(result.status_code != 200 for result in results):
            response = operations.PartitionResponse(
                raw_response=results[0].raw_response,
                status_code=results[0].status_code,
                elements=[],
                content_type=results[0].content_type,
            )
            return response

        first_success = next((result for result in results if result.status_code == 200))
        flattened_elements = [element for response in results
                              if response.status_code == 200 for element in response.elements]

        # Lax error handling - at least one call success means success for whole function.
        response = operations.PartitionResponse(
            raw_response=first_success.raw_response,
            status_code=200,
            elements=flattened_elements,
            content_type=first_success.content_type,
        )
        return response

    return wrapper


def call_api(
        page_tuple: Tuple[io.BytesIO, int],
        func: Callable,
        self: Any,
        request: Optional[shared.PartitionParameters],
        retries: Optional[utils.RetryConfig] = None) -> operations.PartitionResponse:
    """
    Given a single pdf file, send the bytes to the Unstructured api.

    Self is General, but can't use type here because of circular imports. The rest of parameters are like in partition().
    When we get the result, replace the page numbers in the metadata (since everything will come back as page 1).
    Deep-copying is needed to avoid race condition risk, in case some of the variables would be modified by many threads.
    """

    page_content = page_tuple[0]
    page_number = page_tuple[1]
    new_request = copy.deepcopy(request)
    new_request.files.content = page_content
    new_retries = copy.deepcopy(retries)
    new_self = copy.deepcopy(self)

    try:
        result = func(new_self, new_request, new_retries)
        if result.status_code == 200:
            for element in result.elements:
                element["metadata"]["page_number"] = page_number
        return result

    except errors.SDKError as err:
        logger.error(err)

        result = operations.PartitionResponse(
            status_code=err.status_code,
            raw_response=err.raw_response,
            content_type=err.raw_response.headers.get('Content-Type'),
            elements=[],
        )
        return result


def get_pdf_pages(file_content: bytes, split_size: int = 1) -> Tuple[io.BytesIO, int]:
    """
    Given a path to a pdf, open the pdf and split it into n file-like objects, each with split_size pages.

    Yield the files with their page number in the int element of result tuple.
    """

    pdf = PdfReader(io.BytesIO(file_content))
    offset = 0

    while offset < len(pdf.pages):
        new_pdf = PdfWriter()
        pdf_buffer = io.BytesIO()

        end = offset + split_size
        for page in list(pdf.pages[offset:end]):
            new_pdf.add_page(page)

        new_pdf.write(pdf_buffer)
        pdf_buffer.seek(0)

        # 1-index the page numbers
        yield pdf_buffer, offset+1
        offset += split_size


def get_split_pdf_call_threads() -> int:
    """
    Read from os envs the number of threads that should be used for splitting pdf on client side.
    """
    max_threads = 15
    try:
        call_threads = int(os.getenv("UNSTRUCTURED_CLIENT_SPLIT_CALL_THREADS", "5"))
    except ValueError:
        call_threads = 5
        logger.error("UNSTRUCTURED_CLIENT_SPLIT_CALL_THREADS has invalid value.")
    if call_threads > max_threads:
        logger.warning("Clipping UNSTRUCTURED_CLIENT_SPLIT_CALL_THREADS to %d.", max_threads)
        call_threads = max_threads
    logger.info("Splitting PDF by page on client. Using %d threads when calling API.", call_threads)
    logger.info("Set UNSTRUCTURED_CLIENT_SPLIT_CALL_THREADS env var if you want to change that.")
    return call_threads
