"""
Integration test for the complete platform API workflow lifecycle.

This test exercises the full workflow lifecycle:
- List workflows
- Create workflow
- Get workflow
- Delete workflow
- Create job (on-demand)
- Get job
- List jobs
- Get template
- List templates
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

import pytest
from unstructured_client import UnstructuredClient
from unstructured_client.models import shared, operations
from unstructured_client.models.errors import SDKError


@pytest.fixture(scope="module")
def doc_path() -> Path:
    """Get the path to sample documents directory."""
    return Path(__file__).resolve().parents[2] / "_sample_docs"


@pytest.fixture(scope="function")
def platform_client() -> UnstructuredClient:
    """Create a platform API client for integration tests."""
    api_key = os.getenv("UNSTRUCTURED_API_KEY")
    if not api_key:
        pytest.skip("UNSTRUCTURED_API_KEY environment variable not set")
    
    platform_url = os.getenv("PLATFORM_API_URL", "https://platform.unstructuredapp.io")
    
    _client = UnstructuredClient(
        api_key_auth=api_key,
        server_url=platform_url,
    )
    yield _client


@pytest.fixture(scope="function")
def created_workflow_id(platform_client: UnstructuredClient) -> Optional[str]:
    """Fixture to create a workflow and clean it up after the test."""
    workflow_id = None
    try:
        # Create a workflow for testing
        create_response = platform_client.workflows.create_workflow(
            request=operations.CreateWorkflowRequest(
                create_workflow=shared.CreateWorkflow(
                    name="test_integration_workflow",
                    workflow_type="basic",
                )
            )
        )
        assert create_response.status_code == 200
        workflow_id = str(create_response.workflow_information.id)
        yield workflow_id
    finally:
        # Cleanup: delete the workflow if it was created
        # Note: The test itself may delete it, so we check if it still exists
        if workflow_id:
            try:
                # Try to get the workflow first to see if it still exists
                platform_client.workflows.get_workflow(
                    request=operations.GetWorkflowRequest(workflow_id=workflow_id)
                )
                # If we get here, it exists, so delete it
                platform_client.workflows.delete_workflow(
                    request=operations.DeleteWorkflowRequest(workflow_id=workflow_id)
                )
            except SDKError:
                # Workflow already deleted or doesn't exist, ignore
                pass
            except Exception:
                pass  # Ignore other cleanup errors


def test_workflow_lifecycle(
    platform_client: UnstructuredClient,
    created_workflow_id: Optional[str],
    doc_path: Path,
):
    """
    Test the complete workflow lifecycle including workflows, jobs, and templates.
    """
    # 1. List workflows
    list_response = platform_client.workflows.list_workflows(
        request=operations.ListWorkflowsRequest()
    )
    assert list_response.status_code == 200
    assert isinstance(list_response.response_list_workflows, list)
    
    # 2. Get workflow (using the created workflow)
    if created_workflow_id:
        get_response = platform_client.workflows.get_workflow(
            request=operations.GetWorkflowRequest(workflow_id=created_workflow_id)
        )
        assert get_response.status_code == 200
        assert str(get_response.workflow_information.id) == created_workflow_id
        assert get_response.workflow_information.name == "test_integration_workflow"
    
    # 3. List templates
    list_templates_response = platform_client.templates.list_templates(
        request=operations.ListTemplatesRequest()
    )
    assert list_templates_response.status_code == 200
    assert list_templates_response.response_list_templates is not None
    templates = list_templates_response.response_list_templates
    assert isinstance(templates, list)
    assert len(templates) > 0
    
    # Verify we have expected templates
    template_ids = [t.id for t in templates]
    assert "hi_res_partition" in template_ids or "hi_res_and_enrichment" in template_ids
    
    # 4. Get template
    template_id = "hi_res_partition"
    if template_id not in template_ids and len(templates) > 0:
        template_id = templates[0].id
    
    get_template_response = platform_client.templates.get_template(
        request=operations.GetTemplateRequest(template_id=template_id)
    )
    assert get_template_response.status_code == 200
    assert get_template_response.template_detail is not None
    template = get_template_response.template_detail
    assert template.id == template_id
    
    # 5. Create job (on-demand using template)
    request_data = json.dumps({
        "template_id": template_id,
    })
    
    # Read a sample PDF file
    pdf_filename = "layout-parser-paper-fast.pdf"
    pdf_path = doc_path / pdf_filename
    if not pdf_path.exists():
        # Fallback to another common test file
        pdf_filename = "list-item-example-1.pdf"
        pdf_path = doc_path / pdf_filename
    
    with open(pdf_path, "rb") as f:
        pdf_content = f.read()
    
    create_job_response = platform_client.jobs.create_job(
        request=operations.CreateJobRequest(
            body_create_job=shared.BodyCreateJob(
                request_data=request_data,
                input_files=[
                    shared.InputFiles(
                        content=pdf_content,
                        file_name=pdf_filename,
                        content_type="application/pdf",
                    )
                ],
            )
        )
    )
    assert create_job_response.status_code == 200
    job_id = str(create_job_response.job_information.id)
    assert job_id is not None
    assert create_job_response.job_information.status in ["SCHEDULED", "IN_PROGRESS"]
    
    # 6. Get job
    get_job_response = platform_client.jobs.get_job(
        request=operations.GetJobRequest(job_id=job_id)
    )
    assert get_job_response.status_code == 200
    assert str(get_job_response.job_information.id) == job_id
    
    # 7. List jobs
    list_jobs_response = platform_client.jobs.list_jobs(
        request=operations.ListJobsRequest()
    )
    assert list_jobs_response.status_code == 200
    assert isinstance(list_jobs_response.response_list_jobs, list)
    
    # 8. Delete workflow (cleanup is handled by fixture, but we can verify it works)
    if created_workflow_id:
        delete_response = platform_client.workflows.delete_workflow(
            request=operations.DeleteWorkflowRequest(workflow_id=created_workflow_id)
        )
        assert delete_response.status_code in [200, 204]


def test_workflow_lifecycle_with_custom_dag_job(platform_client: UnstructuredClient):
    """
    Test creating a job with a custom DAG (ephemeral job type).
    """
    # 1. List templates to understand the structure
    list_templates_response = platform_client.templates.list_templates(
        request=operations.ListTemplatesRequest()
    )
    assert list_templates_response.status_code == 200
    
    # 2. Create a custom DAG job
    # Using a simple partitioner node
    custom_nodes = [
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
    ]
    
    request_data = json.dumps({
        "job_nodes": custom_nodes,
    })
    
    create_job_response = platform_client.jobs.create_job(
        request=operations.CreateJobRequest(
            body_create_job=shared.BodyCreateJob(
                request_data=request_data,
            )
        )
    )
    assert create_job_response.status_code == 200
    job_id = str(create_job_response.job_information.id)
    assert job_id is not None
    
    # 3. Verify the job can be retrieved
    get_job_response = platform_client.jobs.get_job(
        request=operations.GetJobRequest(job_id=job_id)
    )
    assert get_job_response.status_code == 200
    assert str(get_job_response.job_information.id) == job_id

