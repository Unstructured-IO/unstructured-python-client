import json
import re
from datetime import datetime
from urllib.parse import parse_qs

import pytest
from pydantic import ValidationError

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


def _job(job_id: str, status: str) -> dict:
    return {
        "created_at": "2025-06-22T11:37:21.648Z",
        "id": job_id,
        "status": status,
        "runtime": None,
        "workflow_id": "16b80fee-64dc-472d-8f26-1d7729b6423d",
        "workflow_name": "test_workflow",
    }


def test_get_job_rejected(httpx_mock, platform_client: UnstructuredClient, platform_api_url: str):
    """A preflight-rejected job deserializes instead of raising."""
    job_id = "fcdc4994-eea5-425c-91fa-e03f2bd8030d"
    url = f"{platform_api_url}/api/v1/jobs/{job_id}"

    httpx_mock.add_response(
        method="GET",
        headers={"Content-Type": "application/json"},
        json=_job(job_id, "REJECTED"),
        url=url,
    )

    job_response = platform_client.jobs.get_job(
        request=operations.GetJobRequest(job_id=job_id)
    )
    assert job_response.status_code == 200
    assert job_response.job_information.status == shared.JobStatus.REJECTED


def test_list_jobs_mixed_page_with_rejected(
    httpx_mock, platform_client: UnstructuredClient, platform_api_url: str
):
    """One rejected job must not fail the whole page - the page is validated as one list."""
    url = f"{platform_api_url}/api/v1/jobs/"

    httpx_mock.add_response(
        method="GET",
        headers={"Content-Type": "application/json"},
        json=[
            _job("fcdc4994-eea5-425c-91fa-e03f2bd8030d", "IN_PROGRESS"),
            _job("2b1e7f10-0d9a-4f4d-9d1e-6c9f0a1b2c3d", "REJECTED"),
            _job("3c2f8a21-1e0b-5a5e-8e2f-7d0a1b2c3d4e", "COMPLETED"),
        ],
        url=url,
    )

    jobs_response = platform_client.jobs.list_jobs(request=operations.ListJobsRequest())
    assert jobs_response.status_code == 200

    statuses = [job.status for job in jobs_response.response_list_jobs]
    assert statuses == [
        shared.JobStatus.IN_PROGRESS,
        shared.JobStatus.REJECTED,
        shared.JobStatus.COMPLETED,
    ]


def test_get_job_details_rejected(
    httpx_mock, platform_client: UnstructuredClient, platform_api_url: str
):
    """processing_status is a second closed enum that REJECTED must not break."""
    job_id = "fcdc4994-eea5-425c-91fa-e03f2bd8030d"
    url = f"{platform_api_url}/api/v1/jobs/{job_id}/details"

    httpx_mock.add_response(
        method="GET",
        headers={"Content-Type": "application/json"},
        json={"id": job_id, "processing_status": "REJECTED", "node_stats": []},
        url=url,
    )

    details_response = platform_client.jobs.get_job_details(
        request=operations.GetJobDetailsRequest(job_id=job_id)
    )
    assert details_response.status_code == 200
    assert (
        details_response.job_details.processing_status
        == shared.JobProcessingStatus.REJECTED
    )


@pytest.mark.parametrize("unknown_status", ["PAUSED", "SOME_FUTURE_STATUS"])
def test_list_jobs_tolerates_unknown_status(
    httpx_mock,
    platform_client: UnstructuredClient,
    platform_api_url: str,
    unknown_status: str,
):
    """A status added server-side after this release must not break the client.

    The raw value is preserved, so callers can log exactly what the server sent.
    """
    url = f"{platform_api_url}/api/v1/jobs/"

    httpx_mock.add_response(
        method="GET",
        headers={"Content-Type": "application/json"},
        json=[
            _job("fcdc4994-eea5-425c-91fa-e03f2bd8030d", "IN_PROGRESS"),
            _job("2b1e7f10-0d9a-4f4d-9d1e-6c9f0a1b2c3d", unknown_status),
        ],
        url=url,
    )

    jobs_response = platform_client.jobs.list_jobs(request=operations.ListJobsRequest())
    assert jobs_response.status_code == 200

    unknown = jobs_response.response_list_jobs[1].status
    assert unknown.value == unknown_status
    assert isinstance(unknown, shared.JobStatus)
    # The unknown value must not leak into the declared member set.
    assert unknown_status not in shared.JobStatus.__members__


def _sent_field_names(httpx_mock) -> set[str]:
    """Every form field name the SDK sent, for either encoding."""
    request = httpx_mock.get_requests()[0]
    body = request.read().decode()
    if "multipart/form-data" in request.headers.get("content-type", ""):
        # (?<!file) matters: `filename="a.pdf"` contains `name="a.pdf"`, so a naive pattern
        # reports filenames as field names.
        return set(re.findall(r'(?<!file)name="([^"]+)"', body))
    return set(parse_qs(body))


def _sent_request_data(httpx_mock) -> str:
    """Pull the `request_data` form field out of the body the SDK actually sent.

    Handles both encodings: httpx sends `multipart/form-data` once there is a file part and
    falls back to `application/x-www-form-urlencoded` when the body is fields only.
    """
    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    request = requests[0]
    body = request.read().decode()

    if "multipart/form-data" in request.headers.get("content-type", ""):
        match = re.search(r'name="request_data"\r\n\r\n(.*?)\r\n--', body, re.DOTALL)
        assert match, f"no request_data part in multipart body: {body!r}"
        return match.group(1)

    fields = parse_qs(body)
    assert "request_data" in fields, f"no request_data field in body: {body!r}"
    return fields["request_data"][0]


def _mock_create_job(httpx_mock, platform_api_url: str) -> None:
    httpx_mock.add_response(
        method="POST",
        headers={"Content-Type": "application/json"},
        json=_job("fcdc4994-eea5-425c-91fa-e03f2bd8030d", "IN_PROGRESS"),
        url=f"{platform_api_url}/api/v1/jobs/",
    )


@pytest.mark.parametrize("skip_preflight", [True, False])
def test_create_job_folds_skip_preflight_into_request_data(
    httpx_mock,
    platform_client: UnstructuredClient,
    platform_api_url: str,
    skip_preflight: bool,
):
    """`skip_preflight` rides inside the `request_data` JSON, not as its own form field.

    The spec types the multipart field as a plain string and describes the payload only in
    `contentSchema`, so this is the only place the server reads it.
    """
    _mock_create_job(httpx_mock, platform_api_url)

    platform_client.jobs.create_job(
        request=operations.CreateJobRequest(
            body_create_job=shared.BodyCreateJob(
                request_data=json.dumps({"template_id": "some-template"}),
                skip_preflight=skip_preflight,
            )
        )
    )

    assert json.loads(_sent_request_data(httpx_mock)) == {
        "template_id": "some-template",
        "skip_preflight": skip_preflight,
    }
    # It must not also appear as a form field of its own. Assert on the parsed field names
    # rather than a substring of the encoded body, which would pass by coincidence.
    assert _sent_field_names(httpx_mock) == {"request_data"}


def test_create_job_leaves_request_data_untouched_when_unset(
    httpx_mock, platform_client: UnstructuredClient, platform_api_url: str
):
    """Unset means the caller's string is passed through byte for byte."""
    _mock_create_job(httpx_mock, platform_api_url)
    request_data = '{"template_id":"some-template"}'

    platform_client.jobs.create_job(
        request=operations.CreateJobRequest(
            body_create_job=shared.BodyCreateJob(request_data=request_data)
        )
    )

    assert _sent_request_data(httpx_mock) == request_data


def test_create_job_skip_preflight_param_overrides_json(
    httpx_mock, platform_client: UnstructuredClient, platform_api_url: str
):
    """The explicit parameter wins over a value already in the JSON string."""
    _mock_create_job(httpx_mock, platform_api_url)

    platform_client.jobs.create_job(
        request=operations.CreateJobRequest(
            body_create_job=shared.BodyCreateJob(
                request_data='{"template_id":"some-template","skip_preflight":true}',
                skip_preflight=False,
            )
        )
    )

    assert json.loads(_sent_request_data(httpx_mock))["skip_preflight"] is False


def test_create_job_skip_preflight_requires_json_object_request_data():
    """A non-JSON `request_data` cannot carry the flag, so say so at construction time."""
    with pytest.raises(ValidationError, match="must be a JSON object"):
        shared.BodyCreateJob(request_data="not json at all", skip_preflight=True)

    with pytest.raises(ValidationError, match="must be a JSON object"):
        shared.BodyCreateJob(request_data="[1, 2, 3]", skip_preflight=True)


def test_create_job_typed_dict_path_folds_skip_preflight(
    httpx_mock, platform_client: UnstructuredClient, platform_api_url: str
):
    """The TypedDict request shape routes through `utils.unmarshal`, so the validator still runs."""
    _mock_create_job(httpx_mock, platform_api_url)

    platform_client.jobs.create_job(
        request={
            "body_create_job": {
                "request_data": '{"template_id":"some-template"}',
                "skip_preflight": True,
            }
        }
    )

    assert json.loads(_sent_request_data(httpx_mock))["skip_preflight"] is True


def test_create_job_folds_skip_preflight_with_input_files(
    httpx_mock, platform_client: UnstructuredClient, platform_api_url: str
):
    """The real production shape: a file upload, which switches the body to multipart.

    Without a file part httpx sends urlencoded, so this is the only test that exercises the
    multipart branch - and it is the branch where "not a form field of its own" matters most,
    since a stray part would be indistinguishable from a real one.
    """
    _mock_create_job(httpx_mock, platform_api_url)

    platform_client.jobs.create_job(
        request=operations.CreateJobRequest(
            body_create_job=shared.BodyCreateJob(
                request_data=json.dumps({"job_nodes": []}),
                input_files=[
                    shared.InputFiles(
                        content=b"hello",
                        file_name="a.pdf",
                        content_type="application/pdf",
                    )
                ],
                skip_preflight=True,
            )
        )
    )

    request = httpx_mock.get_requests()[0]
    assert "multipart/form-data" in request.headers["content-type"]
    assert json.loads(_sent_request_data(httpx_mock)) == {
        "job_nodes": [],
        "skip_preflight": True,
    }
    assert _sent_field_names(httpx_mock) == {"request_data", "input_files[]"}


def test_create_job_preserves_high_precision_numbers_on_the_wire(
    httpx_mock, platform_client: UnstructuredClient, platform_api_url: str
):
    """Byte preservation has to survive form encoding, not just the model.

    The model-level fidelity tests assert on `body.request_data`. This one reads the value back
    out of the encoded request body, which is what the server actually parses.
    """
    _mock_create_job(httpx_mock, platform_api_url)
    # More precision than a float64 holds, plus an exponent form and a significant trailing zero.
    request_data = '{"job_nodes":[{"threshold":0.123456789012345678901,"scale":1e5,"pad":1.50}]}'

    platform_client.jobs.create_job(
        request=operations.CreateJobRequest(
            body_create_job=shared.BodyCreateJob(
                request_data=request_data, skip_preflight=True
            )
        )
    )

    sent = _sent_request_data(httpx_mock)
    for literal in ("0.123456789012345678901", "1e5", "1.50"):
        assert literal in sent, f"{literal} was rewritten on the wire: {sent!r}"
    assert json.loads(sent)["skip_preflight"] is True


def test_create_job_with_files_and_flag_survives_reassignment(
    httpx_mock, platform_client: UnstructuredClient, platform_api_url: str
):
    """Multipart + fold + idempotency together.

    Each is covered alone; this is the combination a real caller hits when they build a body,
    attach files, then adjust the flag before sending.
    """
    _mock_create_job(httpx_mock, platform_api_url)

    body = shared.BodyCreateJob(
        request_data='{"job_nodes":[],"scale":1e5}',
        input_files=[
            shared.InputFiles(
                content=b"hello", file_name="a.pdf", content_type="application/pdf"
            )
        ],
        skip_preflight=True,
    )
    # Attaching more files must not disturb the already-folded payload.
    body.input_files = list(body.input_files) + [
        shared.InputFiles(
            content=b"world", file_name="b.pdf", content_type="application/pdf"
        )
    ]
    assert "1e5" in body.request_data, "an unrelated assignment reformatted request_data"

    # Flipping the flag must land the new value.
    body.skip_preflight = False

    platform_client.jobs.create_job(
        request=operations.CreateJobRequest(body_create_job=body)
    )

    request = httpx_mock.get_requests()[0]
    assert "multipart/form-data" in request.headers["content-type"]
    assert json.loads(_sent_request_data(httpx_mock))["skip_preflight"] is False
    assert _sent_field_names(httpx_mock) == {"request_data", "input_files[]"}


def test_create_job_reusing_one_body_sends_the_value_set_at_call_time(
    httpx_mock, platform_client: UnstructuredClient, platform_api_url: str
):
    """A reused body is mutable, so each call must carry whatever was set before it.

    Deterministic stand-in for the shared-mutable-state hazard: the model folds on assignment,
    so a body shared across calls is only safe if callers mutate it between them, never during.
    """
    url = f"{platform_api_url}/api/v1/jobs/"
    for _ in range(2):
        httpx_mock.add_response(
            method="POST",
            headers={"Content-Type": "application/json"},
            json=_job("fcdc4994-eea5-425c-91fa-e03f2bd8030d", "IN_PROGRESS"),
            url=url,
        )

    body = shared.BodyCreateJob(request_data='{"job_nodes":[]}', skip_preflight=True)
    platform_client.jobs.create_job(
        request=operations.CreateJobRequest(body_create_job=body)
    )
    body.skip_preflight = False
    platform_client.jobs.create_job(
        request=operations.CreateJobRequest(body_create_job=body)
    )

    requests = httpx_mock.get_requests()
    assert len(requests) == 2
    sent = [
        json.loads(parse_qs(r.read().decode())["request_data"][0])["skip_preflight"]
        for r in requests
    ]
    assert sent == [True, False]
