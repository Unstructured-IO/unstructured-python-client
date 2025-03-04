from datetime import datetime

import pytest

from unstructured_client import UnstructuredClient
from unstructured_client.models import shared, operations
from unstructured_client.models.errors import SDKError


def test_list_jobs(httpx_mock, client: UnstructuredClient, platform_api_url: str):
    url = f"{platform_api_url}/api/v1/jobs/"

    httpx_mock.add_response(
        method="GET",
        headers={"Content-Type": "application/json"},
        json=[
            {
                "created_at": "2025-06-22T11:37:21.648Z",
                "id": "fcdc4994-eea5-425c-91fa-e03f2bd8030d",
                "status": "IN_PROGRESS",
                "runtime": None,
                "workflow_id": "16b80fee-64dc-472d-8f26-1d7729b6423d",
                "workflow_name": "test_workflow",
            }
        ],
        url=url,
    )

    jobs_response = client.jobs.list_jobs(request=operations.ListJobsRequest())
    assert jobs_response.status_code == 200

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "GET"
    assert request.url == url

    assert len(jobs_response.response_list_jobs) == 1
    job = jobs_response.response_list_jobs[0]
    assert job.id == "fcdc4994-eea5-425c-91fa-e03f2bd8030d"
    assert job.workflow_id == "16b80fee-64dc-472d-8f26-1d7729b6423d"
    assert job.workflow_name == "test_workflow"
    assert job.status == "IN_PROGRESS"
    assert job.created_at == datetime.fromisoformat("2025-06-22T11:37:21.648+00:00")


def test_get_job(httpx_mock, client: UnstructuredClient, platform_api_url: str):
    url = f"{platform_api_url}/api/v1/jobs/fcdc4994-eea5-425c-91fa-e03f2bd8030d"

    httpx_mock.add_response(
        method="GET",
        headers={"Content-Type": "application/json"},
        json={
            "created_at": "2025-06-22T11:37:21.648Z",
            "id": "fcdc4994-eea5-425c-91fa-e03f2bd8030d",
            "status": "SCHEDULED",
            "runtime": None,
            "workflow_id": "16b80fee-64dc-472d-8f26-1d7729b6423d",
            "workflow_name": "test_workflow",
        },
        url=url,
    )

    job_response = client.jobs.get_job(
        request=operations.GetJobRequest(job_id="fcdc4994-eea5-425c-91fa-e03f2bd8030d")
    )
    assert job_response.status_code == 200

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "GET"
    assert request.url == url

    job = job_response.job_information
    assert job.id == "fcdc4994-eea5-425c-91fa-e03f2bd8030d"
    assert job.workflow_id == "16b80fee-64dc-472d-8f26-1d7729b6423d"
    assert job.workflow_name == "test_workflow"
    assert job.status == "SCHEDULED"
    assert job.created_at == datetime.fromisoformat("2025-06-22T11:37:21.648+00:00")


def test_get_job_not_found(
    httpx_mock, client: UnstructuredClient, platform_api_url: str
):
    url = f"{platform_api_url}/api/v1/jobs/fcdc4994-eea5-425c-91fa-e03f2bd8030d"

    httpx_mock.add_response(
        method="GET",
        status_code=404,
        headers={"Content-Type": "application/json"},
        json={"detail": "Job not found"},
        url=url,
    )

    with pytest.raises(SDKError) as e:
        client.jobs.get_job(
            request=operations.GetJobRequest(
                job_id="fcdc4994-eea5-425c-91fa-e03f2bd8030d"
            )
        )

    assert e.value.status_code == 404
    assert e.value.message == "API error occurred"

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "GET"
    assert request.url == url


def test_get_job_error(httpx_mock, client: UnstructuredClient, platform_api_url: str):
    url = f"{platform_api_url}/api/v1/jobs/fcdc4994-eea5-425c-91fa-e03f2bd8030d"

    httpx_mock.add_response(
        method="GET",
        status_code=500,
        headers={"Content-Type": "application/json"},
        json={"detail": "Internal server error"},
        url=url,
    )

    with pytest.raises(SDKError) as e:
        client.jobs.get_job(
            request=operations.GetJobRequest(
                job_id="fcdc4994-eea5-425c-91fa-e03f2bd8030d"
            )
        )

    assert e.value.status_code == 500
    assert e.value.message == "API error occurred"

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "GET"
    assert request.url == url


def test_cancel_job(httpx_mock, client: UnstructuredClient, platform_api_url: str):
    url = f"{platform_api_url}/api/v1/jobs/fcdc4994-eea5-425c-91fa-e03f2bd8030d/cancel"

    httpx_mock.add_response(
        method="POST",
        status_code=200,
        url=url,
        json={
            "id": "fcdc4994-eea5-425c-91fa-e03f2bd8030d",
            "status": "cancelled",
            "message": "Job successfully cancelled.",
        },
    )

    cancel_response = client.jobs.cancel_job(
        request=operations.CancelJobRequest(
            job_id="fcdc4994-eea5-425c-91fa-e03f2bd8030d"
        )
    )
    assert cancel_response.status_code == 200

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "POST"
    assert request.url == url
