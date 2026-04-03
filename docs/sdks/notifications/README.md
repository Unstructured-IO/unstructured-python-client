# Notifications
(*notifications*)

## Overview

### Available Operations

* [get_notification_api_v1_notifications_notification_id_get](#get_notification_api_v1_notifications_notification_id_get) - Get Notification
* [get_unread_count_api_v1_notifications_unread_count_get](#get_unread_count_api_v1_notifications_unread_count_get) - Get Unread Count
* [list_notifications_api_v1_notifications_get](#list_notifications_api_v1_notifications_get) - List Notifications
* [mark_read_api_v1_notifications_mark_read_post](#mark_read_api_v1_notifications_mark_read_post) - Mark Read

## get_notification_api_v1_notifications_notification_id_get

Get a single notification event by ID.

### Example Usage

<!-- UsageSnippet language="python" operationID="get_notification_api_v1_notifications__notification_id__get" method="get" path="/api/v1/notifications/{notification_id}" -->
```python
from unstructured_client import UnstructuredClient


with UnstructuredClient() as uc_client:

    res = uc_client.notifications.get_notification_api_v1_notifications_notification_id_get(request={
        "notification_id": "864270b9-965a-43bf-adb6-a812798b9977",
    })

    assert res.notification_response is not None

    # Handle response
    print(res.notification_response)

```

### Parameters

| Parameter                                                                                                                                                    | Type                                                                                                                                                         | Required                                                                                                                                                     | Description                                                                                                                                                  |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `request`                                                                                                                                                    | [operations.GetNotificationAPIV1NotificationsNotificationIDGetRequest](../../models/operations/getnotificationapiv1notificationsnotificationidgetrequest.md) | :heavy_check_mark:                                                                                                                                           | The request object to use for the request.                                                                                                                   |
| `retries`                                                                                                                                                    | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                                                                                             | :heavy_minus_sign:                                                                                                                                           | Configuration to override the default retry behavior of the client.                                                                                          |

### Response

**[operations.GetNotificationAPIV1NotificationsNotificationIDGetResponse](../../models/operations/getnotificationapiv1notificationsnotificationidgetresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

## get_unread_count_api_v1_notifications_unread_count_get

Get count of unread notification events for current user.

Target performance: <50ms p95 (SC-014).

Args:
    workflow_id: Optional workflow filter

### Example Usage

<!-- UsageSnippet language="python" operationID="get_unread_count_api_v1_notifications_unread_count_get" method="get" path="/api/v1/notifications/unread-count" -->
```python
from unstructured_client import UnstructuredClient


with UnstructuredClient() as uc_client:

    res = uc_client.notifications.get_unread_count_api_v1_notifications_unread_count_get(request={})

    assert res.unread_count_response is not None

    # Handle response
    print(res.unread_count_response)

```

### Parameters

| Parameter                                                                                                                                            | Type                                                                                                                                                 | Required                                                                                                                                             | Description                                                                                                                                          |
| ---------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `request`                                                                                                                                            | [operations.GetUnreadCountAPIV1NotificationsUnreadCountGetRequest](../../models/operations/getunreadcountapiv1notificationsunreadcountgetrequest.md) | :heavy_check_mark:                                                                                                                                   | The request object to use for the request.                                                                                                           |
| `retries`                                                                                                                                            | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                                                                                     | :heavy_minus_sign:                                                                                                                                   | Configuration to override the default retry behavior of the client.                                                                                  |

### Response

**[operations.GetUnreadCountAPIV1NotificationsUnreadCountGetResponse](../../models/operations/getunreadcountapiv1notificationsunreadcountgetresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

## list_notifications_api_v1_notifications_get

List notification events for the authenticated user.

Returns persisted notification events enriched with per-user read status.
Each notification represents a platform event (e.g., job.completed) with
an `is_read` flag indicating whether the current user has marked it as read.

Ordered by created_at DESC with cursor-based pagination.

Args:
    workflow_id: Filter by workflow ID
    event_types: Comma-separated event types (e.g., "job.completed,job.failed")
    since: Filter events created after this ISO 8601 timestamp
    limit: Max events to return (1-100, default 50)
    cursor: Pagination cursor from previous response
    unread_only: Filter to unread events only for current user

### Example Usage

<!-- UsageSnippet language="python" operationID="list_notifications_api_v1_notifications_get" method="get" path="/api/v1/notifications" -->
```python
from unstructured_client import UnstructuredClient


with UnstructuredClient() as uc_client:

    res = uc_client.notifications.list_notifications_api_v1_notifications_get(request={})

    assert res.notification_list_response is not None

    # Handle response
    print(res.notification_list_response)

```

### Parameters

| Parameter                                                                                                                            | Type                                                                                                                                 | Required                                                                                                                             | Description                                                                                                                          |
| ------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------ |
| `request`                                                                                                                            | [operations.ListNotificationsAPIV1NotificationsGetRequest](../../models/operations/listnotificationsapiv1notificationsgetrequest.md) | :heavy_check_mark:                                                                                                                   | The request object to use for the request.                                                                                           |
| `retries`                                                                                                                            | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                                                                     | :heavy_minus_sign:                                                                                                                   | Configuration to override the default retry behavior of the client.                                                                  |

### Response

**[operations.ListNotificationsAPIV1NotificationsGetResponse](../../models/operations/listnotificationsapiv1notificationsgetresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

## mark_read_api_v1_notifications_mark_read_post

Mark notification events as read for current user.

Provide EITHER notification_ids (list of up to 100 UUIDs) OR before (timestamp).
workflow_id filter is only valid with 'before' mode.

Target performance: batch of 100 < 100ms (SC-015).

### Example Usage

<!-- UsageSnippet language="python" operationID="mark_read_api_v1_notifications_mark_read_post" method="post" path="/api/v1/notifications/mark-read" -->
```python
from unstructured_client import UnstructuredClient


with UnstructuredClient() as uc_client:

    res = uc_client.notifications.mark_read_api_v1_notifications_mark_read_post(request={
        "mark_read_request": {},
    })

    assert res.mark_read_response is not None

    # Handle response
    print(res.mark_read_response)

```

### Parameters

| Parameter                                                                                                                            | Type                                                                                                                                 | Required                                                                                                                             | Description                                                                                                                          |
| ------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------ |
| `request`                                                                                                                            | [operations.MarkReadAPIV1NotificationsMarkReadPostRequest](../../models/operations/markreadapiv1notificationsmarkreadpostrequest.md) | :heavy_check_mark:                                                                                                                   | The request object to use for the request.                                                                                           |
| `retries`                                                                                                                            | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                                                                     | :heavy_minus_sign:                                                                                                                   | Configuration to override the default retry behavior of the client.                                                                  |

### Response

**[operations.MarkReadAPIV1NotificationsMarkReadPostResponse](../../models/operations/markreadapiv1notificationsmarkreadpostresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |