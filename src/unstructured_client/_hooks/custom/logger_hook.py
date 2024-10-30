from __future__ import annotations

import logging
from typing import Optional, Tuple, Union, DefaultDict

import httpx

from unstructured_client._hooks.custom.common import UNSTRUCTURED_CLIENT_LOGGER_NAME
from unstructured_client._hooks.types import (
    AfterSuccessContext,
    AfterErrorContext,
    AfterErrorHook,
    SDKInitHook,
    AfterSuccessHook,
)
from unstructured_client.httpclient import HttpClient
from collections import defaultdict

logger = logging.getLogger(UNSTRUCTURED_CLIENT_LOGGER_NAME)


class LoggerHook(AfterErrorHook, AfterSuccessHook, SDKInitHook):
    """Hook providing custom logging"""

    def __init__(self) -> None:
        self.retries_counter: DefaultDict[str, int] = defaultdict(int)

    def log_retries(self, response: Optional[httpx.Response],  error: Optional[Exception], operation_id: str,):
        """Log retries to give users visibility into requests."""

        if response is not None and response.status_code // 100 == 5:
            logger.info(
                "Failed to process a request due to API server error with status code %d. "
                "Attempting retry number %d after sleep.",
                response.status_code,
                self.retries_counter[operation_id],
            )
            if response.text:
                logger.info("Server message - %s", response.text)
        
        elif error is not None and isinstance(error, httpx.ConnectError):
            logger.info(
                "Failed to process a request due to connection error - %s. "
                "Attempting retry number %d after sleep.",
                error,
                self.retries_counter[operation_id],
            )


    def sdk_init(
        self, base_url: str, client: HttpClient
    ) -> Tuple[str, HttpClient]:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
        return base_url, client

    def after_success(
        self, hook_ctx: AfterSuccessContext, response: httpx.Response
    ) -> Union[httpx.Response, Exception]:
        self.retries_counter.pop(hook_ctx.operation_id, None)
        # Note(austin) - pdf splitting returns a mock request
        # so we always reach the AfterSuccessHook
        # This doesn't mean the splits succeeded
        # Need to revisit our logging strategy
        # logger.info("Successfully partitioned the document.")
        return response

    def after_error(
        self,
        hook_ctx: AfterErrorContext,
        response: Optional[httpx.Response],
        error: Optional[Exception],
    ) -> Union[Tuple[Optional[httpx.Response], Optional[Exception]], Exception]:
        """Concrete implementation for AfterErrorHook."""
        self.retries_counter[hook_ctx.operation_id] += 1
        self.log_retries(response, error, hook_ctx.operation_id)

        if response and response.status_code == 200:
            # NOTE: Even though this is an after_error method, due to split_pdf_hook logic we may get
            # a success here when one of the split requests was partitioned successfully
            return response, error
        logger.error("Failed to partition the document.")
        if response:
            logger.error("Server responded with %d - %s", response.status_code, response.text)
        if error is not None:
            logger.error("Following error occurred - %s", error)
        return response, error
