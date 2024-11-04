from __future__ import annotations

import io
import logging
from typing import cast, Optional

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from unstructured_client._hooks.custom.common import UNSTRUCTURED_CLIENT_LOGGER_NAME
from unstructured_client.models import shared

logger = logging.getLogger(UNSTRUCTURED_CLIENT_LOGGER_NAME)

# Loading pdfs with strict=False can dump a lot of warnings
# We don't need to display these
pdf_logger = logging.getLogger("pypdf")
pdf_logger.setLevel(logging.ERROR)

def read_pdf(file: shared.Files) -> Optional[PdfReader]:
    """Reads the given PDF file.

    Args:
        file: The PDF file to be read.

    Returns:
        The PdfReader object if the file is a PDF, None otherwise.
    """

    try:
        content = cast(bytes, file.content)
        return PdfReader(io.BytesIO(content), strict=False)
    except (PdfReadError, UnicodeDecodeError):
        return None

def is_pdf(file: shared.Files) -> bool:
    """Checks if the given file is a PDF.

    Tries to read that file. If there is no error then we assume it is a proper PDF.

    Args:
        file: The file to be checked.

    Returns:
        True if the file is a PDF, False otherwise.
    """

    return read_pdf(file) is not None

