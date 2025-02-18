from __future__ import annotations

from typing import Tuple
from urllib.parse import ParseResult, urlparse, urlunparse

from unstructured_client._hooks.types import SDKInitHook
from unstructured_client.httpclient import HttpClient


def clean_server_url(base_url: str) -> str:
    """Fix url scheme and remove the '/general/v0/general' path."""

    if not base_url:
        return ""
    # -- add a url scheme if not present (urllib.parse does not work reliably without it)
    if "http" not in base_url:
        base_url = "http://" + base_url

    parsed_url: ParseResult = urlparse(base_url)

    if "api.unstructuredapp.io" in base_url:
        if parsed_url.scheme != "https":
            parsed_url = parsed_url._replace(scheme="https")

    # -- path should always be empty
    return urlunparse(parsed_url._replace(path=""))


def choose_server_url(endpoint_url, client_url, default_endpoint_url) -> str:
    """
    Helper function to fix a breaking change in the SDK past 0.30.0.
    When we merged the partition and platform specs, the client server_url stopped working,
    and users need to pass it in the endpoint function.
    For now, call this helper in the generated code to set the correct url.
    """

    # First, see if the endpoint has a url:
    # s.general.partition(server_url=...)
    if endpoint_url is not None:
        url = endpoint_url

    # Next, try the base client url:
    # s = UnstructuredClient(server_url=...)
    # (If not set it's an empty string)
    elif client_url != "":
        url = client_url

    # Finally, take the url defined in the spec:
    # operations.PARTITION_SERVERS[...]
    else:
        url = default_endpoint_url

    # Make sure we drop the path if it's provided anywhere
    # (The endpoint url will be set after we've done the init hooks)
    return clean_server_url(url)


class CleanServerUrlSDKInitHook(SDKInitHook):
    """Hook fixing common mistakes by users in defining `server_url` in the unstructured-client"""

    def sdk_init(
        self, base_url: str, client: HttpClient
    ) -> Tuple[str, HttpClient]:
        """Concrete implementation for SDKInitHook."""
        cleaned_url = clean_server_url(base_url)

        return cleaned_url, client
