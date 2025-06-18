from __future__ import annotations

import io

import pytest
from pypdf import PdfReader

from unstructured_client._hooks.custom.pdf_utils import check_pdf, PDFValidationError
from _test_unstructured_client.unit_utils import sample_docs_path


def _open_pdf(pdf_path: str) -> PdfReader:
    with open(pdf_path, "rb") as f:
        pdf_content = f.read()
    return PdfReader(io.BytesIO(pdf_content))


def test_check_pdf_with_valid_pdf():
    pdf_path = sample_docs_path("list-item-example-1.pdf")
    pdf = _open_pdf(pdf_path)

    result = check_pdf(pdf)
    assert isinstance(result, PdfReader)


@pytest.mark.parametrize(
    ("pdf_name", "expected_error_message"),
    [
        (
            "failing-encrypted.pdf",
            "File is encrypted. Please decrypt it with password.",
        ),
        (
            "failing-missing-root.pdf",
            "File does not appear to be a valid PDF. Error: Cannot find Root object in pdf",
        ),
        (
            "failing-missing-pages.pdf",
            "File does not appear to be a valid PDF. Error: Invalid object in /Pages",
        ),
    ],
)
def test_check_pdf_raises_pdf_validation_error(
    pdf_name: str, expected_error_message: str
):
    """Test that we get a PDFValidationError with the correct error message for invalid PDF files."""
    pdf_path = sample_docs_path(pdf_name)
    pdf = _open_pdf(pdf_path)

    with pytest.raises(PDFValidationError) as exc_info:
        check_pdf(pdf)

    assert exc_info.value.message == expected_error_message
