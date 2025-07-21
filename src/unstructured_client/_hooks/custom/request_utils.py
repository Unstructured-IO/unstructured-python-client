from __future__ import annotations

import asyncio
import io
import json
import logging
from typing import Tuple, Any, BinaryIO
from urllib.parse import urlparse

import httpx
from httpx import URL
from httpx._multipart import DataField, FileField

from unstructured_client._hooks.custom.common import UNSTRUCTURED_CLIENT_LOGGER_NAME
from unstructured_client._hooks.custom.form_utils import (
    PARTITION_FORM_FILES_KEY,
    PARTITION_FORM_SPLIT_PDF_PAGE_KEY,
    PARTITION_FORM_SPLIT_PDF_ALLOW_FAILED_KEY,
    PARTITION_FORM_SPLIT_CACHE_TMP_DATA_KEY,
    PARTITION_FORM_SPLIT_CACHE_TMP_DATA_DIR_KEY,
    PARTITION_FORM_PAGE_RANGE_KEY,
    PARTITION_FORM_STARTING_PAGE_NUMBER_KEY,
    FormData,
)
from unstructured_client.models import shared
from unstructured_client.utils import (
    BackoffStrategy,
    Retries,
    RetryConfig,
    retry_async,
    serialize_request_body,
)

logger = logging.getLogger(UNSTRUCTURED_CLIENT_LOGGER_NAME)


def get_multipart_stream_fields(request: httpx.Request) -> dict[str, Any]:
    """Extracts the multipart fields from the request.

    Args:
        request: The request object.

    Returns:
        The multipart fields.

    Raises:
        Exception: If the filename is not set
    """
    content_type = request.headers.get("Content-Type", "")
    if "multipart" not in content_type:
        return {}
    if request.stream is None or not hasattr(request.stream, "fields"):
        return {}
    fields = request.stream.fields

    mapped_fields: dict[str, Any] = {}
    for field in fields:
        if isinstance(field, DataField):
            if "[]" in field.name:
                name = field.name.replace("[]", "")
                if name not in mapped_fields:
                    mapped_fields[name] = []
                mapped_fields[name].append(field.value)
            mapped_fields[field.name] = field.value
        elif isinstance(field, FileField):
            if field.filename is None or not field.filename.strip():
                raise ValueError("Filename can't be an empty string.")
            mapped_fields[field.name] = {
                "filename": field.filename,
                "content_type": field.headers.get("Content-Type", ""),
                "file": field.file,
            }
    return mapped_fields


def create_pdf_chunk_request_params(
    form_data: FormData, page_number: int
) -> dict[str, Any]:
    """Creates the request body for the partition API."

    Args:
        form_data: The form data.
        page_number: The page number.

    Returns:
        The updated request payload for the chunk.
    """
    fields_to_drop = [
        PARTITION_FORM_SPLIT_PDF_PAGE_KEY,
        PARTITION_FORM_SPLIT_PDF_ALLOW_FAILED_KEY,
        PARTITION_FORM_FILES_KEY,
        PARTITION_FORM_PAGE_RANGE_KEY,
        PARTITION_FORM_PAGE_RANGE_KEY.replace("[]", ""),
        PARTITION_FORM_STARTING_PAGE_NUMBER_KEY,
        PARTITION_FORM_SPLIT_CACHE_TMP_DATA_KEY,
        PARTITION_FORM_SPLIT_CACHE_TMP_DATA_DIR_KEY,
    ]
    chunk_payload = {
        key: form_data[key] for key in form_data if key not in fields_to_drop
    }
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
        pdf_chunk: Tuple of pdf chunk contents (can be both io.BytesIO or
            a file object created with e.g. open()) and the page number.
        original_request: The original request.
        filename: The filename.

    Returns:
        The updated request object.
    """
    pdf_chunk_file, page_number = pdf_chunk
    data = create_pdf_chunk_request_params(form_data, page_number)
    original_headers = prepare_request_headers(original_request.headers)

    pdf_chunk_content: BinaryIO | bytes = (
        pdf_chunk_file.getvalue()
        if isinstance(pdf_chunk_file, io.BytesIO)
        else pdf_chunk_file
    )

    pdf_chunk_partition_params = shared.PartitionParameters(
        files=shared.Files(
            content=pdf_chunk_content,
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
    if serialized_body is None:
        raise ValueError("Failed to serialize the request body.")
    return httpx.Request(
        method="POST",
        url=original_request.url or "",
        headers={**original_headers},
        content=serialized_body.content,
        data=serialized_body.data,
        files=serialized_body.files,
    )


async def call_api_async(
    client: httpx.AsyncClient,
    pdf_chunk_request: httpx.Request,
    pdf_chunk_file: BinaryIO,
    limiter: asyncio.Semaphore,
) -> httpx.Response:
    one_second = 1000
    one_minute = 1000 * 60

    retry_config = RetryConfig(
        "backoff",
        BackoffStrategy(
            initial_interval=one_second * 3,
            max_interval=one_minute * 12,
            max_elapsed_time=one_minute * 30,
            exponent=1.88,
        ),
        retry_connection_errors=True,
    )

    retryable_codes = ["5xx"]

    async def do_request():
        return await client.send(pdf_chunk_request)

    async with limiter:
        try:
            response = await retry_async(
                do_request, Retries(retry_config, retryable_codes)
            )
            return response
        except Exception as e:
            logger.error("Request failed with error: %s", e, exc_info=e)
            raise e
        finally:
            if not isinstance(pdf_chunk_file, io.BytesIO) and not pdf_chunk_file.closed:
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


def create_response(elements: list) -> httpx.Response:
    """
    Creates a modified response object with updated content.

    Args:
        elements: The list of elements to be serialized and added to
        the response.

    Returns:
        The modified response object with updated content.
    """
    response = httpx.Response(
        status_code=200, headers={"Content-Type": "application/json"}
    )
    content = json.dumps(elements).encode()
    content_length = str(len(content))
    response.headers.update({"Content-Length": content_length})
    setattr(response, "_content", content)
    return response


def get_base_url(url: str | URL) -> str:
    """Extracts the base URL from the given URL.

    Args:
        url: The URL.

    Returns:
        The base URL.
    """
    parsed_url = urlparse(str(url))
    return f"{parsed_url.scheme}://{parsed_url.netloc}"
