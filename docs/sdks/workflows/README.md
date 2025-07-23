# Workflows
(*workflows*)

## Overview

### Available Operations

* [create_workflow](#create_workflow) - Create Workflow
* [delete_workflow](#delete_workflow) - Delete Workflow
* [get_workflow](#get_workflow) - Get Workflow
* [list_workflows](#list_workflows) - List Workflows
* [run_workflow](#run_workflow) - Run Workflow
* [update_workflow](#update_workflow) - Update Workflow

## create_workflow

Create a new workflow, either custom or auto, and configure its settings.

### Example Usage

```python
from unstructured_client import UnstructuredClient
from unstructured_client.models import shared


with UnstructuredClient() as uc_client:

    res = uc_client.workflows.create_workflow(request={
        "create_workflow": {
            "name": "<value>",
            "workflow_type": shared.WorkflowType.ADVANCED,
        },
    })

    assert res.workflow_information is not None

    # Handle response
    print(res.workflow_information)

```

### Parameters

| Parameter                                                                            | Type                                                                                 | Required                                                                             | Description                                                                          |
| ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------ |
| `request`                                                                            | [operations.CreateWorkflowRequest](../../models/operations/createworkflowrequest.md) | :heavy_check_mark:                                                                   | The request object to use for the request.                                           |
| `retries`                                                                            | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                     | :heavy_minus_sign:                                                                   | Configuration to override the default retry behavior of the client.                  |

### Response

**[operations.CreateWorkflowResponse](../../models/operations/createworkflowresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

## delete_workflow

Delete a workflow by its ID.

### Example Usage

```python
from unstructured_client import UnstructuredClient


with UnstructuredClient() as uc_client:

    res = uc_client.workflows.delete_workflow(request={
        "workflow_id": "3e61b8a6-32b6-47cf-bce7-6d13357b30eb",
    })

    assert res.any is not None

    # Handle response
    print(res.any)

```

### Parameters

| Parameter                                                                            | Type                                                                                 | Required                                                                             | Description                                                                          |
| ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------ |
| `request`                                                                            | [operations.DeleteWorkflowRequest](../../models/operations/deleteworkflowrequest.md) | :heavy_check_mark:                                                                   | The request object to use for the request.                                           |
| `retries`                                                                            | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                     | :heavy_minus_sign:                                                                   | Configuration to override the default retry behavior of the client.                  |

### Response

**[operations.DeleteWorkflowResponse](../../models/operations/deleteworkflowresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

## get_workflow

Retrieve detailed information for a specific workflow by its ID.

### Example Usage

```python
from unstructured_client import UnstructuredClient


with UnstructuredClient() as uc_client:

    res = uc_client.workflows.get_workflow(request={
        "workflow_id": "d031b0e5-7ca7-4a2b-b3cc-d869d2df3e76",
    })

    assert res.workflow_information is not None

    # Handle response
    print(res.workflow_information)

```

### Parameters

| Parameter                                                                      | Type                                                                           | Required                                                                       | Description                                                                    |
| ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------ |
| `request`                                                                      | [operations.GetWorkflowRequest](../../models/operations/getworkflowrequest.md) | :heavy_check_mark:                                                             | The request object to use for the request.                                     |
| `retries`                                                                      | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)               | :heavy_minus_sign:                                                             | Configuration to override the default retry behavior of the client.            |

### Response

**[operations.GetWorkflowResponse](../../models/operations/getworkflowresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

## list_workflows

Retrieve a list of workflows, optionally filtered by source, destination, state, name, date range, and supports pagination and sorting.

### Example Usage

```python
from unstructured_client import UnstructuredClient


with UnstructuredClient() as uc_client:

    res = uc_client.workflows.list_workflows(request={})

    assert res.response_list_workflows is not None

    # Handle response
    print(res.response_list_workflows)

```

### Parameters

| Parameter                                                                          | Type                                                                               | Required                                                                           | Description                                                                        |
| ---------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `request`                                                                          | [operations.ListWorkflowsRequest](../../models/operations/listworkflowsrequest.md) | :heavy_check_mark:                                                                 | The request object to use for the request.                                         |
| `retries`                                                                          | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                   | :heavy_minus_sign:                                                                 | Configuration to override the default retry behavior of the client.                |

### Response

**[operations.ListWorkflowsResponse](../../models/operations/listworkflowsresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

## run_workflow

Run a workflow by triggering a new job if none is currently active.

### Example Usage

```python
from unstructured_client import UnstructuredClient


with UnstructuredClient() as uc_client:

    res = uc_client.workflows.run_workflow(request={
        "workflow_id": "e7054f23-ce92-4bf1-a1d7-7cf9cb14d013",
    })

    assert res.job_information is not None

    # Handle response
    print(res.job_information)

```

### Parameters

| Parameter                                                                      | Type                                                                           | Required                                                                       | Description                                                                    |
| ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------ |
| `request`                                                                      | [operations.RunWorkflowRequest](../../models/operations/runworkflowrequest.md) | :heavy_check_mark:                                                             | The request object to use for the request.                                     |
| `retries`                                                                      | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)               | :heavy_minus_sign:                                                             | Configuration to override the default retry behavior of the client.            |

### Response

**[operations.RunWorkflowResponse](../../models/operations/runworkflowresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

## update_workflow

Update an existing workflow's name, connectors, schedule, or workflow type.

### Example Usage

```python
from unstructured_client import UnstructuredClient


with UnstructuredClient() as uc_client:

    res = uc_client.workflows.update_workflow(request={
        "update_workflow": {},
        "workflow_id": "b9b7e688-353f-4ff2-bcd7-a49b5fa5f6c7",
    })

    assert res.workflow_information is not None

    # Handle response
    print(res.workflow_information)

```

### Parameters

| Parameter                                                                            | Type                                                                                 | Required                                                                             | Description                                                                          |
| ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------ |
| `request`                                                                            | [operations.UpdateWorkflowRequest](../../models/operations/updateworkflowrequest.md) | :heavy_check_mark:                                                                   | The request object to use for the request.                                           |
| `retries`                                                                            | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                     | :heavy_minus_sign:                                                                   | Configuration to override the default retry behavior of the client.                  |

### Response

**[operations.UpdateWorkflowResponse](../../models/operations/updateworkflowresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |