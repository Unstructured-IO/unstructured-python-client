from datetime import datetime

import pytest

from unstructured_client import UnstructuredClient
from unstructured_client.models import shared, operations
from unstructured_client.models.errors import SDKError
from unstructured_client.models.shared import DestinationConnectorType



def test_list_destinations(
    httpx_mock, client: UnstructuredClient, platform_api_url: str
):
    url = f"{platform_api_url}/api/v1/destinations/"

    httpx_mock.add_response(
        method="GET",
        headers={"Content-Type": "application/json"},
        json=[
            {
                "config": {},
                "created_at": "2025-08-22T08:47:29.802Z",
                "id": "0c363dec-3c70-45ee-8041-481044a6e1cc",
                "name": "test_destination_name",
                "type": "s3",
            }
        ],
        url=url,
    )

    destinations_response = client.destinations.list_destinations(
        request=operations.ListDestinationsRequest()
    )
    assert destinations_response.status_code == 200

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "GET"
    assert request.url == url

    assert len(destinations_response.response_list_destinations) == 1
    destination = destinations_response.response_list_destinations[0]
    assert destination.id == "0c363dec-3c70-45ee-8041-481044a6e1cc"
    assert destination.name == "test_destination_name"
    assert destination.type == "s3"
    assert destination.config == {}
    assert destination.created_at == datetime.fromisoformat(
        "2025-08-22T08:47:29.802+00:00"
    )


def test_list_destinations_empty(
    httpx_mock, client: UnstructuredClient, platform_api_url: str
):
    url = f"{platform_api_url}/api/v1/destinations/"

    httpx_mock.add_response(
        method="GET",
        headers={"Content-Type": "application/json"},
        json=[],
        url=url,
    )

    destinations_response = client.destinations.list_destinations(
        request=operations.ListDestinationsRequest()
    )
    assert destinations_response.status_code == 200

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "GET"
    assert request.url == url

    assert len(destinations_response.response_list_destinations) == 0


@pytest.mark.parametrize(
    "error_status_code",
    [400, 401, 403, 404, 500, 502, 503, 504],
)
@pytest.mark.httpx_mock(can_send_already_matched_responses=True)  # in case of retries
def test_list_destinations_5xx_code(
    httpx_mock,
    client: UnstructuredClient,
    platform_api_url: str,
    error_status_code: int,
):
    url = f"{platform_api_url}/api/v1/destinations/"

    httpx_mock.add_response(
        method="GET",
        headers={"Content-Type": "application/json"},
        status_code=error_status_code,
        url=url,
    )

    with pytest.raises(SDKError) as excinfo:
        client.destinations.list_destinations(
            request=operations.ListDestinationsRequest()
        )
    requests = httpx_mock.get_requests()
    assert len(requests) >= 1
    assert excinfo.value.message == "API error occurred"
    assert excinfo.value.status_code == error_status_code


def test_get_destination(httpx_mock, client: UnstructuredClient, platform_api_url: str):
    dest_id = "0c363dec-3c70-45ee-8041-481044a6e1cc"
    url = f"{platform_api_url}/api/v1/destinations/{dest_id}"

    httpx_mock.add_response(
        method="GET",
        headers={"Content-Type": "application/json"},
        json={
            "config": {},
            "created_at": "2025-08-22T08:47:29.802Z",
            "id": "0c363dec-3c70-45ee-8041-481044a6e1cc",
            "name": "test_destination_name",
            "type": "s3",
        },
        url=url,
    )

    destination_response = client.destinations.get_destination(
        request=operations.GetDestinationRequest(destination_id=dest_id)
    )
    assert destination_response.status_code == 200

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "GET"
    assert request.url == url

    destination = destination_response.destination_connector_information
    assert destination.id == "0c363dec-3c70-45ee-8041-481044a6e1cc"
    assert destination.name == "test_destination_name"
    assert destination.type == "s3"
    assert destination.config == {}
    assert destination.created_at == datetime.fromisoformat(
        "2025-08-22T08:47:29.802+00:00"
    )


def test_get_destination_not_found(
    httpx_mock, client: UnstructuredClient, platform_api_url: str
):
    dest_id = "0c363dec-3c70-45ee-8041-481044a6e1cc"
    url = f"{platform_api_url}/api/v1/destinations/{dest_id}"

    httpx_mock.add_response(
        method="GET",
        headers={"Content-Type": "application/json"},
        status_code=404,
        url=url,
    )

    with pytest.raises(SDKError) as excinfo:
        client.destinations.get_destination(
            request=operations.GetDestinationRequest(destination_id=dest_id)
        )

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    assert excinfo.value.message == "API error occurred"
    assert excinfo.value.status_code == 404


def test_create_destination(
    httpx_mock, client: UnstructuredClient, platform_api_url: str
):
    url = f"{platform_api_url}/api/v1/destinations/"

    httpx_mock.add_response(
        method="POST",
        headers={"Content-Type": "application/json"},
        json={
            "config": {},
            "created_at": "2023-09-15T01:06:53.146Z",
            "id": "b25d4161-77a0-4e08-b65e-86f398ce15ad",
            "name": "test_destination_name",
            "type": "s3",
        },
        url=url,
    )

    destination_response = client.destinations.create_destination(
        request=operations.CreateDestinationRequest(
            create_destination_connector=shared.CreateDestinationConnector(
                name="test_destination_name",
                type=DestinationConnectorType.S3,
                config={},
            )
        )
    )
    assert destination_response.status_code == 200

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "POST"
    assert request.url == url

    destination = destination_response.destination_connector_information
    assert destination.id == "b25d4161-77a0-4e08-b65e-86f398ce15ad"
    assert destination.name == "test_destination_name"
    assert destination.type == "s3"
    assert destination.config == {}
    assert destination.created_at == datetime.fromisoformat(
        "2023-09-15T01:06:53.146+00:00"
    )


def test_update_destination(
    httpx_mock, client: UnstructuredClient, platform_api_url: str
):
    dest_id = "b25d4161-77a0-4e08-b65e-86f398ce15ad"
    url = f"{platform_api_url}/api/v1/destinations/{dest_id}"

    httpx_mock.add_response(
        method="PUT",
        headers={"Content-Type": "application/json"},
        json={
            "config": {},
            "created_at": "2023-09-15T01:06:53.146Z",
            "id": "b25d4161-77a0-4e08-b65e-86f398ce15ad",
            "name": "test_destination_name",
            "type": "s3",
        },
        url=url,
    )

    destination_update_response = client.destinations.update_destination(
        request=operations.UpdateDestinationRequest(
            destination_id=dest_id,
            update_destination_connector=shared.UpdateDestinationConnector(
                config={}
            ),
        )
    )

    destination_update_response.status_code == 200

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "PUT"
    assert request.url == url

    updated_destination = destination_update_response.destination_connector_information
    assert updated_destination.id == "b25d4161-77a0-4e08-b65e-86f398ce15ad"
    assert updated_destination.name == "test_destination_name"
    assert updated_destination.type == "s3"
    assert updated_destination.config == {}
    assert updated_destination.created_at == datetime.fromisoformat(
        "2023-09-15T01:06:53.146+00:00"
    )


def test_delete_destination(
    httpx_mock, client: UnstructuredClient, platform_api_url: str
):
    dest_id = "b25d4161-77a0-4e08-b65e-86f398ce15ad"
    url = f"{platform_api_url}/api/v1/destinations/{dest_id}"

    httpx_mock.add_response(
        method="DELETE",
        headers={"Content-Type": "application/json"},
        status_code=200,
        json={"detail": "Destination with id 1 successfully deleted."},
        url=url,
    )

    response = client.destinations.delete_destination(
        request=operations.DeleteDestinationRequest(destination_id=dest_id)
    )
    assert response.status_code == 200

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "DELETE"
    assert request.url == url
