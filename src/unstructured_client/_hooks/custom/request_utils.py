from __future__ import annotations

import asyncio
import copy
import json
import logging
from typing import Tuple, Any, BinaryIO

import httpx
from httpx._multipart import MultipartStream
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
from unstructured_client.models import shared
from unstructured_client.utils import BackoffStrategy, Retries, RetryConfig, retry_async, serialize_request_body

logger = logging.getLogger(UNSTRUCTURED_CLIENT_LOGGER_NAME)


def create_pdf_request_body(
    form_data: FormData,
    pdf_chunk: BinaryIO,
    filename: str,
    page_number: int
) -> MultipartEncoder:
    """Creates the request body for the partition API."
    
    Args:
        form_data: The form data.
        pdf_chunk: The pdf chunk - can be both io.BytesIO or a file object (created with open())
        filename: The filename.
        page_number: The page number.
    
    """
    payload = prepare_request_payload(form_data)

    payload_fields:  list[tuple[str, Any]] = []
    for key, value in payload.items():
        if isinstance(value, list):
            payload_fields.extend([(key, list_value) for list_value in value])
        else:
            payload_fields.append((key, value))

    payload_fields.append((PARTITION_FORM_FILES_KEY, (
        filename,
        pdf_chunk,
        "application/pdf",
    )))

    return MultipartEncoder(fields=payload_fields)


def create_pdf_request_data(
        form_data: FormData,
        pdf_chunk: BinaryIO,
        filename: str,
        page_number: int
) -> dict[str, Any]:
    """Creates the request body for the partition API."

    Args:
        form_data: The form data.
        pdf_chunk: The pdf chunk - can be both io.BytesIO or a file object (created with open())
        filename: The filename.
        page_number: The page number.

    """
    payload = prepare_request_payload(form_data)
    payload[PARTITION_FORM_STARTING_PAGE_NUMBER_KEY] = str(page_number)

    # payload[PARTITION_FORM_FILES_KEY] = (
    #     filename,
    #     pdf_chunk,
    #     "application/pdf",
    # )
    #
    # return MultipartEncoder(fields=payload_fields)
    return payload

def prepare_pdf_chunk_request_payload(form_data: FormData) -> FormData:
    """Prepares the request payload by removing unnecessary keys and updating the file.

    Args:
        form_data: The original form data.

    Returns:
        The updated request payload.
    """
    fields_to_drop = [
        PARTITION_FORM_SPLIT_PDF_PAGE_KEY,
        PARTITION_FORM_SPLIT_PDF_ALLOW_FAILED_KEY,
        PARTITION_FORM_FILES_KEY,
        PARTITION_FORM_PAGE_RANGE_KEY,
        PARTITION_FORM_STARTING_PAGE_NUMBER_KEY,
    ]
    chunk_payload = {key: form_data[key] for key in form_data if key not in fields_to_drop}
    chunk_payload[PARTITION_FORM_SPLIT_PDF_PAGE_KEY] = "false"
    return chunk_payload

def create_pdf_chunk_request_data(
        form_data: FormData,
        page_number: int
) -> dict[str, Any]:
    """Creates the request body for the partition API."

    Args:
        form_data: The form data.
        pdf_chunk: The pdf chunk - can be both io.BytesIO or a file object (created with open())
        filename: The filename.
        page_number: The page number.

    """
    fields_to_drop = [
        PARTITION_FORM_SPLIT_PDF_PAGE_KEY,
        PARTITION_FORM_SPLIT_PDF_ALLOW_FAILED_KEY,
        PARTITION_FORM_FILES_KEY,
        PARTITION_FORM_PAGE_RANGE_KEY,
        PARTITION_FORM_STARTING_PAGE_NUMBER_KEY,
    ]
    chunk_payload = {key: form_data[key] for key in form_data if key not in fields_to_drop}
    chunk_payload[PARTITION_FORM_SPLIT_PDF_PAGE_KEY] = "false"
    chunk_payload[PARTITION_FORM_STARTING_PAGE_NUMBER_KEY] = str(page_number)
    return chunk_payload

def create_pdf_chunk_request(
    form_data: FormData,
    pdf_chunk: Tuple[BinaryIO, int],
    original_request: httpx.Request,
    filename: str,
) -> httpx.Request:
    """Creates a new request object with the updated payload for the partition API.

    Args:
        form_data: The form data.
        pdf_chunk: The pdf chunk - can be both io.BytesIO or a file object (created with open())
        original_request: The original request.
        filename: The filename.

    Returns:
        The updated request object.
    """
    pdf_chunk_file, page_number = pdf_chunk
    data = create_pdf_chunk_request_data(form_data, page_number)
    original_headers = prepare_request_headers(original_request.headers)

    pdf_chunk_partition_params = shared.PartitionParameters(
        files=shared.Files(
            content=pdf_chunk_file,
            file_name=filename,
            content_type="application/pdf",
        ),
        **data,
    )
    serialized_body = serialize_request_body(
        pdf_chunk_partition_params,
        False,
        False,
        "multipart",
        shared.PartitionParameters,
    )
    # chunk_request = client.build_request(
    #     method="POST",
    #     url=original_request.url or "",
    #     headers={**original_headers, "Content-Type": "application/pdf"},
    #     files={PARTITION_FORM_FILES_KEY: (filename, pdf_chunk_file, "application/pdf")},
    #     data=data,
    # )
    pdf_chunk_request = httpx.Request(
        method="POST",
        url=original_request.url or "",
        # headers={**original_headers, "Content-Type": serialized_body.media_type},
        headers={**original_headers},
        content=serialized_body.content,
        data=serialized_body.data,
        files=serialized_body.files,
    )
    return pdf_chunk_request



async def call_api_async(
    client: httpx.AsyncClient,
    pdf_chunk_request: httpx.Request,
    pdf_chunk_file: BinaryIO,
    limiter: asyncio.Semaphore,
) -> httpx.Response:
    # pdf_chunk_file, page_number = pdf_chunk
    # body = create_pdf_request_body(form_data, pdf_chunk_file, filename, page_number)
    # original_headers = prepare_request_headers(original_request.headers)

    # new_request = httpx.Request(
    #     method="POST",
    #     url=original_request.url or "",
    #     content=body.to_string(),
    #     headers={**original_headers, "Content-Type": body.content_type},
    # )

    one_second = 1000
    one_minute = 1000 * 60

    retry_config = RetryConfig(
        "backoff",
        BackoffStrategy(
            initial_interval = one_second * 3,
            max_interval = one_minute * 12,
            max_elapsed_time = one_minute * 30,
            exponent = 1.88,
        ),
        retry_connection_errors=True
    )

    retryable_codes = [
        "502",
        "503",
        "504"
    ]

    async def do_request():
        return await client.send(pdf_chunk_request)

    async with limiter:
        try:
            response = await retry_async(
                do_request,
                Retries(retry_config, retryable_codes)
            )
            return response
        except Exception as e:
            print(e)
            raise e
        finally:
            if not pdf_chunk_file.closed:
                pdf_chunk_file.close()


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
