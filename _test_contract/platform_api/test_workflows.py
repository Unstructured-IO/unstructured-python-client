import json
from datetime import datetime

import pytest

from unstructured_client import UnstructuredClient
from unstructured_client.models import shared, operations
from unstructured_client.models.errors import UnstructuredClientError


def test_list_workflows(httpx_mock, platform_client: UnstructuredClient, platform_api_url: str):
    url = f"{platform_api_url}/api/v1/workflows/?sort_by=id"

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

    workflows_response = platform_client.workflows.list_workflows(
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
    httpx_mock, platform_client: UnstructuredClient, platform_api_url: str
):
    url = f"{platform_api_url}/api/v1/workflows/?sort_by=id"

    httpx_mock.add_response(
        method="GET",
        url=url,
        json=[],
    )

    workflows_response = platform_client.workflows.list_workflows(
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
    platform_client: UnstructuredClient,
    platform_api_url: str,
    error_status_code: int,
):
    url = f"{platform_api_url}/api/v1/workflows/?sort_by=id"

    httpx_mock.add_response(
        method="GET",
        url=url,
        status_code=error_status_code,
    )

    with pytest.raises(UnstructuredClientError) as error:
        platform_client.workflows.list_workflows(request=operations.ListWorkflowsRequest())
    assert error.value.status_code == error_status_code
    assert "API error occurred" in error.value.message


def test_create_workflow(httpx_mock, platform_client: UnstructuredClient, platform_api_url: str):
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

    create_workflow_response = platform_client.workflows.create_workflow(
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


def test_update_workflow(httpx_mock, platform_client: UnstructuredClient, platform_api_url: str):
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

    update_workflow_response = platform_client.workflows.update_workflow(
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


def test_run_workflow(httpx_mock, platform_client: UnstructuredClient, platform_api_url: str):
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

    run_workflow_response = platform_client.workflows.run_workflow(
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

WORKFLOW_ID = "16b80fee-64dc-472d-8f26-1d7729b6423d"


def _workflow_json(**overrides) -> dict:
    payload = {
        "created_at": "2025-06-22T11:37:21.648Z",
        "destinations": ["aeebecc7-9d8e-4625-bf1d-815c2f084869"],
        "id": WORKFLOW_ID,
        "name": "test_workflow",
        "sources": ["f1f7b1b2-8e4b-4a2b-8f1d-3e3c7c9e5a3c"],
        "workflow_nodes": [],
        "status": "active",
        "workflow_type": "advanced",
    }
    payload.update(overrides)
    return payload


def _sent_body(httpx_mock) -> dict:
    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    return json.loads(requests[0].read())


@pytest.mark.parametrize(
    ("skip_preflight", "expected"),
    [(True, True), (False, False)],
)
def test_create_workflow_sends_skip_preflight(
    httpx_mock,
    platform_client: UnstructuredClient,
    platform_api_url: str,
    skip_preflight: bool,
    expected: bool,
):
    """An explicit value reaches the wire, `False` included."""
    httpx_mock.add_response(
        method="POST",
        url=f"{platform_api_url}/api/v1/workflows/",
        status_code=200,
        json=_workflow_json(skip_preflight=skip_preflight),
    )

    platform_client.workflows.create_workflow(
        request=operations.CreateWorkflowRequest(
            create_workflow=shared.CreateWorkflow(
                name="test_workflow",
                workflow_type="advanced",
                skip_preflight=skip_preflight,
            )
        )
    )

    assert _sent_body(httpx_mock)["skip_preflight"] is expected


def test_create_workflow_omits_skip_preflight_when_unset(
    httpx_mock, platform_client: UnstructuredClient, platform_api_url: str
):
    """Unset must be *absent*, not `false`.

    Regression guard for the `optional_fields` list in `CreateWorkflow.serialize_model`: leave
    `skip_preflight` out of it and the serializer emits the field on every create call.
    """
    httpx_mock.add_response(
        method="POST",
        url=f"{platform_api_url}/api/v1/workflows/",
        status_code=200,
        json=_workflow_json(),
    )

    platform_client.workflows.create_workflow(
        request=operations.CreateWorkflowRequest(
            create_workflow=shared.CreateWorkflow(
                name="test_workflow", workflow_type="advanced"
            )
        )
    )

    assert "skip_preflight" not in _sent_body(httpx_mock)


@pytest.mark.parametrize("skip_preflight", [True, False])
def test_update_workflow_sends_skip_preflight(
    httpx_mock,
    platform_client: UnstructuredClient,
    platform_api_url: str,
    skip_preflight: bool,
):
    """`False` must be sent, not dropped - it is how a caller opts back in to preflight."""
    httpx_mock.add_response(
        method="PUT",
        url=f"{platform_api_url}/api/v1/workflows/{WORKFLOW_ID}",
        status_code=200,
        json=_workflow_json(skip_preflight=skip_preflight),
    )

    platform_client.workflows.update_workflow(
        request=operations.UpdateWorkflowRequest(
            workflow_id=WORKFLOW_ID,
            update_workflow=shared.UpdateWorkflow(skip_preflight=skip_preflight),
        )
    )

    assert _sent_body(httpx_mock)["skip_preflight"] is skip_preflight


def test_update_workflow_omits_skip_preflight_when_unset(
    httpx_mock, platform_client: UnstructuredClient, platform_api_url: str
):
    """Omitted means "leave unchanged" server-side, so an unrelated update must not send it."""
    httpx_mock.add_response(
        method="PUT",
        url=f"{platform_api_url}/api/v1/workflows/{WORKFLOW_ID}",
        status_code=200,
        json=_workflow_json(skip_preflight=True),
    )

    platform_client.workflows.update_workflow(
        request=operations.UpdateWorkflowRequest(
            workflow_id=WORKFLOW_ID,
            update_workflow=shared.UpdateWorkflow(name="renamed"),
        )
    )

    body = _sent_body(httpx_mock)
    assert body == {"name": "renamed"}


@pytest.mark.parametrize(
    ("response_json", "expected"),
    [
        (_workflow_json(skip_preflight=True), True),
        (_workflow_json(skip_preflight=False), False),
        # Absent in the response - defaults to False rather than None.
        (_workflow_json(), False),
    ],
)
def test_workflow_information_reads_skip_preflight(
    httpx_mock,
    platform_client: UnstructuredClient,
    platform_api_url: str,
    response_json: dict,
    expected: bool,
):
    """The response echo must be readable.

    Without the field on the model, `extra="ignore"` silently drops what the server sent and a
    caller cannot tell whether preflight is skipped.
    """
    httpx_mock.add_response(
        method="GET",
        url=f"{platform_api_url}/api/v1/workflows/{WORKFLOW_ID}",
        status_code=200,
        json=response_json,
    )

    response = platform_client.workflows.get_workflow(
        request=operations.GetWorkflowRequest(workflow_id=WORKFLOW_ID)
    )

    assert response.workflow_information.skip_preflight is expected


def test_update_workflow_skip_preflight_only_sends_nothing_else(
    httpx_mock, platform_client: UnstructuredClient, platform_api_url: str
):
    """A partial update must carry *only* what the caller set.

    The other tests assert the key is present. This one asserts nothing else leaked in, which is
    what makes "omit means unchanged" safe: any extra key here would overwrite server state the
    caller never mentioned.
    """
    httpx_mock.add_response(
        method="PUT",
        url=f"{platform_api_url}/api/v1/workflows/{WORKFLOW_ID}",
        status_code=200,
        json=_workflow_json(skip_preflight=True),
    )

    platform_client.workflows.update_workflow(
        request=operations.UpdateWorkflowRequest(
            workflow_id=WORKFLOW_ID,
            update_workflow=shared.UpdateWorkflow(skip_preflight=True),
        )
    )

    assert _sent_body(httpx_mock) == {"skip_preflight": True}
