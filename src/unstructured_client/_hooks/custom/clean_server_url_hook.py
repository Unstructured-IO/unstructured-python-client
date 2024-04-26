from typing import Tuple
from urllib.parse import ParseResult, urlparse, urlunparse

import requests

from unstructured_client._hooks.types import SDKInitHook


class CleanServerUrlSDKInitHook(SDKInitHook):
    """Hook fixing common mistakes by users in defining `server_url` in the unstructured-client"""

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

    def sdk_init(
        self, base_url: str, client: requests.Session
    ) -> Tuple[str, requests.Session]:
        """Concrete implementation for SDKInitHook."""
        cleaned_url = self.clean_server_url(base_url)

        return cleaned_url, client
