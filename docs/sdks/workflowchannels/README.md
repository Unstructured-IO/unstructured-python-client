# WorkflowChannels

## Overview

### Available Operations

* [create_workflow_channel_api_v1_workflows_workflow_id_notifications_channels_post](#create_workflow_channel_api_v1_workflows_workflow_id_notifications_channels_post) - Create Workflow Channel
* [delete_workflow_channel_api_v1_workflows_workflow_id_notifications_channels_channel_id_delete](#delete_workflow_channel_api_v1_workflows_workflow_id_notifications_channels_channel_id_delete) - Delete Workflow Channel
* [get_workflow_channel_api_v1_workflows_workflow_id_notifications_channels_channel_id_get](#get_workflow_channel_api_v1_workflows_workflow_id_notifications_channels_channel_id_get) - Get Workflow Channel
* [list_workflow_channels_api_v1_workflows_workflow_id_notifications_channels_get](#list_workflow_channels_api_v1_workflows_workflow_id_notifications_channels_get) - List Workflow Channels
* [update_workflow_channel_api_v1_workflows_workflow_id_notifications_channels_channel_id_patch](#update_workflow_channel_api_v1_workflows_workflow_id_notifications_channels_channel_id_patch) - Update Workflow Channel
* [verify_workflow_channel_api_v1_workflows_workflow_id_notifications_channels_channel_id_verify_post](#verify_workflow_channel_api_v1_workflows_workflow_id_notifications_channels_channel_id_verify_post) - Verify Workflow Channel

## create_workflow_channel_api_v1_workflows_workflow_id_notifications_channels_post

Create workflow-scoped notification channel.

Creates a new delivery channel for receiving platform event notifications
scoped to the specified workflow.

### Example Usage

<!-- UsageSnippet language="python" operationID="create_workflow_channel_api_v1_workflows__workflow_id__notifications_channels_post" method="post" path="/api/v1/workflows/{workflow_id}/notifications/channels" -->
```python
from unstructured_client import UnstructuredClient


with UnstructuredClient() as uc_client:

    res = uc_client.workflow_channels.create_workflow_channel_api_v1_workflows_workflow_id_notifications_channels_post(request={
        "request_body": {
            "channel_type": "webhook",
            "enabled": True,
            "event_types": [],
            "url": "https://measly-dependency.net",
        },
        "workflow_id": "f25202cb-485b-4362-96dd-a702cc80a033",
    })

    assert res.response_create_workflow_channel_api_v1_workflows_workflow_id_notifications_channels_post is not None

    # Handle response
    print(res.response_create_workflow_channel_api_v1_workflows_workflow_id_notifications_channels_post)

```

### Parameters

| Parameter                                                                                                                                                                                            | Type                                                                                                                                                                                                 | Required                                                                                                                                                                                             | Description                                                                                                                                                                                          |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `request`                                                                                                                                                                                            | [operations.CreateWorkflowChannelAPIV1WorkflowsWorkflowIDNotificationsChannelsPostRequest](../../models/operations/createworkflowchannelapiv1workflowsworkflowidnotificationschannelspostrequest.md) | :heavy_check_mark:                                                                                                                                                                                   | The request object to use for the request.                                                                                                                                                           |
| `retries`                                                                                                                                                                                            | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                                                                                                                                     | :heavy_minus_sign:                                                                                                                                                                                   | Configuration to override the default retry behavior of the client.                                                                                                                                  |

### Response

**[operations.CreateWorkflowChannelAPIV1WorkflowsWorkflowIDNotificationsChannelsPostResponse](../../models/operations/createworkflowchannelapiv1workflowsworkflowidnotificationschannelspostresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

## delete_workflow_channel_api_v1_workflows_workflow_id_notifications_channels_channel_id_delete

Delete workflow-scoped notification channel.

### Example Usage

<!-- UsageSnippet language="python" operationID="delete_workflow_channel_api_v1_workflows__workflow_id__notifications_channels__channel_id__delete" method="delete" path="/api/v1/workflows/{workflow_id}/notifications/channels/{channel_id}" -->
```python
from unstructured_client import UnstructuredClient


with UnstructuredClient() as uc_client:

    res = uc_client.workflow_channels.delete_workflow_channel_api_v1_workflows_workflow_id_notifications_channels_channel_id_delete(request={
        "channel_id": "<id>",
        "workflow_id": "702977f1-229e-4c29-b272-f3b341e640b3",
    })

    assert res is not None

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                                                                                                                                                                                  | Type                                                                                                                                                                                                                       | Required                                                                                                                                                                                                                   | Description                                                                                                                                                                                                                |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `request`                                                                                                                                                                                                                  | [operations.DeleteWorkflowChannelAPIV1WorkflowsWorkflowIDNotificationsChannelsChannelIDDeleteRequest](../../models/operations/deleteworkflowchannelapiv1workflowsworkflowidnotificationschannelschanneliddeleterequest.md) | :heavy_check_mark:                                                                                                                                                                                                         | The request object to use for the request.                                                                                                                                                                                 |
| `retries`                                                                                                                                                                                                                  | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                                                                                                                                                           | :heavy_minus_sign:                                                                                                                                                                                                         | Configuration to override the default retry behavior of the client.                                                                                                                                                        |

### Response

**[operations.DeleteWorkflowChannelAPIV1WorkflowsWorkflowIDNotificationsChannelsChannelIDDeleteResponse](../../models/operations/deleteworkflowchannelapiv1workflowsworkflowidnotificationschannelschanneliddeleteresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

## get_workflow_channel_api_v1_workflows_workflow_id_notifications_channels_channel_id_get

Get workflow-scoped notification channel by ID.

### Example Usage

<!-- UsageSnippet language="python" operationID="get_workflow_channel_api_v1_workflows__workflow_id__notifications_channels__channel_id__get" method="get" path="/api/v1/workflows/{workflow_id}/notifications/channels/{channel_id}" -->
```python
from unstructured_client import UnstructuredClient


with UnstructuredClient() as uc_client:

    res = uc_client.workflow_channels.get_workflow_channel_api_v1_workflows_workflow_id_notifications_channels_channel_id_get(request={
        "channel_id": "<id>",
        "workflow_id": "d62674fd-06b6-479a-8cdd-a80b8f8fcdfe",
    })

    assert res.response_get_workflow_channel_api_v1_workflows_workflow_id_notifications_channels_channel_id_get is not None

    # Handle response
    print(res.response_get_workflow_channel_api_v1_workflows_workflow_id_notifications_channels_channel_id_get)

```

### Parameters

| Parameter                                                                                                                                                                                                      | Type                                                                                                                                                                                                           | Required                                                                                                                                                                                                       | Description                                                                                                                                                                                                    |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `request`                                                                                                                                                                                                      | [operations.GetWorkflowChannelAPIV1WorkflowsWorkflowIDNotificationsChannelsChannelIDGetRequest](../../models/operations/getworkflowchannelapiv1workflowsworkflowidnotificationschannelschannelidgetrequest.md) | :heavy_check_mark:                                                                                                                                                                                             | The request object to use for the request.                                                                                                                                                                     |
| `retries`                                                                                                                                                                                                      | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                                                                                                                                               | :heavy_minus_sign:                                                                                                                                                                                             | Configuration to override the default retry behavior of the client.                                                                                                                                            |

### Response

**[operations.GetWorkflowChannelAPIV1WorkflowsWorkflowIDNotificationsChannelsChannelIDGetResponse](../../models/operations/getworkflowchannelapiv1workflowsworkflowidnotificationschannelschannelidgetresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

## list_workflow_channels_api_v1_workflows_workflow_id_notifications_channels_get

List workflow-scoped notification channels.

Returns all channel configurations for the specified workflow.
channel_type is required - no cross-type aggregation.

### Example Usage

<!-- UsageSnippet language="python" operationID="list_workflow_channels_api_v1_workflows__workflow_id__notifications_channels_get" method="get" path="/api/v1/workflows/{workflow_id}/notifications/channels" -->
```python
from unstructured_client import UnstructuredClient
from unstructured_client.models import shared


with UnstructuredClient() as uc_client:

    res = uc_client.workflow_channels.list_workflow_channels_api_v1_workflows_workflow_id_notifications_channels_get(request={
        "channel_type": shared.ChannelType.EMAIL,
        "workflow_id": "396ae11f-0443-440d-9d93-3aafb1d4e45b",
    })

    assert res.channel_list_response is not None

    # Handle response
    print(res.channel_list_response)

```

### Parameters

| Parameter                                                                                                                                                                                        | Type                                                                                                                                                                                             | Required                                                                                                                                                                                         | Description                                                                                                                                                                                      |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `request`                                                                                                                                                                                        | [operations.ListWorkflowChannelsAPIV1WorkflowsWorkflowIDNotificationsChannelsGetRequest](../../models/operations/listworkflowchannelsapiv1workflowsworkflowidnotificationschannelsgetrequest.md) | :heavy_check_mark:                                                                                                                                                                               | The request object to use for the request.                                                                                                                                                       |
| `retries`                                                                                                                                                                                        | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                                                                                                                                 | :heavy_minus_sign:                                                                                                                                                                               | Configuration to override the default retry behavior of the client.                                                                                                                              |

### Response

**[operations.ListWorkflowChannelsAPIV1WorkflowsWorkflowIDNotificationsChannelsGetResponse](../../models/operations/listworkflowchannelsapiv1workflowsworkflowidnotificationschannelsgetresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

## update_workflow_channel_api_v1_workflows_workflow_id_notifications_channels_channel_id_patch

Update workflow-scoped notification channel.

Updates an existing channel. Only provided fields are updated.

### Example Usage

<!-- UsageSnippet language="python" operationID="update_workflow_channel_api_v1_workflows__workflow_id__notifications_channels__channel_id__patch" method="patch" path="/api/v1/workflows/{workflow_id}/notifications/channels/{channel_id}" -->
```python
from unstructured_client import UnstructuredClient


with UnstructuredClient() as uc_client:

    res = uc_client.workflow_channels.update_workflow_channel_api_v1_workflows_workflow_id_notifications_channels_channel_id_patch(request={
        "update_channel_request": {},
        "channel_id": "<id>",
        "workflow_id": "6732a38f-9865-453e-a3d9-59972464e976",
    })

    assert res.response_update_workflow_channel_api_v1_workflows_workflow_id_notifications_channels_channel_id_patch is not None

    # Handle response
    print(res.response_update_workflow_channel_api_v1_workflows_workflow_id_notifications_channels_channel_id_patch)

```

### Parameters

| Parameter                                                                                                                                                                                                                | Type                                                                                                                                                                                                                     | Required                                                                                                                                                                                                                 | Description                                                                                                                                                                                                              |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `request`                                                                                                                                                                                                                | [operations.UpdateWorkflowChannelAPIV1WorkflowsWorkflowIDNotificationsChannelsChannelIDPatchRequest](../../models/operations/updateworkflowchannelapiv1workflowsworkflowidnotificationschannelschannelidpatchrequest.md) | :heavy_check_mark:                                                                                                                                                                                                       | The request object to use for the request.                                                                                                                                                                               |
| `retries`                                                                                                                                                                                                                | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                                                                                                                                                         | :heavy_minus_sign:                                                                                                                                                                                                       | Configuration to override the default retry behavior of the client.                                                                                                                                                      |

### Response

**[operations.UpdateWorkflowChannelAPIV1WorkflowsWorkflowIDNotificationsChannelsChannelIDPatchResponse](../../models/operations/updateworkflowchannelapiv1workflowsworkflowidnotificationschannelschannelidpatchresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

## verify_workflow_channel_api_v1_workflows_workflow_id_notifications_channels_channel_id_verify_post

Verify a workflow-scoped notification channel using a verification code.

Email channels require verification by providing the 6-digit code
sent to the recipient email address during channel creation.

### Example Usage

<!-- UsageSnippet language="python" operationID="verify_workflow_channel_api_v1_workflows__workflow_id__notifications_channels__channel_id__verify_post" method="post" path="/api/v1/workflows/{workflow_id}/notifications/channels/{channel_id}/verify" -->
```python
from unstructured_client import UnstructuredClient


with UnstructuredClient() as uc_client:

    res = uc_client.workflow_channels.verify_workflow_channel_api_v1_workflows_workflow_id_notifications_channels_channel_id_verify_post(request={
        "verify_channel_request": {
            "code": "<value>",
        },
        "channel_id": "<id>",
        "workflow_id": "0304693f-aa71-4717-b4f2-8e52d1f1363e",
    })

    assert res is not None

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                                                                                                                                                                                          | Type                                                                                                                                                                                                                               | Required                                                                                                                                                                                                                           | Description                                                                                                                                                                                                                        |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `request`                                                                                                                                                                                                                          | [operations.VerifyWorkflowChannelAPIV1WorkflowsWorkflowIDNotificationsChannelsChannelIDVerifyPostRequest](../../models/operations/verifyworkflowchannelapiv1workflowsworkflowidnotificationschannelschannelidverifypostrequest.md) | :heavy_check_mark:                                                                                                                                                                                                                 | The request object to use for the request.                                                                                                                                                                                         |
| `retries`                                                                                                                                                                                                                          | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                                                                                                                                                                   | :heavy_minus_sign:                                                                                                                                                                                                                 | Configuration to override the default retry behavior of the client.                                                                                                                                                                |

### Response

**[operations.VerifyWorkflowChannelAPIV1WorkflowsWorkflowIDNotificationsChannelsChannelIDVerifyPostResponse](../../models/operations/verifyworkflowchannelapiv1workflowsworkflowidnotificationschannelschannelidverifypostresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |