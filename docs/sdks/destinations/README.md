# Destinations
(*destinations*)

## Overview

### Available Operations

* [create_connection_check_destinations](#create_connection_check_destinations) - Create destination connection check
* [create_destination](#create_destination) - Create destination connector
* [delete_destination](#delete_destination) - Delete destination connector
* [get_connection_check_destinations](#get_connection_check_destinations) - Get the latest destination connector connection check
* [get_destination](#get_destination) - Get destination connector
* [list_destinations](#list_destinations) - List destination connectors
* [update_destination](#update_destination) - Update destination connector

## create_connection_check_destinations

Initiate a connection check for the destination connector

### Example Usage

<!-- UsageSnippet language="python" operationID="create_connection_check_destinations" method="post" path="/api/v1/destinations/{destination_id}/connection-check" -->
```python
from unstructured_client import UnstructuredClient


with UnstructuredClient() as uc_client:

    res = uc_client.destinations.create_connection_check_destinations(request={
        "destination_id": "cb9e35c1-0b04-4d98-83fa-fa6241323f96",
    })

    assert res.dag_node_connection_check is not None

    # Handle response
    print(res.dag_node_connection_check)

```

### Parameters

| Parameter                                                                                                                  | Type                                                                                                                       | Required                                                                                                                   | Description                                                                                                                |
| -------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `request`                                                                                                                  | [operations.CreateConnectionCheckDestinationsRequest](../../models/operations/createconnectioncheckdestinationsrequest.md) | :heavy_check_mark:                                                                                                         | The request object to use for the request.                                                                                 |
| `retries`                                                                                                                  | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                                                           | :heavy_minus_sign:                                                                                                         | Configuration to override the default retry behavior of the client.                                                        |

### Response

**[operations.CreateConnectionCheckDestinationsResponse](../../models/operations/createconnectioncheckdestinationsresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

## create_destination

Create a new destination connector using the provided configuration and name.

### Example Usage

<!-- UsageSnippet language="python" operationID="create_destination" method="post" path="/api/v1/destinations/" -->
```python
from unstructured_client import UnstructuredClient
from unstructured_client.models import shared


with UnstructuredClient() as uc_client:

    res = uc_client.destinations.create_destination(request={
        "create_destination_connector": {
            "config": {
                "collection": "<value>",
                "database": "<value>",
                "uri": "https://criminal-bowler.com",
            },
            "name": "<value>",
            "type": shared.DestinationConnectorType.ELASTICSEARCH,
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

<!-- UsageSnippet language="python" operationID="delete_destination" method="delete" path="/api/v1/destinations/{destination_id}" -->
```python
from unstructured_client import UnstructuredClient


with UnstructuredClient() as uc_client:

    res = uc_client.destinations.delete_destination(request={
        "destination_id": "f50b6b0c-1177-4edb-ae10-68199cd00ba6",
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

### Response

**[operations.DeleteDestinationResponse](../../models/operations/deletedestinationresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

## get_connection_check_destinations

Retrieves the most recent connection check for the specified destination connector.

### Example Usage

<!-- UsageSnippet language="python" operationID="get_connection_check_destinations" method="get" path="/api/v1/destinations/{destination_id}/connection-check" -->
```python
from unstructured_client import UnstructuredClient


with UnstructuredClient() as uc_client:

    res = uc_client.destinations.get_connection_check_destinations(request={
        "destination_id": "c95687a3-239f-485c-946b-4c8fe314ef82",
    })

    assert res.dag_node_connection_check is not None

    # Handle response
    print(res.dag_node_connection_check)

```

### Parameters

| Parameter                                                                                                            | Type                                                                                                                 | Required                                                                                                             | Description                                                                                                          |
| -------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `request`                                                                                                            | [operations.GetConnectionCheckDestinationsRequest](../../models/operations/getconnectioncheckdestinationsrequest.md) | :heavy_check_mark:                                                                                                   | The request object to use for the request.                                                                           |
| `retries`                                                                                                            | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                                                     | :heavy_minus_sign:                                                                                                   | Configuration to override the default retry behavior of the client.                                                  |

### Response

**[operations.GetConnectionCheckDestinationsResponse](../../models/operations/getconnectioncheckdestinationsresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

## get_destination

Retrieve detailed information for a specific destination connector by its ID.

### Example Usage

<!-- UsageSnippet language="python" operationID="get_destination" method="get" path="/api/v1/destinations/{destination_id}" -->
```python
from unstructured_client import UnstructuredClient


with UnstructuredClient() as uc_client:

    res = uc_client.destinations.get_destination(request={
        "destination_id": "6352107c-44bd-4a20-a286-de73a4d9c9bd",
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

<!-- UsageSnippet language="python" operationID="list_destinations" method="get" path="/api/v1/destinations/" -->
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

<!-- UsageSnippet language="python" operationID="update_destination" method="put" path="/api/v1/destinations/{destination_id}" -->
```python
from unstructured_client import UnstructuredClient


with UnstructuredClient() as uc_client:

    res = uc_client.destinations.update_destination(request={
        "update_destination_connector": {
            "config": {
                "batch_size": 100,
                "bootstrap_servers": "<value>",
                "kafka_api_key": "<value>",
                "port": 9092,
                "secret": "<value>",
                "topic": "<value>",
            },
        },
        "destination_id": "9726962d-9d1e-4f84-8787-c7313d183927",
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

### Response

**[operations.UpdateDestinationResponse](../../models/operations/updatedestinationresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |