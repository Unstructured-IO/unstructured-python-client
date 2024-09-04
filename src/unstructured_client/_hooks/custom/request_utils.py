from __future__ import annotations

import asyncio
import copy
import io
import json
import logging
from typing import Tuple, Any

import httpx
from requests_toolbelt.multipart.encoder import MultipartEncoder  # type: ignore

from unstructured_client._hooks.custom.common import UNSTRUCTURED_CLIENT_LOGGER_NAME
from unstructured_client._hooks.custom.form_utils import (
    PARTITION_FORM_FILES_KEY,
    PARTITION_FORM_SPLIT_PDF_PAGE_KEY,
    PARTITION_FORM_SPLIT_PDF_ALLOW_FAILED_KEY,
    PARTITION_FORM_PAGE_RANGE_KEY,
    PARTITION_FORM_STARTING_PAGE_NUMBER_KEY,
    FormData,
)
import unstructured_client.utils as utils

logger = logging.getLogger(UNSTRUCTURED_CLIENT_LOGGER_NAME)


def create_request_body(
    form_data: FormData, page_content: io.BytesIO, filename: str, page_number: int
) -> MultipartEncoder:
    payload = prepare_request_payload(form_data)

    payload_fields:  list[tuple[str, Any]] = []
    for key, value in payload.items():
        if isinstance(value, list):
            payload_fields.extend([(key, list_value) for list_value in value])
        else:
            payload_fields.append((key, value))

    payload_fields.append((PARTITION_FORM_FILES_KEY, (
        filename,
        page_content,
        "application/pdf",
    )))

    payload_fields.append((PARTITION_FORM_STARTING_PAGE_NUMBER_KEY, str(page_number)))

    body = MultipartEncoder(
        fields=payload_fields
    )
    return body


async def call_api_async(
    client: httpx.AsyncClient,
    page: Tuple[io.BytesIO, int],
    original_request: httpx.Request,
    form_data: FormData,
    filename: str,
    limiter: asyncio.Semaphore,
) -> httpx.Response:
    page_content, page_number = page
    body = create_request_body(form_data, page_content, filename, page_number)
    original_headers = prepare_request_headers(original_request.headers)

    new_request = httpx.Request(
        method="POST",
        url=original_request.url or "",
        content=body.to_string(),
        headers={**original_headers, "Content-Type": body.content_type},
    )

    async with limiter:
        response = await send_request_async_with_retries(client, new_request)
        return response


async def send_request_async_with_retries(client: httpx.AsyncClient, request: httpx.Request):
    # Hardcode the retry config until we can
    # properly reuse the SDK logic
    # (Values are in ms)
    retry_config = utils.RetryConfig(
        "backoff",
        utils.BackoffStrategy(
            initial_interval=3000,  # 3 seconds
            max_interval=1000 * 60 * 12,  # 12 minutes
            exponent=1.88, 
            max_elapsed_time=1000 * 60 * 30  # 30 minutes
        ),
        retry_connection_errors=True
    )

    retryable_codes = [
        "502",
        "503",
        "504"
    ]

    async def do_request():
        return await client.send(request)

    response = await utils.retry_async(
        do_request,
        utils.Retries(retry_config, retryable_codes)
    )

    return response


def prepare_request_headers(
    headers: httpx.Headers,
) -> httpx.Headers:
    """Prepare the request headers by removing the 'Content-Type' and 'Content-Length' headers.

    Args:
        headers: The original request headers.

    Returns:
        The modified request headers.
    """
    new_headers = headers.copy()
    new_headers.pop("Content-Type", None)
    new_headers.pop("Content-Length", None)
    return new_headers


def prepare_request_payload(form_data: FormData) -> FormData:
    """Prepares the request payload by removing unnecessary keys and updating the file.

    Args:
        form_data: The original form data.

    Returns:
        The updated request payload.
    """
    payload = copy.deepcopy(form_data)
    payload.pop(PARTITION_FORM_SPLIT_PDF_PAGE_KEY, None)
    payload.pop(PARTITION_FORM_SPLIT_PDF_ALLOW_FAILED_KEY, None)
    payload.pop(PARTITION_FORM_FILES_KEY, None)
    payload.pop(PARTITION_FORM_PAGE_RANGE_KEY, None)
    payload.pop(PARTITION_FORM_STARTING_PAGE_NUMBER_KEY, None)
    updated_parameters = {
        PARTITION_FORM_SPLIT_PDF_PAGE_KEY: "false",
    }
    payload.update(updated_parameters)
    return payload


def create_response(elements: list) -> httpx.Response:
    """
    Creates a modified response object with updated content.

    Args:
        elements: The list of elements to be serialized and added to
        the response.

    Returns:
        The modified response object with updated content.
    """
    response = httpx.Response(status_code=200, headers={"Content-Type": "application/json"})
    content = json.dumps(elements).encode()
    content_length = str(len(content))
    response.headers.update({"Content-Length": content_length})
    setattr(response, "_content", content)
    return response
