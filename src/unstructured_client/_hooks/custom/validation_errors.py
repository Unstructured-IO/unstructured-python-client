"""File validation error classes for the Unstructured client."""

from typing import Optional


class FileValidationError(Exception):
    """Base exception for file validation errors.
    
    This exception should be raised when a file fails validation
    checks before being processed by the API.
    """

    def __init__(self, message: str, file_type: Optional[str] = None):
        self.message: str = message
        self.file_type: Optional[str] = file_type
        super().__init__(self.message)
