import logging
from typing import Optional, Tuple, Union

import requests

from unstructured_client._hooks.custom.common import UNSTRUCTURED_CLIENT_LOGGER_NAME
from unstructured_client._hooks.types import (
    AfterErrorContext,
    AfterErrorHook,
    SDKInitHook,
)

logger = logging.getLogger(UNSTRUCTURED_CLIENT_LOGGER_NAME)


class LogRetriesAfterErrorHook(AfterErrorHook, SDKInitHook):
    """Hook providing visibility to users when the client retries requests"""

    def log_retries(self, response: Optional[requests.Response]):
        """Log retries to give users visibility into requests."""

        if response is not None and response.status_code // 100 == 5:
            logger.info("Failed to process a request due to API server error with status code %d."
                        "Sleeping before retry.",
                        response.status_code)
            if response.text:
                logger.info("Server message - %s", response.text)

    def sdk_init(
        self, base_url: str, client: requests.Session
    ) -> Tuple[str, requests.Session]:
        return base_url, client

    def after_error(
        self,
        hook_ctx: AfterErrorContext,
        response: Optional[requests.Response],
        error: Optional[Exception],
    ) -> Union[Tuple[Optional[requests.Response], Optional[Exception]], Exception]:
        """Concrete implementation for AfterErrorHook."""
        self.log_retries(response)
        return response, error
