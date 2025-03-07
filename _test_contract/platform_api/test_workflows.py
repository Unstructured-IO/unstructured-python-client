from datetime import datetime

import pytest

from unstructured_client import UnstructuredClient
from unstructured_client.models import shared, operations
from unstructured_client.models.errors import SDKError


def test_list_workflows(httpx_mock, client: UnstructuredClient, platform_api_url: str):
    url = f"{platform_api_url}/api/v1/workflows/"

    httpx_mock.add_response(
        method="GET",
        url=url,
        json=[
            {
                "created_at": "2025-06-22T11:37:21.648Z",
                "destinations": [
                    "aeebecc7-9d8e-4625-bf1d-815c2f084869",
                ],
                "id": "16b80fee-64dc-472d-8f26-1d7729b6423d",
                "name": "test_workflow",
                "schedule": {"crontab_entries": [{"cron_expression": "0 0 * * 0"}]},
                "sources": [
                    "f1f7b1b2-8e4b-4a2b-8f1d-3e3c7c9e5a3c",
                ],
                "workflow_nodes": [],
                "status": "active",
                "workflow_type": "advanced",
            }
        ],
    )

    workflows_response = client.workflows.list_workflows(
        request=operations.ListWorkflowsRequest()
    )
    assert workflows_response.status_code == 200

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "GET"
    assert request.url == url

    workflows = workflows_response.response_list_workflows
    assert len(workflows) == 1
    workflow = workflows[0]
    assert workflow.id == "16b80fee-64dc-472d-8f26-1d7729b6423d"
    assert workflow.name == "test_workflow"
    assert workflow.workflow_type == "advanced"
    assert workflow.status == "active"
    assert workflow.created_at == datetime.fromisoformat(
        "2025-06-22T11:37:21.648+00:00"
    )
    assert workflow.schedule == shared.WorkflowSchedule(
        crontab_entries=[shared.crontabentry.CronTabEntry(cron_expression="0 0 * * 0")]
    )

    assert workflow.sources == [
        "f1f7b1b2-8e4b-4a2b-8f1d-3e3c7c9e5a3c",
    ]

    assert workflow.destinations == [
        "aeebecc7-9d8e-4625-bf1d-815c2f084869",
    ]


def test_list_workflows_empty(
    httpx_mock, client: UnstructuredClient, platform_api_url: str
):
    url = f"{platform_api_url}/api/v1/workflows/"

    httpx_mock.add_response(
        method="GET",
        url=url,
        json=[],
    )

    workflows_response = client.workflows.list_workflows(
        request=operations.ListWorkflowsRequest()
    )
    assert workflows_response.status_code == 200

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "GET"
    assert request.url == url

    workflows = workflows_response.response_list_workflows
    assert len(workflows) == 0


@pytest.mark.parametrize("error_status_code", [400, 401, 403, 404, 500, 502, 503, 504])
@pytest.mark.httpx_mock(can_send_already_matched_responses=True)  # in case of retries
def test_list_workflows_error(
    httpx_mock,
    client: UnstructuredClient,
    platform_api_url: str,
    error_status_code: int,
):
    url = f"{platform_api_url}/api/v1/workflows/"

    httpx_mock.add_response(
        method="GET",
        url=url,
        status_code=error_status_code,
    )

    with pytest.raises(SDKError) as excinfo:
        client.workflows.list_workflows(request=operations.ListWorkflowsRequest())
    assert excinfo.value.status_code == error_status_code
    assert excinfo.value.message == "API error occurred"


def test_create_workflow(httpx_mock, client: UnstructuredClient, platform_api_url: str):
    url = f"{platform_api_url}/api/v1/workflows/"

    httpx_mock.add_response(
        method="POST",
        url=url,
        status_code=200,
        json={
            "created_at": "2025-06-22T11:37:21.648Z",
            "destinations": [
                "aeebecc7-9d8e-4625-bf1d-815c2f084869",
            ],
            "id": "16b80fee-64dc-472d-8f26-1d7729b6423d",
            "name": "test_workflow",
            "schedule": {"crontab_entries": [{"cron_expression": "0 0 * * 0"}]},
            "sources": [
                "f1f7b1b2-8e4b-4a2b-8f1d-3e3c7c9e5a3c",
            ],
            "workflow_nodes": [],
            "status": "active",
            "workflow_type": "advanced",
        },
    )

    create_workflow_response = client.workflows.create_workflow(
        request=operations.CreateWorkflowRequest(
            create_workflow=shared.CreateWorkflow(
                name="test_workflow",
                workflow_type="advanced",
                schedule="weekly",
                source_id="f1f7b1b2-8e4b-4a2b-8f1d-3e3c7c9e5a3c",
                destination_id="aeebecc7-9d8e-4625-bf1d-815c2f084869",
            )
        )
    )

    assert create_workflow_response.status_code == 200

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "POST"
    assert request.url == url


def test_update_workflow(httpx_mock, client: UnstructuredClient, platform_api_url: str):
    url = f"{platform_api_url}/api/v1/workflows/16b80fee-64dc-472d-8f26-1d7729b6423d"

    httpx_mock.add_response(
        method="PUT",
        url=url,
        status_code=200,
        json={
            "created_at": "2025-06-22T11:37:21.648Z",
            "destinations": [
                "aeebecc7-9d8e-4625-bf1d-815c2f084869",
            ],
            "id": "16b80fee-64dc-472d-8f26-1d7729b6423d",
            "name": "test_workflow",
            "schedule": {"crontab_entries": [{"cron_expression": "0 0 * * 0"}]},
            "sources": [
                "f1f7b1b2-8e4b-4a2b-8f1d-3e3c7c9e5a3c",
            ],
            "workflow_nodes": [],
            "status": "active",
            "workflow_type": "advanced",
        },
    )

    update_workflow_response = client.workflows.update_workflow(
        request=operations.UpdateWorkflowRequest(
            workflow_id="16b80fee-64dc-472d-8f26-1d7729b6423d",
            update_workflow=shared.UpdateWorkflow(
                name="test_workflow",
                workflow_type="advanced",
                schedule="weekly",
                source_id="f1f7b1b2-8e4b-4a2b-8f1d-3e3c7c9e5a3c",
                destination_id="aeebecc7-9d8e-4625-bf1d-815c2f084869",
            ),
        )
    )

    assert update_workflow_response.status_code == 200

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "PUT"
    assert request.url == url

    updated_workflow = update_workflow_response.workflow_information
    assert updated_workflow.id == "16b80fee-64dc-472d-8f26-1d7729b6423d"
    assert updated_workflow.name == "test_workflow"
    assert updated_workflow.workflow_type == "advanced"
    assert updated_workflow.status == "active"
    assert updated_workflow.created_at == datetime.fromisoformat(
        "2025-06-22T11:37:21.648+00:00"
    )
    assert updated_workflow.schedule == shared.WorkflowSchedule(
        crontab_entries=[shared.crontabentry.CronTabEntry(cron_expression="0 0 * * 0")]
    )
    assert updated_workflow.sources == ["f1f7b1b2-8e4b-4a2b-8f1d-3e3c7c9e5a3c"]
    assert updated_workflow.destinations == ["aeebecc7-9d8e-4625-bf1d-815c2f084869"]


def test_run_workflow(httpx_mock, client: UnstructuredClient, platform_api_url: str):
    url = (
        f"{platform_api_url}/api/v1/workflows/16b80fee-64dc-472d-8f26-1d7729b6423d/run"
    )

    httpx_mock.add_response(
        method="POST",
        status_code=202,
        headers={"Content-Type": "application/json"},
        json={
                "created_at": "2025-06-22T11:37:21.648Z",
                "id": "fcdc4994-eea5-425c-91fa-e03f2bd8030d",
                "status": "IN_PROGRESS",
                "runtime": None,
                "workflow_id": "16b80fee-64dc-472d-8f26-1d7729b6423d",
                "workflow_name": "test_workflow",
        },
        url=url,
    )

    run_workflow_response = client.workflows.run_workflow(
        request=operations.RunWorkflowRequest(
            workflow_id="16b80fee-64dc-472d-8f26-1d7729b6423d"
        )
    )

    assert run_workflow_response.status_code == 202

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "POST"
    assert request.url == url

    new_job = run_workflow_response.job_information
    assert new_job.id == "fcdc4994-eea5-425c-91fa-e03f2bd8030d"
    assert new_job.workflow_name == "test_workflow"
    assert new_job.status == "IN_PROGRESS"