from datetime import datetime
from pathlib import Path

import pytest

from unstructured_client import UnstructuredClient
from unstructured_client.models import operations, shared

RETRY_STATUS_CODES = [500, 501, 502, 503, 504, 505]

@pytest.mark.parametrize("status_code", RETRY_STATUS_CODES)
def test_list_jobs_retries(httpx_mock, platform_client: UnstructuredClient, platform_api_url: str, status_code: int):
    url = f"{platform_api_url}/api/v1/jobs/"

    for _ in range(2):
        httpx_mock.add_response(status_code=status_code, method="GET", json=[{"detail": "error"}], url=url)
    httpx_mock.add_response(
        method="GET",
        headers={"Content-Type": "application/json"},
        status_code=200,
        json=[
            {
                "created_at": "2025-06-22T11:37:21.648Z",
                "id": "fcdc4994-eea5-425c-91fa-e03f2bd8030d",
                "status": "COMPLETED",
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
    assert len(requests) == 3
    for request in requests:
        assert request.method == "GET"
        assert request.url == url

    assert len(jobs_response.response_list_jobs) == 1
    job = jobs_response.response_list_jobs[0]
    assert job.id == "fcdc4994-eea5-425c-91fa-e03f2bd8030d"

@pytest.mark.parametrize("status_code", RETRY_STATUS_CODES)
def test_partition_retries(
    httpx_mock,
    serverless_client: UnstructuredClient,
    dummy_partitioned_text: str,
serverless_api_url: str,
    status_code: int,
    doc_path: Path,
):
    url = f"{serverless_api_url}/general/v0/general"
    filename = "layout-parser-paper-fast.pdf"
    file_path = str(doc_path / filename)

    for _ in range(2):
        httpx_mock.add_response(
            status_code=status_code,
            method="POST",
            json=[{"detail": "error"}],
            url=url
        )
    httpx_mock.add_response(
        method="POST",
        headers={"Content-Type": "application/json"},
        content=dummy_partitioned_text.encode(),
        url=url,
    )


    with open(file_path, "rb") as f:

        partition_response = serverless_client.general.partition(
            request=operations.PartitionRequest(
                partition_parameters=shared.PartitionParameters(
                    files=shared.Files(
                        content=f,
                        file_name=filename,
                    ),
                    strategy=shared.Strategy.HI_RES,
                ),
            )
        )

    assert partition_response.status_code == 200

    requests = httpx_mock.get_requests()
    assert len(requests) == 3
    for request in requests:
        assert request.method == "POST"
        assert request.url == url

    assert len(partition_response.elements) > 0
    for element in partition_response.elements:
        assert "text" in element