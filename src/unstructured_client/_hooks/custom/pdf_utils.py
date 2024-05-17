import io
import logging
from typing import Generator, Tuple

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError

from unstructured_client._hooks.custom.common import UNSTRUCTURED_CLIENT_LOGGER_NAME
from unstructured_client.models import shared

logger = logging.getLogger(UNSTRUCTURED_CLIENT_LOGGER_NAME)


def get_pdf_pages(
    pdf: PdfReader,
    split_size: int = 1,
) -> Generator[Tuple[io.BytesIO, int, int], None, None]:
    """Reads given bytes of a pdf file and split it into n file-like objects, each
    with `split_size` pages.

    Args:
        file_content (bytes): Content of the PDF file.
        split_size (int, optional): Split size, e.g. if the given file has 10 pages
        and this value is set to 2 it will yield 5 documents, each containing 2 pages
        of the original document. By default it will split each page to a separate file.

    Yields:
        Generator[Tuple[io.BytesIO, int, int], None, None]: Yield the file contents with
        their page number and overall pages number of the original document.
    """

    offset = 0
    offset_end = len(pdf.pages)

    while offset < offset_end:
        new_pdf = PdfWriter()
        pdf_buffer = io.BytesIO()

        end = min(offset + split_size, offset_end)

        for page in list(pdf.pages[offset:end]):
            new_pdf.add_page(page)

        new_pdf.write(pdf_buffer)
        pdf_buffer.seek(0)

        yield pdf_buffer, offset, offset_end
        offset += split_size


def is_pdf(file: shared.Files) -> bool:
    """
    Check if the given file is a PDF. First it checks the file extension and if
    it is equal to `.pdf` then it tries to read that file. If there is no error
    then we assume it is a proper PDF.

    Args:
        file (File): The file to be checked.

    Returns:
        bool: True if the file is a PDF, False otherwise.
    """
    if not file.file_name.endswith(".pdf"):
        logger.warning("Given file doesn't have '.pdf' extension. Continuing without splitting.")
        return False

    try:
        PdfReader(io.BytesIO(file.content), strict=True)
    except (PdfReadError, UnicodeDecodeError) as exc:
        logger.error(exc)
        logger.warning(
            "Attempted to interpret file as pdf, but error arose when splitting by pages. "
            "Reverting to non-split pdf handling path."
        )
        return False

    return True
