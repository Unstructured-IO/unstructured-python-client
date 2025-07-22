from __future__ import annotations

import io
import logging
from typing import cast, Optional, BinaryIO, Union

from pypdf import PdfReader
from pypdf.errors import FileNotDecryptedError, PdfReadError

from unstructured_client._hooks.custom.common import UNSTRUCTURED_CLIENT_LOGGER_NAME
from unstructured_client._hooks.custom.validation_errors import FileValidationError

logger = logging.getLogger(UNSTRUCTURED_CLIENT_LOGGER_NAME)

# Loading pdfs with strict=False can dump a lot of warnings
# We don't need to display these
pdf_logger = logging.getLogger("pypdf")
pdf_logger.setLevel(logging.ERROR)


class PDFValidationError(FileValidationError):
    """Exception for PDF validation errors."""

    def __init__(self, message: str):
        super().__init__(message, file_type="PDF")


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


def check_pdf(pdf: PdfReader) -> PdfReader:
    """
    Check if PDF is:
    - Encrypted
    - Has corrupted pages
    - Has corrupted root object

    Throws:
    - PDFValidationError if file is encrypted or corrupted
    """
    try:
        # This will raise if the file is encrypted
        pdf.metadata  # pylint: disable=pointless-statement

        # This will raise if the file's root object is corrupted
        pdf.root_object  # pylint: disable=pointless-statement

        # This will raise if the file's pages are corrupted
        list(pdf.pages)

        return pdf
    except FileNotDecryptedError as e:
        raise PDFValidationError(
            "File is encrypted. Please decrypt it with password.",
        ) from e
    except PdfReadError as e:
        raise PDFValidationError(
            f"File does not appear to be a valid PDF. Error: {e}",
        ) from e
