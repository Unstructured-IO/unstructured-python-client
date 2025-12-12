from datetime import datetime

import pytest

from unstructured_client import UnstructuredClient
from unstructured_client.models import operations
from unstructured_client.models.errors import SDKError


def test_list_templates(httpx_mock, platform_client: UnstructuredClient, platform_api_url: str):
    url = f"{platform_api_url}/api/v1/templates/"

    httpx_mock.add_response(
        method="GET",
        headers={"Content-Type": "application/json"},
        json=[
            {
                "id": "hi_res_partition",
                "name": "High Resolution Partition",
                "description": "Partition documents with high resolution strategy",
                "version": "1.0.0",
                "last_updated": "2024-01-01T00:00:00.000000",
            },
            {
                "id": "hi_res_and_enrichment",
                "name": "High Resolution and Enrichment",
                "description": "Partition with enrichment",
                "version": "1.0.0",
                "last_updated": "2024-01-01T00:00:00.000000",
            },
        ],
        url=url,
    )

    templates_response = platform_client.templates.list_templates(
        request=operations.ListTemplatesRequest()
    )
    assert templates_response.status_code == 200

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "GET"
    assert request.url == url

    templates = templates_response.response_list_templates
    assert templates is not None
    assert len(templates) == 2
    assert templates[0].id == "hi_res_partition"
    assert templates[0].name == "High Resolution Partition"
    assert templates[1].id == "hi_res_and_enrichment"


def test_get_template(httpx_mock, platform_client: UnstructuredClient, platform_api_url: str):
    url = f"{platform_api_url}/api/v1/templates/hi_res_partition"

    httpx_mock.add_response(
        method="GET",
        headers={"Content-Type": "application/json"},
        json={
            "id": "hi_res_partition",
            "name": "High Resolution Partition",
            "description": "Partition documents with high resolution strategy",
            "version": "1.0.0",
            "last_updated": "2024-01-01T00:00:00.000000",
            "nodes": [
                {
                    "id": "93fc2ce8-e7c8-424f-a6aa-41460fc5d35d",
                    "name": "partition step",
                    "type": "partition",
                    "subtype": "unstructured_api",
                    "settings": {
                        "strategy": "fast",
                        "include_page_breaks": False,
                    },
                }
            ],
        },
        url=url,
    )

    template_response = platform_client.templates.get_template(
        request=operations.GetTemplateRequest(template_id="hi_res_partition")
    )
    assert template_response.status_code == 200

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "GET"
    assert request.url == url

    template = template_response.template_detail
    assert template is not None
    assert template.id == "hi_res_partition"
    assert template.name == "High Resolution Partition"
    assert len(template.nodes) == 1
    assert template.nodes[0].id == "93fc2ce8-e7c8-424f-a6aa-41460fc5d35d"


def test_get_template_not_found(
    httpx_mock, platform_client: UnstructuredClient, platform_api_url: str
):
    url = f"{platform_api_url}/api/v1/templates/nonexistent_template"

    httpx_mock.add_response(
        method="GET",
        status_code=404,
        headers={"Content-Type": "application/json"},
        json={"detail": "Template nonexistent_template not found"},
        url=url,
    )

    with pytest.raises(SDKError) as e:
        platform_client.templates.get_template(
            request=operations.GetTemplateRequest(template_id="nonexistent_template")
        )

    assert e.value.status_code == 404
    assert "API error occurred" in e.value.message

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "GET"
    assert request.url == url

