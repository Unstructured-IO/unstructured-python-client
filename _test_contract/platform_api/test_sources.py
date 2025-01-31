from datetime import datetime
from unittest import mock

import pytest

from unstructured_client import UnstructuredClient
from unstructured_client.models import shared, operations
from unstructured_client.models.errors import SDKError
from unstructured_client.models.shared import SourceConnectorType


class AsyncMock(mock.MagicMock):
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)


def test_list_sources(httpx_mock, client: UnstructuredClient, platform_api_url: str):
    url = f"{platform_api_url}/api/v1/sources/"

    httpx_mock.add_response(
        method="GET",
        headers={"Content-Type": "application/json"},
        json=[
            {
                "config": {},
                "created_at": "2023-09-15T01:06:53.146Z",
                "id": "a15d4161-77a0-4e08-b65e-86f398ce15ad",
                "name": "test_source_name",
                "type": "onedrive",
            }
        ],
        url=url,
    )

    sources_response = client.sources.list_sources(
        request=operations.ListSourcesRequest()
    )
    assert sources_response.status_code == 200

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "GET"
    assert request.url == url

    assert len(sources_response.response_list_sources) == 1
    source = sources_response.response_list_sources[0]
    assert source.id == "a15d4161-77a0-4e08-b65e-86f398ce15ad"
    assert source.name == "test_source_name"
    assert source.type == "onedrive"
    assert source.config == {}
    assert source.created_at == datetime.fromisoformat("2023-09-15T01:06:53.146+00:00")


def test_list_sources_empty(
    httpx_mock, client: UnstructuredClient, platform_api_url: str
):
    url = f"{platform_api_url}/api/v1/sources/"

    httpx_mock.add_response(
        method="GET",
        headers={"Content-Type": "application/json"},
        json=[],
        url=url,
    )

    sources_response = client.sources.list_sources(
        request=operations.ListSourcesRequest()
    )
    assert sources_response.status_code == 200

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "GET"
    assert request.url == url

    assert len(sources_response.response_list_sources) == 0


@pytest.mark.parametrize(
    "error_status_code",
    [400, 401, 403, 404, 500, 502, 503, 504],
)
@pytest.mark.httpx_mock(can_send_already_matched_responses=True)  # in case of retries
def test_list_sources_5xx_code(
    httpx_mock,
    client: UnstructuredClient,
    platform_api_url: str,
    error_status_code: int,
):
    url = f"{platform_api_url}/api/v1/sources/"

    httpx_mock.add_response(
        method="GET",
        headers={"Content-Type": "application/json"},
        status_code=error_status_code,
        url=url,
    )

    with pytest.raises(SDKError) as excinfo:
        client.sources.list_sources(request=operations.ListSourcesRequest())
    requests = httpx_mock.get_requests()
    assert len(requests) >= 1
    assert excinfo.value.message == "API error occurred"
    assert excinfo.value.status_code == error_status_code


def test_get_source(httpx_mock, client: UnstructuredClient, platform_api_url: str):
    dest_id = "a15d4161-77a0-4e08-b65e-86f398ce15ad"
    url = f"{platform_api_url}/api/v1/sources/{dest_id}"

    httpx_mock.add_response(
        method="GET",
        headers={"Content-Type": "application/json"},
        json={
            "config": {},
            "created_at": "2023-09-15T01:06:53.146Z",
            "id": "a15d4161-77a0-4e08-b65e-86f398ce15ad",
            "name": "test_source_name",
            "type": "onedrive",
        },
        url=url,
    )

    source_response = client.sources.get_source(
        request=operations.GetSourceRequest(source_id=dest_id)
    )
    assert source_response.status_code == 200

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "GET"
    assert request.url == url

    source = source_response.source_connector_information
    assert source.id == "a15d4161-77a0-4e08-b65e-86f398ce15ad"
    assert source.name == "test_source_name"
    assert source.type == "onedrive"
    assert source.config == {}
    assert source.created_at == datetime.fromisoformat("2023-09-15T01:06:53.146+00:00")


def test_get_source_not_found(
    httpx_mock, client: UnstructuredClient, platform_api_url: str
):
    dest_id = "a15d4161-77a0-4e08-b65e-86f398ce15ad"
    url = f"{platform_api_url}/api/v1/sources/{dest_id}"

    httpx_mock.add_response(
        method="GET",
        headers={"Content-Type": "application/json"},
        status_code=404,
        url=url,
    )

    with pytest.raises(SDKError) as excinfo:
        client.sources.get_source(request=operations.GetSourceRequest(source_id=dest_id))

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    assert excinfo.value.message == "API error occurred"
    assert excinfo.value.status_code == 404


def test_create_source(httpx_mock, client: UnstructuredClient, platform_api_url: str):
    url = f"{platform_api_url}/api/v1/sources/"

    httpx_mock.add_response(
        method="POST",
        headers={"Content-Type": "application/json"},
        json={
            "config": {},
            "created_at": "2023-09-15T01:06:53.146Z",
            "id": "a15d4161-77a0-4e08-b65e-86f398ce15ad",
            "name": "test_source_name",
            "type": "onedrive",
        },
        url=url,
    )

    source_response = client.sources.create_source(
        request=operations.CreateSourceRequest(
            create_source_connector=shared.CreateSourceConnector(
                name="test_source_name",
                type=SourceConnectorType.ONEDRIVE,
                config={},
            )
        )
    )
    assert source_response.status_code == 200

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "POST"
    assert request.url == url

    source = source_response.source_connector_information
    assert source.id == "a15d4161-77a0-4e08-b65e-86f398ce15ad"
    assert source.name == "test_source_name"
    assert source.type == "onedrive"
    assert source.config == {}
    assert source.created_at == datetime.fromisoformat("2023-09-15T01:06:53.146+00:00")


def test_update_source(httpx_mock, client: UnstructuredClient, platform_api_url: str):
    dest_id = "a15d4161-77a0-4e08-b65e-86f398ce15ad"
    url = f"{platform_api_url}/api/v1/sources/{dest_id}"

    httpx_mock.add_response(
        method="PUT",
        headers={"Content-Type": "application/json"},
        status_code=200,
        json={
            "config": {},
            "created_at": "2023-09-15T01:06:53.146Z",
            "id": "a15d4161-77a0-4e08-b65e-86f398ce15ad",
            "name": "test_source_name",
            "type": "onedrive",
        },
        url=url,
    )

    source_update_response = client.sources.update_source(
        request=operations.UpdateSourceRequest(
            source_id=dest_id,
            update_source_connector=shared.UpdateSourceConnector(
                config={}
            ),
        )
    )

    assert source_update_response.status_code == 200

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "PUT"
    assert request.url == url

    updated_source = source_update_response.source_connector_information
    assert updated_source.id == "a15d4161-77a0-4e08-b65e-86f398ce15ad"
    assert updated_source.name == "test_source_name"
    assert updated_source.type == "onedrive"
    assert updated_source.config == {}
    assert updated_source.created_at == datetime.fromisoformat(
        "2023-09-15T01:06:53.146+00:00"
    )


def test_delete_source(httpx_mock, client: UnstructuredClient, platform_api_url: str):
    dest_id = "a15d4161-77a0-4e08-b65e-86f398ce15ad"
    url = f"{platform_api_url}/api/v1/sources/{dest_id}"

    httpx_mock.add_response(
        method="DELETE",
        headers={"Content-Type": "application/json"},
        status_code=200,
        json={"detail": "Source with id 1 successfully deleted."},
        url=url,
    )

    response = client.sources.delete_source(
        request=operations.DeleteSourceRequest(source_id=dest_id)
    )
    assert response.status_code == 200

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "DELETE"
    assert request.url == url
