from __future__ import annotations

import io
import logging
from typing import cast

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from unstructured_client._hooks.custom.common import UNSTRUCTURED_CLIENT_LOGGER_NAME
from unstructured_client.models import shared

logger = logging.getLogger(UNSTRUCTURED_CLIENT_LOGGER_NAME)

# Loading pdfs with strict=False can dump a lot of warnings
# We don't need to display these
pdf_logger = logging.getLogger("pypdf")
pdf_logger.setLevel(logging.ERROR)



def is_pdf(file: shared.Files) -> bool:
    """Checks if the given file is a PDF.

    Tries to read that file. If there is no error then we assume it is a proper PDF.

    Args:
        file: The file to be checked.

    Returns:
        True if the file is a PDF, False otherwise.
    """

    try:
        content = cast(bytes, file.content)
        PdfReader(io.BytesIO(content), strict=True)
    except (PdfReadError, UnicodeDecodeError):
        return False

    return True
