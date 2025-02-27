# Destinations
(*destinations*)

## Overview

### Available Operations

* [create_destination](#create_destination) - Create destination connector
* [delete_destination](#delete_destination) - Delete destination connector
* [get_destination](#get_destination) - Get destination connector
* [list_destinations](#list_destinations) - List destination connectors
* [update_destination](#update_destination) - Update destination connector

## create_destination

Create a new destination connector using the provided configuration and name.

### Example Usage

```python
from unstructured_client import UnstructuredClient
from unstructured_client.models import shared

with UnstructuredClient() as uc_client:

    res = uc_client.destinations.create_destination(request={
        "create_destination_connector": {
            "config": {
                "endpoint": "<value>",
                "index": "<value>",
                "key": "<key>",
            },
            "name": "<value>",
            "type": shared.DestinationConnectorType.ASTRADB,
        },
    })

    assert res.destination_connector_information is not None

    # Handle response
    print(res.destination_connector_information)

```

### Parameters

| Parameter                                                                                  | Type                                                                                       | Required                                                                                   | Description                                                                                |
| ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ |
| `request`                                                                                  | [operations.CreateDestinationRequest](../../models/operations/createdestinationrequest.md) | :heavy_check_mark:                                                                         | The request object to use for the request.                                                 |
| `retries`                                                                                  | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                           | :heavy_minus_sign:                                                                         | Configuration to override the default retry behavior of the client.                        |
| `server_url`                                                                               | *Optional[str]*                                                                            | :heavy_minus_sign:                                                                         | An optional server URL to use.                                                             |

### Response

**[operations.CreateDestinationResponse](../../models/operations/createdestinationresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

## delete_destination

Delete a specific destination connector by its ID.

### Example Usage

```python
from unstructured_client import UnstructuredClient

with UnstructuredClient() as uc_client:

    res = uc_client.destinations.delete_destination(request={
        "destination_id": "10a88d76-65fb-4c88-8488-9e7d272c6373",
    })

    assert res.any is not None

    # Handle response
    print(res.any)

```

### Parameters

| Parameter                                                                                  | Type                                                                                       | Required                                                                                   | Description                                                                                |
| ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ |
| `request`                                                                                  | [operations.DeleteDestinationRequest](../../models/operations/deletedestinationrequest.md) | :heavy_check_mark:                                                                         | The request object to use for the request.                                                 |
| `retries`                                                                                  | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                           | :heavy_minus_sign:                                                                         | Configuration to override the default retry behavior of the client.                        |
| `server_url`                                                                               | *Optional[str]*                                                                            | :heavy_minus_sign:                                                                         | An optional server URL to use.                                                             |

### Response

**[operations.DeleteDestinationResponse](../../models/operations/deletedestinationresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

## get_destination

Retrieve detailed information for a specific destination connector by its ID.

### Example Usage

```python
from unstructured_client import UnstructuredClient

with UnstructuredClient() as uc_client:

    res = uc_client.destinations.get_destination(request={
        "destination_id": "41ba03fb-faa3-4e9e-8cfb-27f133c4198a",
    })

    assert res.destination_connector_information is not None

    # Handle response
    print(res.destination_connector_information)

```

### Parameters

| Parameter                                                                            | Type                                                                                 | Required                                                                             | Description                                                                          |
| ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------ |
| `request`                                                                            | [operations.GetDestinationRequest](../../models/operations/getdestinationrequest.md) | :heavy_check_mark:                                                                   | The request object to use for the request.                                           |
| `retries`                                                                            | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                     | :heavy_minus_sign:                                                                   | Configuration to override the default retry behavior of the client.                  |
| `server_url`                                                                         | *Optional[str]*                                                                      | :heavy_minus_sign:                                                                   | An optional server URL to use.                                                       |

### Response

**[operations.GetDestinationResponse](../../models/operations/getdestinationresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

## list_destinations

Retrieve a list of available destination connectors.

### Example Usage

```python
from unstructured_client import UnstructuredClient

with UnstructuredClient() as uc_client:

    res = uc_client.destinations.list_destinations(request={})

    assert res.response_list_destinations is not None

    # Handle response
    print(res.response_list_destinations)

```

### Parameters

| Parameter                                                                                | Type                                                                                     | Required                                                                                 | Description                                                                              |
| ---------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| `request`                                                                                | [operations.ListDestinationsRequest](../../models/operations/listdestinationsrequest.md) | :heavy_check_mark:                                                                       | The request object to use for the request.                                               |
| `retries`                                                                                | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                         | :heavy_minus_sign:                                                                       | Configuration to override the default retry behavior of the client.                      |
| `server_url`                                                                             | *Optional[str]*                                                                          | :heavy_minus_sign:                                                                       | An optional server URL to use.                                                           |

### Response

**[operations.ListDestinationsResponse](../../models/operations/listdestinationsresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

## update_destination

Update the configuration of an existing destination connector.

### Example Usage

```python
from unstructured_client import UnstructuredClient

with UnstructuredClient() as uc_client:

    res = uc_client.destinations.update_destination(request={
        "update_destination_connector": {
            "config": {
                "batch_size": 7372,
                "database": "<value>",
                "host": "pushy-apparatus.net",
                "password": "sxtPKvIMqbllzrd",
                "port": 432315,
                "table_name": "<value>",
                "username": "Dulce38",
            },
        },
        "destination_id": "0a0ddfee-087e-467d-abcc-fdb6451a6e6f",
    })

    assert res.destination_connector_information is not None

    # Handle response
    print(res.destination_connector_information)

```

### Parameters

| Parameter                                                                                  | Type                                                                                       | Required                                                                                   | Description                                                                                |
| ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ |
| `request`                                                                                  | [operations.UpdateDestinationRequest](../../models/operations/updatedestinationrequest.md) | :heavy_check_mark:                                                                         | The request object to use for the request.                                                 |
| `retries`                                                                                  | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                           | :heavy_minus_sign:                                                                         | Configuration to override the default retry behavior of the client.                        |
| `server_url`                                                                               | *Optional[str]*                                                                            | :heavy_minus_sign:                                                                         | An optional server URL to use.                                                             |

### Response

**[operations.UpdateDestinationResponse](../../models/operations/updatedestinationresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |