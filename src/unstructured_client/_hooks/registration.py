import logging
import sys
from typing import Optional, Tuple, Union
from urllib.parse import ParseResult, urlparse, urlunparse
import warnings

import requests

from .types import AfterErrorContext, AfterErrorHook, Hooks, SDKInitHook


# This file is only ever generated once on the first generation and then is free to be modified.
# Any hooks you wish to add should be registered in the init_hooks function. Feel free to define 
# them in this file or in separate files in the hooks folder.


class CleanServerUrlSDKInitHook(SDKInitHook):

    def clean_server_url(self, base_url) -> str:
        """Fix url scheme and remove the '/general/v0/general' path."""

        # -- add a url scheme if not present (urllib.parse does not work reliably without it)
        if "http" not in base_url:
            base_url = "http://" + base_url

        parsed_url: ParseResult = urlparse(base_url)

        if "api.unstructuredapp.io" in base_url:
            if parsed_url.scheme != "https":
                parsed_url = parsed_url._replace(scheme="https")

        # -- path should always be empty
        return urlunparse(parsed_url._replace(path=""))
    
    def sdk_init(self, base_url: str, client: requests.Session) -> Tuple[str, requests.Session]:
        """Concrete implementation for SDKInitHook."""
        cleaned_url = self.clean_server_url(base_url)

        return cleaned_url, client


class LogRetriesAfterErrorHook(AfterErrorHook):

    def log_retries(self, response: Optional[requests.Response]):
        """Log retries to give users visibility into requests."""
        logging.basicConfig(
            level=logging.INFO, 
            format='%(levelname)s: %(message)s', 
            stream=sys.stdout,
        )
        logger = logging.getLogger('unstructured-client')
        logger.setLevel(logging.INFO)

        if response is not None and response.status_code == 500:
            logger.info("Response status code: 500. Sleeping before retry.")

            if bool(response.text):
                logger.info(response.text)

    def after_error(
        self, 
        hook_ctx: AfterErrorContext, 
        response: Optional[requests.Response], 
        error: Optional[Exception],
    ) -> Union[Tuple[Optional[requests.Response], Optional[Exception]], Exception]:
        """Concrete implementation for AfterErrorHook."""
        self.log_retries(response)
        return response, error


class SuggestDefiningUrlIf401AfterErrorHook(AfterErrorHook):

    def warn_if_401(self, response: Optional[requests.Response]):
        """Suggest defining the 'server_url' parameter if a 401 error is encountered."""
        if response is not None and response.status_code == 401:
            warnings.warn(
                "If intending to use the paid API, please define `server_url` in your request."
            )

    def after_error(
        self, 
        hook_ctx: AfterErrorContext, 
        response: Optional[requests.Response], 
        error: Optional[Exception],
    ) -> Union[Tuple[Optional[requests.Response], Optional[Exception]], Exception]:
        """Concrete implementation for AfterErrorHook."""
        self.warn_if_401(response)
        return response, error
    

def init_hooks(hooks: Hooks):
    # pylint: disable=unused-argument
    """Add hooks by calling `hooks.register_<type_or>_hook` with an instance of that hook.

    Hooks are registered per SDK instance, and are valid for the lifetime of the SDK instance"""
    hooks.register_sdk_init_hook(CleanServerUrlSDKInitHook())
    hooks.register_after_error_hook(SuggestDefiningUrlIf401AfterErrorHook())
    hooks.register_after_error_hook(LogRetriesAfterErrorHook())
