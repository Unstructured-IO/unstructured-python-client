from __future__ import annotations

import copy
import io
import json
import logging
from typing import Optional, Tuple

import requests
from requests.structures import CaseInsensitiveDict
from requests_toolbelt.multipart.decoder import MultipartDecoder
from requests_toolbelt.multipart.encoder import MultipartEncoder

from unstructured_client._hooks.custom.common import UNSTRUCTURED_CLIENT_LOGGER_NAME
from unstructured_client._hooks.custom.form_utils import (
    PARTITION_FORM_FILES_KEY,
    PARTITION_FORM_SPLIT_PDF_PAGE_KEY,
    PARTITION_FORM_STARTING_PAGE_NUMBER_KEY,
    FormData,
)

logger = logging.getLogger(UNSTRUCTURED_CLIENT_LOGGER_NAME)


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
    return requests.Request(
        method="POST",
        url=request.url or "",
        data=body,
        headers={**headers, "Content-Type": body.content_type},
    )


def call_api(
    client: Optional[requests.Session],
    page: Tuple[io.BytesIO, int],
    request: requests.PreparedRequest,
    form_data: FormData,
    filename: str,
) -> requests.Response:
    """Calls the API with the provided parameters.

    This function can be executed in parallel using e.g ProcessPoolExecutor.

    Args:
        client: The HTTP client.
        page: A tuple containing the page content and page number.
        request: The prepared request object.
        form_data: The form data to include in the request.
        filename: The name of the original file.

    Returns:
        requests.Response: The response from the API.

    """
    if client is None:
        raise RuntimeError("HTTP client not accessible!")
    page_content, page_number = page
    print(f"Sending request for page {page_number}")

    new_request = create_request(request, form_data, page_content, filename, page_number)
    prepared_request = client.prepare_request(new_request)

    try:
        return client.send(prepared_request)
    except Exception:
        logger.error("Failed to send request for page %d", page_number)
        return requests.Response()


def prepare_request_headers(headers: CaseInsensitiveDict[str]) -> CaseInsensitiveDict[str]:
    """
    Prepare the request headers by removing the 'Content-Type' and
    'Content-Length' headers.

    Args:
        headers: The original request headers.

    Returns:
        The modified request headers.
    """
    headers = copy.deepcopy(headers)
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


def create_response(response: requests.Response, elements: list) -> requests.Response:
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
