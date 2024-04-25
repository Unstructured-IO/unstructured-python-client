import io
import logging
import os
from concurrent.futures import Future
from unittest import TestCase

import requests
from requests_toolbelt import MultipartDecoder, MultipartEncoder


from unstructured_client._hooks.custom import SplitPdfHook
from unstructured_client.models import shared


class TestSplitPdfHook(TestCase):

    def test_unit_sdk_init(self):
        """Test sdk init method properly sets the client."""
        hook = SplitPdfHook()
        # This is a fake URL, test doesn't make an API call
        test_url = "http://localhost:5000"
        test_client = requests.Session()

        hook.sdk_init(test_url, test_client)

        self.assertEqual(hook.client, test_client)

    def test_unit_clear_operation(self):
        """Test clear operation method properly clears request/response data."""
        hook = SplitPdfHook()
        operation_id = "some_id"
        hook.partition_requests[operation_id] = [Future(), Future()]
        hook.partition_responses[operation_id] = [
            requests.Response(),
            requests.Response(),
        ]

        assert len(hook.partition_requests[operation_id]) == 2
        assert len(hook.partition_responses[operation_id]) == 2

        hook._clear_operation(operation_id)

        assert hook.partition_requests.get(operation_id) is None
        assert hook.partition_responses.get(operation_id) is None

    def test_unit_get_split_pdf_call_threads_default(self):
        """Test get split pdf call threads method returns the right values."""
        hook = SplitPdfHook()

        # Test default value
        assert hook._get_split_pdf_call_threads() == 5

        # Test custom value
        os.environ["UNSTRUCTURED_CLIENT_SPLIT_CALL_THREADS"] = "10"
        assert hook._get_split_pdf_call_threads() == 10

        # Test over limit value
        os.environ["UNSTRUCTURED_CLIENT_SPLIT_CALL_THREADS"] = "20"
        assert hook._get_split_pdf_call_threads() == 15

        # Test negative value
        os.environ["UNSTRUCTURED_CLIENT_SPLIT_CALL_THREADS"] = "-3"
        assert hook._get_split_pdf_call_threads() == 5

    def test_unit_prepare_request_payload(self):
        """Test prepare request payload method properly sets split_pdf_page to 'false'
        and removes files key."""
        hook = SplitPdfHook()
        test_form_data = {
            "files": ("test_file.pdf", b"test_file_content"),
            "split_pdf_page": "true",
            "parameter_1": "value_1",
            "parameter_2": "value_2",
            "parameter_3": "value_3",
        }
        expected_form_data = {
            "split_pdf_page": "false",
            "parameter_1": "value_1",
            "parameter_2": "value_2",
            "parameter_3": "value_3",
        }

        payload = hook._prepare_request_payload(test_form_data)

        self.assertNotEqual(payload, test_form_data)
        self.assertEqual(payload, expected_form_data)

    def test_unit_prepare_request_headers(self):
        """Test prepare request headers method properly removes Content-Type and Content-Length headers."""
        hook = SplitPdfHook()
        test_headers = {
            "Content-Type": "application/json",
            "Content-Length": "100",
            "Authorization": "Bearer token",
        }
        expected_headers = {
            "Authorization": "Bearer token",
        }

        headers = hook._prepare_request_headers(test_headers)

        self.assertNotEqual(headers, test_headers)
        self.assertEqual(headers, expected_headers)

    def test_unit_create_response(self):
        """Test create response method properly overrides body elements and Content-Length header."""
        hook = SplitPdfHook()
        test_elements = [{"key": "value"}, {"key_2": "value"}]
        test_response = requests.Response()
        test_response.status_code = 200
        test_response._content = b'[{"key_2": "value"}]'
        test_response.headers = requests.structures.CaseInsensitiveDict(
            {
                "Content-Type": "application/json",
                "Content-Length": len(test_response._content),
            }
        )

        expected_status_code = 200
        expected_content = b'[{"key": "value"}, {"key_2": "value"}]'
        expected_content_length = "38"

        response = hook._create_response(test_response, test_elements)

        self.assertEqual(response.status_code, expected_status_code)
        self.assertEqual(response._content, expected_content)
        self.assertEqual(
            response.headers.get("Content-Length"), expected_content_length
        )

    def test_unit_create_request(self):
        """Test create request method properly sets file, Content-Type and Content-Length headers."""
        hook = SplitPdfHook()

        # Prepare test data
        request = requests.PreparedRequest()
        request.headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer token",
        }
        form_data = {
            "parameter_1": "value_1",
            "parameter_2": "value_2",
        }
        page = (io.BytesIO(b"page_content"), 1)
        filename = "test_file.pdf"

        # Expected results
        expected_payload = {
            "parameter_1": "value_1",
            "parameter_2": "value_2",
            "split_pdf_page": "false",
        }
        expected_page_filename = "test_file.pdf"
        expected_body = MultipartEncoder(
            fields={
                **expected_payload,
                "files": (
                    expected_page_filename,
                    page[0],
                    "application/pdf",
                ),
            }
        )
        expected_url = ""

        # Create request
        request_obj = hook._create_request(request, form_data, page[0], filename)
        request_content_type: str = request_obj.headers.get("Content-Type")
        # Assert the request object
        self.assertEqual(request_obj.method, "POST")
        self.assertEqual(request_obj.url, expected_url)
        self.assertEqual(request_obj.data.fields, expected_body.fields)
        self.assertTrue(request_content_type.startswith("multipart/form-data"))

    def test_unit_decode_content_disposition(self):
        """Test decode content disposition method properly decodes Content-Disposition header."""
        hook = SplitPdfHook()

        # Test case 1: Single parameter
        content_disposition = b'attachment; filename="test_file.pdf"'
        expected_result = {"filename": "test_file.pdf"}
        result = hook._decode_content_disposition(content_disposition)
        self.assertEqual(result, expected_result)

        # Test case 2: Multiple parameters
        content_disposition = (
            b'attachment; filename="test_file.pdf"; size=100; version="1.0"'
        )
        expected_result = {"filename": "test_file.pdf", "size": "100", "version": "1.0"}
        result = hook._decode_content_disposition(content_disposition)
        self.assertEqual(result, expected_result)

        # Test case 3: No parameters
        content_disposition = b"attachment"
        expected_result = {}
        result = hook._decode_content_disposition(content_disposition)
        self.assertEqual(result, expected_result)

    def test_unit_parse_form_data(self):
        """Test parse form data method properly parses the form data and returns dictionary."""
        hook = SplitPdfHook()

        # Prepare test data
        decoded_data = MultipartDecoder(
            b'--boundary\r\nContent-Disposition: form-data; name="files"; filename="test_file.pdf"\r\n\r\nfile_content\r\n--boundary\r\nContent-Disposition: form-data; name="parameter_1"\r\n\r\nvalue_1\r\n--boundary\r\nContent-Disposition: form-data; name="parameter_2"\r\n\r\nvalue_2\r\n--boundary--\r\n',
            "multipart/form-data; boundary=boundary",
        )

        # Expected results
        expected_form_data = {
            "files": shared.Files(b"file_content", "test_file.pdf"),
            "parameter_1": "value_1",
            "parameter_2": "value_2",
        }

        # Parse form data
        form_data = hook._parse_form_data(decoded_data)

        # Assert the parsed form data
        self.assertEqual(
            form_data.get("parameter_1"), expected_form_data.get("parameter_1")
        )
        self.assertEqual(
            form_data.get("parameter_2"), expected_form_data.get("parameter_2")
        )
        self.assertEqual(
            form_data.get("files").file_name, expected_form_data.get("files").file_name
        )
        self.assertEqual(
            form_data.get("files").content, expected_form_data.get("files").content
        )

    def test_unit_parse_form_data_error(self):
        """Test parse form data method raises RuntimeError when the form data is invalid (no Content-Disposition header)."""
        hook = SplitPdfHook()

        # Prepare test data
        decoded_data = MultipartDecoder(
            b'--boundary\r\nContent: form-data; name="files"; filename="test_file.pdf"\r\n\r\nfile_content\r\n--boundary--\r\n',
            "multipart/form-data; boundary=boundary",
        )

        # Assert RuntimeError
        self.assertRaises(RuntimeError, hook._parse_form_data, decoded_data)

    def test_unit_parse_form_data_empty_filename_error(self):
        """Test parse form data method raises ValueError when the form data has empty filename."""
        hook = SplitPdfHook()

        # Prepare test data
        decoded_data = MultipartDecoder(
            b'--boundary\r\nContent-Disposition: form-data; name="files"; filename=""\r\n\r\nfile_content\r\n--boundary--\r\n',
            "multipart/form-data; boundary=boundary",
        )

        # Assert ValueError
        self.assertRaises(ValueError, hook._parse_form_data, decoded_data)

    def test_unit_parse_form_data_none_filename_error(self):
        """Test parse form data method raises ValueError when the form data has no filename (None)."""
        hook = SplitPdfHook()

        # Prepare test data
        decoded_data = MultipartDecoder(
            b'--boundary\r\nContent-Disposition: form-data; name="files"\r\n\r\nfile_content\r\n--boundary--\r\n',
            "multipart/form-data; boundary=boundary",
        )

        # Assert ValueError
        self.assertRaises(ValueError, hook._parse_form_data, decoded_data)

    def test_unit_is_pdf_valid_pdf(self):
        """Test is pdf method returns True for valid pdf file (has .pdf extension and can be read)."""
        hook = SplitPdfHook()
        filename = "_sample_docs/layout-parser-paper-fast.pdf"

        with open(filename, "rb") as f:
            file = shared.Files(
                content=f.read(),
                file_name=filename,
            )

        result = hook._is_pdf(file)

        self.assertTrue(result)

    def test_unit_is_pdf_invalid_extension(self):
        """Test is pdf method returns False for file with invalid extension."""
        hook = SplitPdfHook()
        file = shared.Files(b"txt_content", "test_file.txt")

        with self.assertLogs(level=logging.WARNING) as cm:
            result = hook._is_pdf(file)

        self.assertFalse(result)
        self.assertIn("Given file doesn't have '.pdf' extension", cm.output[0])

    def test_unit_is_pdf_invalid_pdf(self):
        """Test is pdf method returns False for file with invalid pdf content."""
        hook = SplitPdfHook()
        file = shared.Files(b"invalid_pdf_content", "test_file.pdf")

        with self.assertLogs(level=logging.WARNING) as cm:
            result = hook._is_pdf(file)

        self.assertFalse(result)
        self.assertIn("Attempted to interpret file as pdf", cm.output[1])
