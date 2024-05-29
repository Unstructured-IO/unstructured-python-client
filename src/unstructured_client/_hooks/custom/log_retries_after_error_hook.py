import logging
from typing import Optional, Tuple, Union, DefaultDict

import requests

from unstructured_client._hooks.custom.common import UNSTRUCTURED_CLIENT_LOGGER_NAME
from unstructured_client._hooks.types import (
    AfterSuccessContext,
    AfterErrorContext,
    AfterErrorHook,
    SDKInitHook,
)
from collections import defaultdict

logger = logging.getLogger(UNSTRUCTURED_CLIENT_LOGGER_NAME)


class LogRetriesAfterErrorHook(AfterErrorHook, SDKInitHook):
    """Hook providing visibility to users when the client retries requests"""

    def __init__(self) -> None:
        self.retries_counter: DefaultDict[str, int] = defaultdict(int)

    def log_retries(self, response: Optional[requests.Response], operation_id: str):
        """Log retries to give users visibility into requests."""

        if response is not None and response.status_code // 100 == 5:
            logger.info("Failed to process a request due to API server error with status code %d. "
                        "Attempting retry number %d after sleep.",
                        response.status_code,
                        self.retries_counter[operation_id])
            if response.text:
                logger.info("Server message - %s", response.text)

    def sdk_init(
        self, base_url: str, client: requests.Session
    ) -> Tuple[str, requests.Session]:
        return base_url, client

    def after_success(
        self, hook_ctx: AfterSuccessContext, response: requests.Response
    ) -> Union[requests.Response, Exception]:
        del self.retries_counter[hook_ctx.operation_id]
        return response

    def after_error(
        self,
        hook_ctx: AfterErrorContext,
        response: Optional[requests.Response],
        error: Optional[Exception],
    ) -> Union[Tuple[Optional[requests.Response], Optional[Exception]], Exception]:
        """Concrete implementation for AfterErrorHook."""
        self.retries_counter[hook_ctx.operation_id]+= 1
        self.log_retries(response, hook_ctx.operation_id)
        return response, error
