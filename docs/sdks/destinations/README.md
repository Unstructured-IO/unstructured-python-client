# Destinations
(*destinations*)

## Overview

### Available Operations

* [check_destination_connection_api_v1_destinations_destination_id_connection_check_post](#check_destination_connection_api_v1_destinations_destination_id_connection_check_post) - Check Destination Connection
* [create_destination](#create_destination) - Create destination connector
* [delete_destination](#delete_destination) - Delete destination connector
* [get_destination](#get_destination) - Get destination connector
* [get_destination_connection_check_api_v1_destinations_destination_id_connection_check_get](#get_destination_connection_check_api_v1_destinations_destination_id_connection_check_get) - Get Destination Connection Check
* [list_destinations](#list_destinations) - List destination connectors
* [update_destination](#update_destination) - Update destination connector

## check_destination_connection_api_v1_destinations_destination_id_connection_check_post

Check Destination Connection

Initiates a connection check for the specified destination connector.

**Parameters:**
- **destination_id**: The UUID of the destination connector.
- **db_session**: Database session dependency.
- **user_data**: Information about the authenticated user.

**Returns:**
- The result of the connection check.

### Example Usage

```python
from unstructured_client import UnstructuredClient


with UnstructuredClient() as uc_client:

    res = uc_client.destinations.check_destination_connection_api_v1_destinations_destination_id_connection_check_post(request={
        "destination_id": "b65169f5-79ba-4464-918f-b0be2c07b962",
    })

    assert res.dag_node_connection_check is not None

    # Handle response
    print(res.dag_node_connection_check)

```

### Parameters

| Parameter                                                                                                                                                                                                      | Type                                                                                                                                                                                                           | Required                                                                                                                                                                                                       | Description                                                                                                                                                                                                    |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `request`                                                                                                                                                                                                      | [operations.CheckDestinationConnectionAPIV1DestinationsDestinationIDConnectionCheckPostRequest](../../models/operations/checkdestinationconnectionapiv1destinationsdestinationidconnectioncheckpostrequest.md) | :heavy_check_mark:                                                                                                                                                                                             | The request object to use for the request.                                                                                                                                                                     |
| `retries`                                                                                                                                                                                                      | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                                                                                                                                               | :heavy_minus_sign:                                                                                                                                                                                             | Configuration to override the default retry behavior of the client.                                                                                                                                            |
| `server_url`                                                                                                                                                                                                   | *Optional[str]*                                                                                                                                                                                                | :heavy_minus_sign:                                                                                                                                                                                             | An optional server URL to use.                                                                                                                                                                                 |

### Response

**[operations.CheckDestinationConnectionAPIV1DestinationsDestinationIDConnectionCheckPostResponse](../../models/operations/checkdestinationconnectionapiv1destinationsdestinationidconnectioncheckpostresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

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
                "api_endpoint": "<value>",
                "batch_size": 20,
                "collection_name": "<value>",
                "flatten_metadata": False,
                "token": "<value>",
            },
            "name": "<value>",
            "type": shared.DestinationConnectorType.AZURE_AI_SEARCH,
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

## get_destination_connection_check_api_v1_destinations_destination_id_connection_check_get

Get Destination Connection Check

Retrieves the most recent connection check for the specified destination connector.

**Parameters:**
- **destination_id**: The UUID of the destination connector.
- **db_session**: Database session dependency.
- **user_data**: Information about the authenticated user.

**Returns:**
- Connection check results.

### Example Usage

```python
from unstructured_client import UnstructuredClient


with UnstructuredClient() as uc_client:

    res = uc_client.destinations.get_destination_connection_check_api_v1_destinations_destination_id_connection_check_get(request={
        "destination_id": "3c48df35-2b2c-46f2-9aa2-d7eae993797c",
    })

    assert res.dag_node_connection_check is not None

    # Handle response
    print(res.dag_node_connection_check)

```

### Parameters

| Parameter                                                                                                                                                                                                          | Type                                                                                                                                                                                                               | Required                                                                                                                                                                                                           | Description                                                                                                                                                                                                        |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `request`                                                                                                                                                                                                          | [operations.GetDestinationConnectionCheckAPIV1DestinationsDestinationIDConnectionCheckGetRequest](../../models/operations/getdestinationconnectioncheckapiv1destinationsdestinationidconnectioncheckgetrequest.md) | :heavy_check_mark:                                                                                                                                                                                                 | The request object to use for the request.                                                                                                                                                                         |
| `retries`                                                                                                                                                                                                          | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                                                                                                                                                   | :heavy_minus_sign:                                                                                                                                                                                                 | Configuration to override the default retry behavior of the client.                                                                                                                                                |
| `server_url`                                                                                                                                                                                                       | *Optional[str]*                                                                                                                                                                                                    | :heavy_minus_sign:                                                                                                                                                                                                 | An optional server URL to use.                                                                                                                                                                                     |

### Response

**[operations.GetDestinationConnectionCheckAPIV1DestinationsDestinationIDConnectionCheckGetResponse](../../models/operations/getdestinationconnectioncheckapiv1destinationsdestinationidconnectioncheckgetresponse.md)**

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
        "destination_id": "6f9ea9d2-7c4e-42ec-8b5a-6971bd7ec9d2",
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