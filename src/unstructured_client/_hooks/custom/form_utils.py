from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from typing_extensions import TypeAlias

from requests_toolbelt.multipart.decoder import MultipartDecoder  # type: ignore

from unstructured_client._hooks.custom.common import UNSTRUCTURED_CLIENT_LOGGER_NAME
from unstructured_client.models import shared

if TYPE_CHECKING:
    from typing import Union

logger = logging.getLogger(UNSTRUCTURED_CLIENT_LOGGER_NAME)
FormData: TypeAlias = "dict[str, Union[str, shared.Files, list[str]]]"

PARTITION_FORM_FILES_KEY = "files"
PARTITION_FORM_SPLIT_PDF_PAGE_KEY = "split_pdf_page"
PARTITION_FORM_PAGE_RANGE_KEY = "split_pdf_page_range[]"
PARTITION_FORM_SPLIT_PDF_ALLOW_FAILED_KEY = "split_pdf_allow_failed"
PARTITION_FORM_STARTING_PAGE_NUMBER_KEY = "starting_page_number"
PARTITION_FORM_CONCURRENCY_LEVEL_KEY = "split_pdf_concurrency_level"


def get_page_range(form_data: FormData, key: str, max_pages: int) -> tuple[int, int]:
    """Retrieves the split page range from the given form data.

    If the range is invalid or outside the bounds of the page count,
    returns (1, num_pages), i.e. the full range.

    Args:
        form_data: The form data containing the page range
        key: The key to look for in the form data.

    Returns:
        The range of pages to send in the request in the form (start, end)
    """
    _page_range = None
    try:
        _page_range = form_data.get(key)

        if isinstance(_page_range, list):
            page_range = (int(_page_range[0]), int(_page_range[1]))
        else:
            page_range = (1, max_pages)

    except (ValueError, IndexError) as exc:
        msg = f"{_page_range} is not a valid page range."
        logger.error(msg)
        raise ValueError(msg) from exc

    start, end = page_range

    if not 0 < start <= max_pages or not 0 < end <= max_pages or not start <= end:
        msg = f"Page range {page_range} is out of bounds. Start and end values should be between 1 and {max_pages}."
        logger.error(msg)
        raise ValueError(msg)

    return page_range


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

def get_split_pdf_allow_failed_param(
    form_data: FormData, key: str, fallback_value: bool,
) -> bool:
    """Retrieves the value for allow failed that should be used for splitting pdf.

    In case given the number is not a "false" or "true" literal, it will use the
    default value.

    Args:
        form_data: The form data containing the desired concurrency level.
        key: The key to look for in the form data.
        fallback_value: The default value to use in case of an error.

    Returns:
        The concurrency level after validation.
    """
    allow_failed = form_data.get(key)

    if not isinstance(allow_failed, str):
        return fallback_value

    if allow_failed.lower() not in ["true", "false"]:
        logger.warning(
            "'%s' is not a valid boolean. Using default value '%s'.",
            key,
            fallback_value,
        )
        return fallback_value

    return allow_failed.lower() == "true"


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

    if not isinstance(concurrency_level_str, str):
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
        content_disposition = part.headers.get(b"Content-Disposition") # type: ignore
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
            form_data[PARTITION_FORM_FILES_KEY] = shared.Files(content=part.content, file_name=filename)
        else:
            content = part.content.decode()
            if name in form_data:
                form_data_value = form_data[name]
                if isinstance(form_data_value, list):
                    form_data_value.append(content)
                else:
                    new_list = [form_data_value, content]
                    form_data[name] = new_list
            else:
                form_data[name] = content

    return form_data
