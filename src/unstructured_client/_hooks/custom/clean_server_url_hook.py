from __future__ import annotations

from typing import Tuple
from urllib.parse import ParseResult, urlparse, urlunparse

from unstructured_client._hooks.types import SDKInitHook
from unstructured_client.httpclient import HttpClient

# Domains Unstructured serves its APIs from. Every operation in this SDK already carries
# its own path prefix (`/api/v1/...`, `/general/v0/general`), so a base URL under one of
# these hosts must not carry a path of its own -- the app and the docs hand users a full
# API URL, and appending an operation path to that produces a doubled prefix that 404s.
UNSTRUCTURED_DOMAINS = ("unstructuredapp.io", "unstructured.io")


def is_unstructured_domain(hostname: str | None) -> bool:
    """True if the hostname is one of Unstructured's own API domains, or a subdomain of one.

    Matched on domain boundaries, so a host that merely contains one of our domains
    (`unstructuredapp.io.example.com`) is somebody else's and is left alone.
    """
    if not hostname:
        return False

    hostname = hostname.lower()
    return any(
        hostname == domain or hostname.endswith(f".{domain}")
        for domain in UNSTRUCTURED_DOMAINS
    )


def clean_server_url(base_url: str | None) -> str:
    """Fix url scheme and remove subpath for URLs under Unstructured domains."""

    if not base_url:
        return ""

    # add a url scheme if not present (urllib.parse does not work reliably without it)
    if "http" not in base_url:
        base_url = "http://" + base_url

    parsed_url: ParseResult = urlparse(base_url)

    if is_unstructured_domain(parsed_url.hostname):
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
