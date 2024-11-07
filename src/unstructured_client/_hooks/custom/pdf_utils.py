from __future__ import annotations

import io
import logging
from typing import cast, Optional, BinaryIO, Union

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from unstructured_client._hooks.custom.common import UNSTRUCTURED_CLIENT_LOGGER_NAME

logger = logging.getLogger(UNSTRUCTURED_CLIENT_LOGGER_NAME)

# Loading pdfs with strict=False can dump a lot of warnings
# We don't need to display these
pdf_logger = logging.getLogger("pypdf")
pdf_logger.setLevel(logging.ERROR)

def read_pdf(pdf_file: Union[BinaryIO, bytes]) -> Optional[PdfReader]:
    """Reads the given PDF file.

    Args:
        pdf_file: The PDF file to be read.

    Returns:
        The PdfReader object if the file is a PDF, None otherwise.
    """

    try:
        if isinstance(pdf_file, bytes):
            content = cast(bytes, pdf_file)
            pdf_file = io.BytesIO(content)
        return PdfReader(pdf_file, strict=False)
    except (PdfReadError, UnicodeDecodeError):
        return None
