from __future__ import annotations

import asyncio
import copy
import io
import json
import logging
from typing import Optional, Tuple

import httpx
import requests
from requests.structures import CaseInsensitiveDict
from requests_toolbelt.multipart.encoder import MultipartEncoder

from unstructured_client._hooks.custom.common import UNSTRUCTURED_CLIENT_LOGGER_NAME
from unstructured_client._hooks.custom.form_utils import (
    PARTITION_FORM_FILES_KEY,
    PARTITION_FORM_SPLIT_PDF_PAGE_KEY,
    PARTITION_FORM_STARTING_PAGE_NUMBER_KEY,
    FormData,
)

logger = logging.getLogger(UNSTRUCTURED_CLIENT_LOGGER_NAME)


def create_request_body(
    form_data: FormData, page_content: io.BytesIO, filename: str, page_number: int
) -> MultipartEncoder:
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
    return body


def create_httpx_request(
    original_request: requests.Request, body: MultipartEncoder
) -> httpx.Request:
    headers = prepare_request_headers(original_request.headers)
    return httpx.Request(
        method="POST",
        url=original_request.url or "",
        content=body.to_string(),
        headers={**headers, "Content-Type": body.content_type},
    )


def create_request(
    request: requests.PreparedRequest,
    body: MultipartEncoder,
) -> requests.Request:
    headers = prepare_request_headers(request.headers)
    return requests.Request(
        method="POST",
        url=request.url or "",
        data=body,
        headers={**headers, "Content-Type": body.content_type},
    )


async def call_api_async(
    client: httpx.AsyncClient,
    page: Tuple[io.BytesIO, int],
    original_request: requests.Request,
    form_data: FormData,
    filename: str,
    limiter: asyncio.Semaphore,
) -> tuple[int, dict]:
    page_content, page_number = page
    body = create_request_body(form_data, page_content, filename, page_number)
    new_request = create_httpx_request(original_request, body)
    async with limiter:
        try:
            response = await client.send(new_request)
            return response.status_code, response.json()
        except Exception:
            logger.error("Failed to send request for page %d", page_number)
            return 500, {}


def call_api(
    client: Optional[requests.Session],
    page: Tuple[io.BytesIO, int],
    request: requests.PreparedRequest,
    form_data: FormData,
    filename: str,
) -> requests.Response:
    if client is None:
        raise RuntimeError("HTTP client not accessible!")
    page_content, page_number = page

    body = create_request_body(form_data, page_content, filename, page_number)
    new_request = create_request(request, body)
    prepared_request = client.prepare_request(new_request)

    try:
        return client.send(prepared_request)
    except Exception:
        logger.error("Failed to send request for page %d", page_number)
        return requests.Response()


def prepare_request_headers(
    headers: CaseInsensitiveDict[str],
) -> CaseInsensitiveDict[str]:
    """Prepare the request headers by removing the 'Content-Type' and 'Content-Length' headers.

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


def log_after_split_response(status_code: int, split_number: int):
    if status_code == 200:
        logger.info(
            "Successfully partitioned set #%d, elements added to the final result.",
            split_number,
        )
    else:
        logger.warning(
            "Failed to partition set #%d, its elements will be omitted in the final result.",
            split_number,
        )
