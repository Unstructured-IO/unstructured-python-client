from __future__ import annotations

import re
from typing import Tuple
from urllib.parse import ParseResult, urlparse, urlunparse

from unstructured_client._hooks.types import SDKInitHook
from unstructured_client.httpclient import HttpClient

# A scheme is "<letter><letter|digit|+|-|.>* ://" (RFC 3986). Matching on the substring
# "http" instead treats any host containing it, such as `myhttpd.local`, as already
# schemed. Requiring "://" also keeps `localhost:8000` unschemed, which is why urlparse
# is not used for this check: it reads `localhost` as the scheme.
_URL_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://")


def clean_server_url(base_url: str | None) -> str:
    """Fix url scheme and remove subpath for URLs under Unstructured domains."""

    if not base_url:
        return ""

    # add a url scheme if not present (urllib.parse does not work reliably without it)
    if not _URL_SCHEME_RE.match(base_url):
        base_url = "http://" + base_url

    parsed_url: ParseResult = urlparse(base_url)
    
    if "unstructuredapp.io" in parsed_url.netloc:
        if parsed_url.scheme != "https":
            parsed_url = parsed_url._replace(scheme="https")
        # We only want the base url for Unstructured domains
        clean_url =  urlunparse(parsed_url._replace(path="", params="", query="", fragment=""))
    
    else:
        # For other domains, we want to keep the path
        clean_url = urlunparse(parsed_url._replace(params="", query="", fragment=""))

    return clean_url.rstrip("/")
    


class CleanServerUrlSDKInitHook(SDKInitHook):
    """Hook fixing common mistakes by users in defining `server_url` in the unstructured-client"""

    def sdk_init(
        self, base_url: str, client: HttpClient
    ) -> Tuple[str, HttpClient]:
        """Concrete implementation for SDKInitHook."""
        cleaned_url = clean_server_url(base_url)

        return cleaned_url, client
