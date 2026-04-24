"""Tests for :class:`AuthHeaderBeforeRequestHook`.

These verify the header swap happens for our token-exchange callables and is
a no-op for plain string ``api_key_auth`` or arbitrary user-supplied
callables.
"""

from __future__ import annotations

import httpx

from unstructured_client import UnstructuredClient
from unstructured_client._hooks.custom.auth_header_hook import (
    AuthHeaderBeforeRequestHook,
)
from unstructured_client._hooks.types import BeforeRequestContext, HookContext
from unstructured_client.auth import ClientCredentials, LegacyKeyExchange

from ._mock_transport import ScriptedTransport, exchange_response

ACCOUNTS_URL = "https://accounts.example.test"
SERVER_URL = "https://api.example.test"
SECRET = "uns_sk_hook_test"
FAKE_KEY = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


def _make_request(headers: dict) -> httpx.Request:
    return httpx.Request(
        "GET", "https://api.example.test/api/v1/jobs/", headers=headers
    )


def _make_hook_ctx(security_source) -> BeforeRequestContext:
    inner = HookContext(
        config=None,  # type: ignore[arg-type]
        base_url=SERVER_URL,
        operation_id="cancel_job",
        oauth2_scopes=[],
        security_source=security_source,
    )
    return BeforeRequestContext(inner)


def test_rewrites_header_when_source_is_client_credentials():
    transport = ScriptedTransport([exchange_response()])
    cc = ClientCredentials(
        client_secret=SECRET,
        server_url=ACCOUNTS_URL,
        http_client=httpx.Client(transport=transport),
    )

    def factory():
        return None

    setattr(factory, "__wrapped_callable__", cc)

    hook = AuthHeaderBeforeRequestHook()
    request = _make_request({"unstructured-api-key": "jwt-value"})

    result = hook.before_request(_make_hook_ctx(factory), request)

    assert isinstance(result, httpx.Request)
    assert result.headers.get("Authorization") == "Bearer jwt-value"
    assert "unstructured-api-key" not in result.headers


def test_rewrites_header_when_source_is_legacy_key_exchange():
    transport = ScriptedTransport([exchange_response()])
    lke = LegacyKeyExchange(
        api_key="legacy",
        server_url=ACCOUNTS_URL,
        http_client=httpx.Client(transport=transport),
    )

    def factory():
        return None

    setattr(factory, "__wrapped_callable__", lke)

    hook = AuthHeaderBeforeRequestHook()
    request = _make_request({"unstructured-api-key": "jwt-value"})

    result = hook.before_request(_make_hook_ctx(factory), request)

    assert isinstance(result, httpx.Request)
    assert result.headers.get("Authorization") == "Bearer jwt-value"
    assert "unstructured-api-key" not in result.headers


def test_is_noop_for_plain_string_security_source():
    from unstructured_client.models import shared

    hook = AuthHeaderBeforeRequestHook()
    request = _make_request({"unstructured-api-key": FAKE_KEY})

    result = hook.before_request(
        _make_hook_ctx(shared.Security(api_key_auth=FAKE_KEY)),
        request,
    )

    assert isinstance(result, httpx.Request)
    assert result.headers.get("unstructured-api-key") == FAKE_KEY
    assert "Authorization" not in result.headers


def test_is_noop_for_arbitrary_user_callable():
    def user_callable() -> str:
        return "whatever"

    def factory():
        return None

    setattr(factory, "__wrapped_callable__", user_callable)

    hook = AuthHeaderBeforeRequestHook()
    request = _make_request({"unstructured-api-key": "whatever"})

    result = hook.before_request(_make_hook_ctx(factory), request)

    assert isinstance(result, httpx.Request)
    assert result.headers.get("unstructured-api-key") == "whatever"
    assert "Authorization" not in result.headers


def test_is_noop_when_security_source_is_none():
    hook = AuthHeaderBeforeRequestHook()
    request = _make_request({"unstructured-api-key": FAKE_KEY})

    result = hook.before_request(_make_hook_ctx(None), request)

    assert isinstance(result, httpx.Request)
    assert result.headers.get("unstructured-api-key") == FAKE_KEY
    assert "Authorization" not in result.headers


def test_integration_sends_bearer_header_for_client_credentials():
    """End-to-end: UnstructuredClient + ClientCredentials -> ``Authorization: Bearer``."""
    exchange_transport = ScriptedTransport(
        [exchange_response(access_token="jwt-abc", expires_in=900)]
    )
    exchange_http_client = httpx.Client(transport=exchange_transport)
    cc = ClientCredentials(
        client_secret=SECRET,
        server_url=ACCOUNTS_URL,
        http_client=exchange_http_client,
    )

    captured: dict = {}

    def _mock(request: httpx.Request) -> httpx.Response:
        captured["headers"] = dict(request.headers)
        return httpx.Response(200, json={})

    downstream_client = httpx.Client(transport=httpx.MockTransport(_mock))

    session = UnstructuredClient(
        api_key_auth=cc,
        client=downstream_client,
        server_url=SERVER_URL,
    )

    try:
        from unstructured_client.models import operations

        session.jobs.cancel_job(
            request=operations.CancelJobRequest(job_id="test-job-id"),
        )
    except Exception:  # noqa: BLE001
        # Mocked 200 with empty JSON won't deserialize correctly, but by then
        # the outgoing headers were already captured.
        pass

    headers = captured.get("headers", {})
    assert headers.get("authorization") == "Bearer jwt-abc"
    assert "unstructured-api-key" not in {k.lower() for k in headers}


def test_integration_leaves_legacy_path_unchanged_for_plain_string():
    captured: dict = {}

    def _mock(request: httpx.Request) -> httpx.Response:
        captured["headers"] = dict(request.headers)
        return httpx.Response(200, json={})

    client = httpx.Client(transport=httpx.MockTransport(_mock))
    session = UnstructuredClient(
        api_key_auth=FAKE_KEY,
        client=client,
        server_url=SERVER_URL,
    )

    try:
        from unstructured_client.models import operations

        session.jobs.cancel_job(
            request=operations.CancelJobRequest(job_id="test-job-id"),
        )
    except Exception:  # noqa: BLE001
        pass

    headers = captured.get("headers", {})
    assert headers.get("unstructured-api-key") == FAKE_KEY
    assert "authorization" not in {k.lower() for k in headers}
