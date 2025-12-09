from datetime import datetime

import pytest

from unstructured_client import UnstructuredClient
from unstructured_client.models import shared, operations
from unstructured_client.models.errors import SDKError


def test_list_jobs(httpx_mock, platform_client: UnstructuredClient, platform_api_url: str):
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

    jobs_response = platform_client.jobs.list_jobs(request=operations.ListJobsRequest())
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


def test_get_job(httpx_mock, platform_client: UnstructuredClient, platform_api_url: str):
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

    job_response = platform_client.jobs.get_job(
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
    httpx_mock, platform_client: UnstructuredClient, platform_api_url: str
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
        platform_client.jobs.get_job(
            request=operations.GetJobRequest(
                job_id="fcdc4994-eea5-425c-91fa-e03f2bd8030d"
            )
        )

    assert e.value.status_code == 404
    assert "API error occurred" in e.value.message

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "GET"
    assert request.url == url


def test_get_job_error(httpx_mock, platform_client: UnstructuredClient, platform_api_url: str):
    url = f"{platform_api_url}/api/v1/jobs/fcdc4994-eea5-425c-91fa-e03f2bd8030d"

    httpx_mock.add_response(
        method="GET",
        status_code=500,
        headers={"Content-Type": "application/json"},
        json={"detail": "Internal server error"},
        url=url,
        is_reusable=True,
    )

    with pytest.raises(SDKError) as e:
        platform_client.jobs.get_job(
            request=operations.GetJobRequest(
                job_id="fcdc4994-eea5-425c-91fa-e03f2bd8030d"
            )
        )

    assert e.value.status_code == 500
    assert "API error occurred" in e.value.message

    requests = httpx_mock.get_requests()
    assert len(requests) == 4
    request = requests[0]
    assert request.method == "GET"
    assert request.url == url


def test_cancel_job(httpx_mock, platform_client: UnstructuredClient, platform_api_url: str):
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

    cancel_response = platform_client.jobs.cancel_job(
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


def test_create_job(httpx_mock, platform_client: UnstructuredClient, platform_api_url: str):
    url = f"{platform_api_url}/api/v1/jobs/"

    httpx_mock.add_response(
        method="POST",
        status_code=200,
        headers={"Content-Type": "application/json"},
        json={
            "created_at": "2025-06-22T11:37:21.648Z",
            "id": "fcdc4994-eea5-425c-91fa-e03f2bd8030d",
            "status": "SCHEDULED",
            "runtime": None,
            "workflow_id": "16b80fee-64dc-472d-8f26-1d7729b6423d",
            "workflow_name": "job-fcdc4994",
            "input_file_ids": ["upload-test-file-123"],
            "output_node_files": [
                {
                    "node_id": "93fc2ce8-e7c8-424f-a6aa-41460fc5d35d",
                    "file_id": "upload-test-file-123",
                    "node_type": "partition",
                    "node_subtype": "unstructured_api",
                }
            ],
            "job_type": "template",
        },
        url=url,
    )

    create_job_response = platform_client.jobs.create_job(
        request=operations.CreateJobRequest(
            body_create_job=shared.BodyCreateJob(
                job_type="template",
                template_id="hi_res_partition",
            )
        )
    )
    assert create_job_response.status_code == 200

    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "POST"
    assert request.url == url

    job = create_job_response.job_information
    assert job.id == "fcdc4994-eea5-425c-91fa-e03f2bd8030d"
    assert job.status == "SCHEDULED"
    assert job.job_type == "template"
    assert job.created_at == datetime.fromisoformat("2025-06-22T11:37:21.648+00:00")
