# Channels

## Overview

### Available Operations

* [create_channel_api_v1_notifications_channels_post](#create_channel_api_v1_notifications_channels_post) - Create Channel
* [delete_channel_api_v1_notifications_channels_channel_id_delete](#delete_channel_api_v1_notifications_channels_channel_id_delete) - Delete Channel
* [get_channel_api_v1_notifications_channels_channel_id_get](#get_channel_api_v1_notifications_channels_channel_id_get) - Get Channel
* [list_channels_api_v1_notifications_channels_get](#list_channels_api_v1_notifications_channels_get) - List Channels
* [update_channel_api_v1_notifications_channels_channel_id_patch](#update_channel_api_v1_notifications_channels_channel_id_patch) - Update Channel
* [verify_channel_api_v1_notifications_channels_channel_id_verify_post](#verify_channel_api_v1_notifications_channels_channel_id_verify_post) - Verify Channel

## create_channel_api_v1_notifications_channels_post

Create notification channel.

Creates a new delivery channel for receiving platform event notifications.
URL must use HTTPS for webhook type. At least one event type must be specified.

### Example Usage

<!-- UsageSnippet language="python" operationID="create_channel_api_v1_notifications_channels_post" method="post" path="/api/v1/notifications/channels" -->
```python
from unstructured_client import UnstructuredClient
from unstructured_client.models import shared


with UnstructuredClient() as uc_client:

    res = uc_client.channels.create_channel_api_v1_notifications_channels_post(request={
        "request_body": {
            "channel_type": "email",
            "email_config": {
                "recipient_email": "Karelle_Wiegand72@hotmail.com",
            },
            "enabled": True,
            "event_types": [
                shared.NotificationEventType.JOB_SCHEDULED,
            ],
        },
    })

    assert res.response_create_channel_api_v1_notifications_channels_post is not None

    # Handle response
    print(res.response_create_channel_api_v1_notifications_channels_post)

```

### Parameters

| Parameter                                                                                                                                      | Type                                                                                                                                           | Required                                                                                                                                       | Description                                                                                                                                    |
| ---------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `request`                                                                                                                                      | [operations.CreateChannelAPIV1NotificationsChannelsPostRequest](../../models/operations/createchannelapiv1notificationschannelspostrequest.md) | :heavy_check_mark:                                                                                                                             | The request object to use for the request.                                                                                                     |
| `retries`                                                                                                                                      | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                                                                               | :heavy_minus_sign:                                                                                                                             | Configuration to override the default retry behavior of the client.                                                                            |

### Response

**[operations.CreateChannelAPIV1NotificationsChannelsPostResponse](../../models/operations/createchannelapiv1notificationschannelspostresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

## delete_channel_api_v1_notifications_channels_channel_id_delete

Delete account-level notification channel.

### Example Usage

<!-- UsageSnippet language="python" operationID="delete_channel_api_v1_notifications_channels__channel_id__delete" method="delete" path="/api/v1/notifications/channels/{channel_id}" -->
```python
from unstructured_client import UnstructuredClient


with UnstructuredClient() as uc_client:

    res = uc_client.channels.delete_channel_api_v1_notifications_channels_channel_id_delete(request={
        "channel_id": "<id>",
    })

    assert res is not None

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                                                                                                                            | Type                                                                                                                                                                 | Required                                                                                                                                                             | Description                                                                                                                                                          |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `request`                                                                                                                                                            | [operations.DeleteChannelAPIV1NotificationsChannelsChannelIDDeleteRequest](../../models/operations/deletechannelapiv1notificationschannelschanneliddeleterequest.md) | :heavy_check_mark:                                                                                                                                                   | The request object to use for the request.                                                                                                                           |
| `retries`                                                                                                                                                            | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                                                                                                     | :heavy_minus_sign:                                                                                                                                                   | Configuration to override the default retry behavior of the client.                                                                                                  |

### Response

**[operations.DeleteChannelAPIV1NotificationsChannelsChannelIDDeleteResponse](../../models/operations/deletechannelapiv1notificationschannelschanneliddeleteresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

## get_channel_api_v1_notifications_channels_channel_id_get

Get account-level notification channel by ID.

### Example Usage

<!-- UsageSnippet language="python" operationID="get_channel_api_v1_notifications_channels__channel_id__get" method="get" path="/api/v1/notifications/channels/{channel_id}" -->
```python
from unstructured_client import UnstructuredClient


with UnstructuredClient() as uc_client:

    res = uc_client.channels.get_channel_api_v1_notifications_channels_channel_id_get(request={
        "channel_id": "<id>",
    })

    assert res.response_get_channel_api_v1_notifications_channels_channel_id_get is not None

    # Handle response
    print(res.response_get_channel_api_v1_notifications_channels_channel_id_get)

```

### Parameters

| Parameter                                                                                                                                                | Type                                                                                                                                                     | Required                                                                                                                                                 | Description                                                                                                                                              |
| -------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `request`                                                                                                                                                | [operations.GetChannelAPIV1NotificationsChannelsChannelIDGetRequest](../../models/operations/getchannelapiv1notificationschannelschannelidgetrequest.md) | :heavy_check_mark:                                                                                                                                       | The request object to use for the request.                                                                                                               |
| `retries`                                                                                                                                                | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                                                                                         | :heavy_minus_sign:                                                                                                                                       | Configuration to override the default retry behavior of the client.                                                                                      |

### Response

**[operations.GetChannelAPIV1NotificationsChannelsChannelIDGetResponse](../../models/operations/getchannelapiv1notificationschannelschannelidgetresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

## list_channels_api_v1_notifications_channels_get

List account-level notification channels.

Returns all channel configurations for the account (workflow_id=None scope).
channel_type is required - no cross-type aggregation.

### Example Usage

<!-- UsageSnippet language="python" operationID="list_channels_api_v1_notifications_channels_get" method="get" path="/api/v1/notifications/channels" -->
```python
from unstructured_client import UnstructuredClient
from unstructured_client.models import shared


with UnstructuredClient() as uc_client:

    res = uc_client.channels.list_channels_api_v1_notifications_channels_get(request={
        "channel_type": shared.ChannelType.WEBHOOK,
    })

    assert res.channel_list_response is not None

    # Handle response
    print(res.channel_list_response)

```

### Parameters

| Parameter                                                                                                                                  | Type                                                                                                                                       | Required                                                                                                                                   | Description                                                                                                                                |
| ------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `request`                                                                                                                                  | [operations.ListChannelsAPIV1NotificationsChannelsGetRequest](../../models/operations/listchannelsapiv1notificationschannelsgetrequest.md) | :heavy_check_mark:                                                                                                                         | The request object to use for the request.                                                                                                 |
| `retries`                                                                                                                                  | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                                                                           | :heavy_minus_sign:                                                                                                                         | Configuration to override the default retry behavior of the client.                                                                        |

### Response

**[operations.ListChannelsAPIV1NotificationsChannelsGetResponse](../../models/operations/listchannelsapiv1notificationschannelsgetresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

## update_channel_api_v1_notifications_channels_channel_id_patch

Update account-level notification channel.

Updates an existing channel. Only provided fields are updated.

### Example Usage

<!-- UsageSnippet language="python" operationID="update_channel_api_v1_notifications_channels__channel_id__patch" method="patch" path="/api/v1/notifications/channels/{channel_id}" -->
```python
from unstructured_client import UnstructuredClient


with UnstructuredClient() as uc_client:

    res = uc_client.channels.update_channel_api_v1_notifications_channels_channel_id_patch(request={
        "update_channel_request": {},
        "channel_id": "<id>",
    })

    assert res.response_update_channel_api_v1_notifications_channels_channel_id_patch is not None

    # Handle response
    print(res.response_update_channel_api_v1_notifications_channels_channel_id_patch)

```

### Parameters

| Parameter                                                                                                                                                          | Type                                                                                                                                                               | Required                                                                                                                                                           | Description                                                                                                                                                        |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `request`                                                                                                                                                          | [operations.UpdateChannelAPIV1NotificationsChannelsChannelIDPatchRequest](../../models/operations/updatechannelapiv1notificationschannelschannelidpatchrequest.md) | :heavy_check_mark:                                                                                                                                                 | The request object to use for the request.                                                                                                                         |
| `retries`                                                                                                                                                          | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                                                                                                   | :heavy_minus_sign:                                                                                                                                                 | Configuration to override the default retry behavior of the client.                                                                                                |

### Response

**[operations.UpdateChannelAPIV1NotificationsChannelsChannelIDPatchResponse](../../models/operations/updatechannelapiv1notificationschannelschannelidpatchresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

## verify_channel_api_v1_notifications_channels_channel_id_verify_post

Verify a notification channel using a verification code.

Email channels require verification by providing the 6-digit code
sent to the recipient email address during channel creation.

### Example Usage

<!-- UsageSnippet language="python" operationID="verify_channel_api_v1_notifications_channels__channel_id__verify_post" method="post" path="/api/v1/notifications/channels/{channel_id}/verify" -->
```python
from unstructured_client import UnstructuredClient


with UnstructuredClient() as uc_client:

    res = uc_client.channels.verify_channel_api_v1_notifications_channels_channel_id_verify_post(request={
        "verify_channel_request": {
            "code": "<value>",
        },
        "channel_id": "<id>",
    })

    assert res is not None

    # Handle response
    print(res)

```

### Parameters

| Parameter                                                                                                                                                                    | Type                                                                                                                                                                         | Required                                                                                                                                                                     | Description                                                                                                                                                                  |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `request`                                                                                                                                                                    | [operations.VerifyChannelAPIV1NotificationsChannelsChannelIDVerifyPostRequest](../../models/operations/verifychannelapiv1notificationschannelschannelidverifypostrequest.md) | :heavy_check_mark:                                                                                                                                                           | The request object to use for the request.                                                                                                                                   |
| `retries`                                                                                                                                                                    | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                                                                                                             | :heavy_minus_sign:                                                                                                                                                           | Configuration to override the default retry behavior of the client.                                                                                                          |

### Response

**[operations.VerifyChannelAPIV1NotificationsChannelsChannelIDVerifyPostResponse](../../models/operations/verifychannelapiv1notificationschannelschannelidverifypostresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |