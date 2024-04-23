import logging
import sys
from typing import Optional, Tuple, Union

import requests

from unstructured_client._hooks.custom.common import UNSTRUCTURED_CLIENT_LOGGER_NAME
from unstructured_client._hooks.types import (
    AfterErrorContext,
    AfterErrorHook,
    SDKInitHook,
)


class LogRetriesAfterErrorHook(AfterErrorHook, SDKInitHook):
    """Hook providing visibility to users when the client retries requests"""

    def log_retries(self, response: Optional[requests.Response]):
        """Log retries to give users visibility into requests."""
        logger = logging.getLogger(UNSTRUCTURED_CLIENT_LOGGER_NAME)
        logger.setLevel(logging.INFO)

        if response is not None and response.status_code == 500:
            logger.info("Response status code: 500. Sleeping before retry.")

            if bool(response.text):
                logger.info(response.text)

    def sdk_init(
        self, base_url: str, client: requests.Session
    ) -> Tuple[str, requests.Session]:
        logging.basicConfig(
            level=logging.INFO,
            format="%(levelname)s: %(message)s",
            stream=sys.stdout,
        )
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
