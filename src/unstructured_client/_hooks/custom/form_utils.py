from __future__ import annotations

import logging
from typing import Union

from requests_toolbelt.multipart.decoder import MultipartDecoder

from unstructured_client._hooks.custom.common import UNSTRUCTURED_CLIENT_LOGGER_NAME
from unstructured_client.models import shared

logger = logging.getLogger(UNSTRUCTURED_CLIENT_LOGGER_NAME)
FormData = dict[str, Union[str, shared.Files]]

PARTITION_FORM_FILES_KEY = "files"
PARTITION_FORM_SPLIT_PDF_PAGE_KEY = "split_pdf_page"
PARTITION_FORM_STARTING_PAGE_NUMBER_KEY = "starting_page_number"
PARTITION_FORM_CONCURRENCY_LEVEL_KEY = "split_pdf_concurrency_level"


def get_starting_page_number(form_data: FormData, key: str, fallback_value: int) -> int:
    """Retrieves the starting page number from the given form data.

    In case given starting page number is not a valid integer or less than 1, it will
    use the default value.

    Args:
        form_data: The form data containing the starting page number.
        key: The key to look for in the form data.
        fallback_value: The default value to use in case of an error.

    Returns:
        The starting page number.
    """
    starting_page_number = fallback_value
    try:
        _starting_page_number = form_data.get(key) or fallback_value
        starting_page_number = int(_starting_page_number)  # type: ignore
    except ValueError:
        logger.warning(
            "'%s' is not a valid integer. Using default value '%d'.",
            key,
            fallback_value,
        )

    if starting_page_number < 1:
        logger.warning(
            "'%s' is less than 1. Using default value '%d'.",
            key,
            fallback_value,
        )
        starting_page_number = fallback_value

    return starting_page_number


def get_split_pdf_concurrency_level_param(
    form_data: FormData, key: str, fallback_value: int, max_allowed: int
) -> int:
    """Retrieves the value for concurreny level that should be used for splitting pdf.

    In case given the number is not a valid integer or less than 1, it will use the
    default value.

    Args:
        form_data: The form data containing the desired concurrency level.
        key: The key to look for in the form data.
        fallback_value: The default value to use in case of an error.
        max_allowed: The maximum allowed value for the concurrency level.

    Returns:
        The concurrency level after validation.
    """
    concurrency_level_str = form_data.get(key)

    if concurrency_level_str is None:
        return fallback_value

    try:
        concurrency_level = int(concurrency_level_str)
    except ValueError:
        logger.warning(
            "'%s' is not a valid integer. Using default value '%s'.",
            key,
            fallback_value,
        )
        return fallback_value

    if concurrency_level < 1:
        logger.warning(
            "'%s' is less than 1. Using the default value = %s.",
            key,
            fallback_value,
        )
        return fallback_value

    if concurrency_level > max_allowed:
        logger.warning(
            "'%s' is greater than %s. Using the maximum allowed value = %s.",
            key,
            max_allowed,
            max_allowed,
        )
        return max_allowed

    return concurrency_level


def decode_content_disposition(content_disposition: bytes) -> dict[str, str]:
    """Decode the `Content-Disposition` header and return the parameters as a dictionary.

    Args:
        content_disposition: The `Content-Disposition` header as bytes.

    Returns:
        A dictionary containing the parameters extracted from the
        `Content-Disposition` header.
    """
    data = content_disposition.decode().split("; ")[1:]
    parameters = [d.split("=") for d in data]
    parameters_dict = {p[0]: p[1].strip('"') for p in parameters}
    return parameters_dict


def parse_form_data(decoded_data: MultipartDecoder) -> FormData:
    """Parses the form data from the decoded multipart data.

    Args:
        decoded_data: The decoded multipart data.

    Returns:
        The parsed form data.
    """
    form_data: FormData = {}

    for part in decoded_data.parts:
        content_disposition = part.headers.get(b"Content-Disposition")
        if content_disposition is None:
            raise RuntimeError("Content-Disposition header not found. Can't split pdf file.")
        part_params = decode_content_disposition(content_disposition)
        name = part_params.get("name")

        if name is None:
            continue

        if name == PARTITION_FORM_FILES_KEY:
            filename = part_params.get("filename")
            if filename is None or not filename.strip():
                raise ValueError("Filename can't be an empty string.")
            form_data[PARTITION_FORM_FILES_KEY] = shared.Files(part.content, filename)
        else:
            form_data[name] = part.content.decode()

    return form_data
