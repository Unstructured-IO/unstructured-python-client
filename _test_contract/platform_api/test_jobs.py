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
    import json

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

    # request_data should be a JSON string containing the job creation data
    request_data = json.dumps({
        "template_id": "hi_res_partition",
    })

    create_job_response = platform_client.jobs.create_job(
        request=operations.CreateJobRequest(
            body_create_job=shared.BodyCreateJob(
                request_data=request_data,
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


def test_list_jobs_tolerates_rejected_and_unrecognized_statuses(
    httpx_mock, platform_client: UnstructuredClient, platform_api_url: str
):
    url = f"{platform_api_url}/api/v1/jobs/"

    def job(job_id: str, status: str) -> dict:
        return {
            "created_at": "2025-06-22T11:37:21.648Z",
            "id": job_id,
            "status": status,
            "workflow_id": "16b80fee-64dc-472d-8f26-1d7729b6423d",
            "workflow_name": "test_workflow",
        }

    httpx_mock.add_response(
        method="GET",
        headers={"Content-Type": "application/json"},
        json=[
            job("fcdc4994-eea5-425c-91fa-e03f2bd8030d", "REJECTED"),
            job("a1b2c3d4-eea5-425c-91fa-e03f2bd8030d", "SOME_FUTURE_STATUS"),
            job("b2c3d4e5-eea5-425c-91fa-e03f2bd8030d", "COMPLETED"),
        ],
        url=url,
    )

    jobs = platform_client.jobs.list_jobs(request=operations.ListJobsRequest()).response_list_jobs

    assert jobs[0].status is shared.JobStatus.REJECTED
    assert type(jobs[1].status) is str
    assert jobs[1].status == "SOME_FUTURE_STATUS"
    assert jobs[2].status is shared.JobStatus.COMPLETED


@pytest.mark.parametrize(
    ("processing_status", "expected"),
    [
        ("REJECTED", shared.JobProcessingStatus.REJECTED),
        ("SOME_FUTURE_STATUS", "SOME_FUTURE_STATUS"),
    ],
)
def test_get_job_details_tolerates_rejected_and_unrecognized_statuses(
    httpx_mock,
    platform_client: UnstructuredClient,
    platform_api_url: str,
    processing_status: str,
    expected,
):
    url = f"{platform_api_url}/api/v1/jobs/fcdc4994-eea5-425c-91fa-e03f2bd8030d/details"

    httpx_mock.add_response(
        method="GET",
        headers={"Content-Type": "application/json"},
        json={
            "id": "fcdc4994-eea5-425c-91fa-e03f2bd8030d",
            "node_stats": [],
            "processing_status": processing_status,
        },
        url=url,
    )

    details = platform_client.jobs.get_job_details(
        request=operations.GetJobDetailsRequest(job_id="fcdc4994-eea5-425c-91fa-e03f2bd8030d")
    ).job_details

    assert details.processing_status == expected
    assert type(details.processing_status) is type(expected)


def test_get_job_details_exposes_preflight_failure(
    httpx_mock, platform_client: UnstructuredClient, platform_api_url: str
):
    url = f"{platform_api_url}/api/v1/jobs/fcdc4994-eea5-425c-91fa-e03f2bd8030d/details"

    def node(name: str, **failure) -> dict:
        return {
            "node_name": name,
            "ready": 0,
            "in_progress": 0,
            "success": 0,
            "failure": 0,
            **failure,
        }

    httpx_mock.add_response(
        method="GET",
        headers={"Content-Type": "application/json"},
        json={
            "id": "fcdc4994-eea5-425c-91fa-e03f2bd8030d",
            "processing_status": "REJECTED",
            "node_stats": [
                node(
                    "s3-source",
                    failure_category="AUTH_INVALID_CREDENTIAL",
                    failure_reason="The AWS Access Key Id you provided does not exist.",
                ),
                node("future-destination", failure_category="SOME_FUTURE_CATEGORY"),
                node("partitioner", failure_category=None, failure_reason=None),
            ],
        },
        url=url,
    )

    details = platform_client.jobs.get_job_details(
        request=operations.GetJobDetailsRequest(job_id="fcdc4994-eea5-425c-91fa-e03f2bd8030d")
    ).job_details

    source, destination, partitioner = details.node_stats
    assert source.failure_category is shared.PreflightFailureCategory.AUTH_INVALID_CREDENTIAL
    assert source.failure_reason == "The AWS Access Key Id you provided does not exist."
    assert type(destination.failure_category) is str
    assert destination.failure_category == "SOME_FUTURE_CATEGORY"
    assert partitioner.failure_category is None
    assert partitioner.failure_reason is None
