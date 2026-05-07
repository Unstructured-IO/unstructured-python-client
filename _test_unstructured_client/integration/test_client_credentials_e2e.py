"""End-to-end integration test for :class:`ClientCredentials` and
:class:`LegacyKeyExchange`.

This test is **opt-in**: it only runs when every required env var is set.
Point it at any deployment that has ``DEPLOYMENT_MODE=dedicated`` (or any
other configuration that accepts ``/auth/token-exchange``) and a valid
client secret provisioned via account-service.

Required env vars
-----------------

- ``UNS_ACCOUNTS_URL``   base URL of account-service (e.g.
  ``https://accounts.<your-deployment>.example``)
- ``UNS_CLIENT_SECRET``  ``uns_sk_...`` client secret
- ``UNS_PLATFORM_API_URL`` platform-api base URL to hit after exchange

Optional:

- ``UNS_LEGACY_API_KEY`` if set, the LegacyKeyExchange path is also
  exercised against the same platform-api.

What it verifies
----------------

1. The SDK can bootstrap a :class:`ClientCredentials` and successfully
   exchange the secret for a JWT against real account-service.
2. A real downstream call (``jobs.list_jobs``) goes through with
   ``Authorization: Bearer`` and returns 2xx.
3. Re-using the same client does not trigger a second exchange (cache
   hit) because the first JWT is still within its TTL.
"""

from __future__ import annotations

import os

import pytest

from unstructured_client import UnstructuredClient
from unstructured_client.auth import ClientCredentials, LegacyKeyExchange
from unstructured_client.models import operations

ACCOUNTS_URL = os.getenv("UNS_ACCOUNTS_URL")
CLIENT_SECRET = os.getenv("UNS_CLIENT_SECRET")
PLATFORM_API_URL = os.getenv("UNS_PLATFORM_API_URL")
LEGACY_API_KEY = os.getenv("UNS_LEGACY_API_KEY")


_REASON = (
    "Opt-in E2E: set UNS_ACCOUNTS_URL, UNS_CLIENT_SECRET, and "
    "UNS_PLATFORM_API_URL to run against a real deployment that supports "
    "/auth/token-exchange."
)


pytestmark = pytest.mark.skipif(
    not (ACCOUNTS_URL and CLIENT_SECRET and PLATFORM_API_URL),
    reason=_REASON,
)


def _list_jobs(session: UnstructuredClient) -> None:
    """Lightweight read request that only needs an authenticated identity."""
    session.jobs.list_jobs(request=operations.ListJobsRequest())


def test_client_credentials_exchange_and_list_jobs():
    cc = ClientCredentials(
        client_secret=CLIENT_SECRET,  # type: ignore[arg-type]
        server_url=ACCOUNTS_URL,  # type: ignore[arg-type]
    )
    try:
        session = UnstructuredClient(
            api_key_auth=cc,
            server_url=PLATFORM_API_URL,
            timeout_ms=60_000,
        )

        _list_jobs(session)

        # Cached exchange: internal cache now holds a JWT; a second call
        # should not trigger a new exchange unless we crossed the refresh
        # buffer, which is unlikely across two sequential requests.
        before_cache = cc._cache  # type: ignore[attr-defined]
        assert before_cache is not None, "expected cache to be populated after first call"

        _list_jobs(session)

        after_cache = cc._cache  # type: ignore[attr-defined]
        assert after_cache is before_cache, (
            "ClientCredentials re-exchanged within TTL; cache should be reused"
        )
    finally:
        cc.close()


@pytest.mark.skipif(
    LEGACY_API_KEY is None,
    reason="Set UNS_LEGACY_API_KEY to also exercise the LegacyKeyExchange path.",
)
def test_legacy_key_exchange_and_list_jobs():
    lke = LegacyKeyExchange(
        api_key=LEGACY_API_KEY,  # type: ignore[arg-type]
        server_url=ACCOUNTS_URL,  # type: ignore[arg-type]
    )
    try:
        session = UnstructuredClient(
            api_key_auth=lke,
            server_url=PLATFORM_API_URL,
            timeout_ms=60_000,
        )
        _list_jobs(session)
        assert lke._cache is not None  # type: ignore[attr-defined]
    finally:
        lke.close()
