from __future__ import annotations

from typing import Tuple
from urllib.parse import ParseResult, urlparse, urlunparse

from unstructured_client._hooks.types import SDKInitHook
from unstructured_client.httpclient import HttpClient


def clean_server_url(base_url: str) -> str:
    """Fix url scheme and remove the '/general/v0/general' path."""

    if not base_url:
        return ""

    # add a url scheme if not present (urllib.parse does not work reliably without it)
    if "http" not in base_url:
        base_url = "http://" + base_url

    parsed_url: ParseResult = urlparse(base_url)
    
    if "api.unstructuredapp.io" in parsed_url.netloc:
        if parsed_url.scheme != "https":
            parsed_url = parsed_url._replace(scheme="https")

    # We only want the base url
    return urlunparse(parsed_url._replace(path="", params="", query="", fragment=""))


def choose_server_url(endpoint_url: str | None, client_url: str, default_endpoint_url: str) -> str:
    """
    Helper function to fix a breaking change in the SDK past 0.30.0.
    When we merged the partition and platform specs, the client server_url stopped working,
    and users need to pass it in the endpoint function.
    For now, call this helper in the generated code to set the correct url.

    Order of choices:
    Endpoint server_url -> s.general.partition(server_url=...)
      (Passed in as None if not set)

    Base client server_url -> s = UnstructuredClient(server_url=...)
      (Passed as empty string if not set)

    Default endpoint URL as defined in the spec
    """

    # If the client doesn't get a server_url, it sets a default of platform
    # This is not always the correct default - we need to make sure default_endpoint_url is used
    # So, only use the client url if it has been set to something else
    if client_url == "https://platform.unstructuredapp.io":
        client_url = ""

    url = endpoint_url if endpoint_url is not None else (client_url or default_endpoint_url)
    return clean_server_url(url)


class CleanServerUrlSDKInitHook(SDKInitHook):
    """Hook fixing common mistakes by users in defining `server_url` in the unstructured-client"""

    def sdk_init(
        self, base_url: str, client: HttpClient
    ) -> Tuple[str, HttpClient]:
        """Concrete implementation for SDKInitHook."""
        cleaned_url = clean_server_url(base_url)

        return cleaned_url, client
