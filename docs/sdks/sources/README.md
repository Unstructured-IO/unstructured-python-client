# Sources
(*sources*)

## Overview

### Available Operations

* [create_connection_check_sources](#create_connection_check_sources) - Create source connection check
* [create_source](#create_source) - Create source connector
* [delete_source](#delete_source) - Delete source connector
* [get_connection_check_sources](#get_connection_check_sources) - Get the latest source connector connection check
* [get_source](#get_source) - Get source connector
* [list_sources](#list_sources) - List available source connectors
* [update_source](#update_source) - Update source connector

## create_connection_check_sources

Initiates a connection check for the specified source connector.

### Example Usage

<!-- UsageSnippet language="python" operationID="create_connection_check_sources" method="post" path="/api/v1/sources/{source_id}/connection-check" -->
```python
from unstructured_client import UnstructuredClient
from unstructured_client.models import operations


with UnstructuredClient() as uc_client:

    res = uc_client.sources.create_connection_check_sources(security=operations.CreateConnectionCheckSourcesSecurity(
        http_bearer="<YOUR_BEARER_TOKEN_HERE>",
    ), request={
        "source_id": "8d49e3f2-3e6d-4973-bc61-292af66829d7",
    })

    assert res.dag_node_connection_check is not None

    # Handle response
    print(res.dag_node_connection_check)

```

### Parameters

| Parameter                                                                                                          | Type                                                                                                               | Required                                                                                                           | Description                                                                                                        |
| ------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------ |
| `request`                                                                                                          | [operations.CreateConnectionCheckSourcesRequest](../../models/operations/createconnectionchecksourcesrequest.md)   | :heavy_check_mark:                                                                                                 | The request object to use for the request.                                                                         |
| `security`                                                                                                         | [operations.CreateConnectionCheckSourcesSecurity](../../models/operations/createconnectionchecksourcessecurity.md) | :heavy_check_mark:                                                                                                 | The security requirements to use for the request.                                                                  |
| `retries`                                                                                                          | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                                                   | :heavy_minus_sign:                                                                                                 | Configuration to override the default retry behavior of the client.                                                |

### Response

**[operations.CreateConnectionCheckSourcesResponse](../../models/operations/createconnectionchecksourcesresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

## create_source

Create a new source connector using the provided configuration and name.

### Example Usage

<!-- UsageSnippet language="python" operationID="create_source" method="post" path="/api/v1/sources/" -->
```python
from unstructured_client import UnstructuredClient
from unstructured_client.models import operations, shared


with UnstructuredClient() as uc_client:

    res = uc_client.sources.create_source(security=operations.CreateSourceSecurity(
        http_bearer="<YOUR_BEARER_TOKEN_HERE>",
    ), request={
        "create_source_connector": {
            "config": {
                "catalog": "<value>",
                "client_id": "<id>",
                "client_secret": "<value>",
                "host": "athletic-nudge.org",
                "volume": "<value>",
                "volume_path": "<value>",
            },
            "name": "<value>",
            "type": shared.SourceConnectorType.SALESFORCE,
        },
    })

    assert res.source_connector_information is not None

    # Handle response
    print(res.source_connector_information)

```

### Parameters

| Parameter                                                                          | Type                                                                               | Required                                                                           | Description                                                                        |
| ---------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `request`                                                                          | [operations.CreateSourceRequest](../../models/operations/createsourcerequest.md)   | :heavy_check_mark:                                                                 | The request object to use for the request.                                         |
| `security`                                                                         | [operations.CreateSourceSecurity](../../models/operations/createsourcesecurity.md) | :heavy_check_mark:                                                                 | The security requirements to use for the request.                                  |
| `retries`                                                                          | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                   | :heavy_minus_sign:                                                                 | Configuration to override the default retry behavior of the client.                |

### Response

**[operations.CreateSourceResponse](../../models/operations/createsourceresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

## delete_source

Delete a specific source connector identified by its ID.

### Example Usage

<!-- UsageSnippet language="python" operationID="delete_source" method="delete" path="/api/v1/sources/{source_id}" -->
```python
from unstructured_client import UnstructuredClient
from unstructured_client.models import operations


with UnstructuredClient() as uc_client:

    res = uc_client.sources.delete_source(security=operations.DeleteSourceSecurity(
        http_bearer="<YOUR_BEARER_TOKEN_HERE>",
    ), request={
        "source_id": "296c4009-7b81-4144-9c7c-e058204aeb93",
    })

    assert res.any is not None

    # Handle response
    print(res.any)

```

### Parameters

| Parameter                                                                          | Type                                                                               | Required                                                                           | Description                                                                        |
| ---------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `request`                                                                          | [operations.DeleteSourceRequest](../../models/operations/deletesourcerequest.md)   | :heavy_check_mark:                                                                 | The request object to use for the request.                                         |
| `security`                                                                         | [operations.DeleteSourceSecurity](../../models/operations/deletesourcesecurity.md) | :heavy_check_mark:                                                                 | The security requirements to use for the request.                                  |
| `retries`                                                                          | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                   | :heavy_minus_sign:                                                                 | Configuration to override the default retry behavior of the client.                |

### Response

**[operations.DeleteSourceResponse](../../models/operations/deletesourceresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

## get_connection_check_sources

Retrieves the most recent connection check for the specified source connector.

### Example Usage

<!-- UsageSnippet language="python" operationID="get_connection_check_sources" method="get" path="/api/v1/sources/{source_id}/connection-check" -->
```python
from unstructured_client import UnstructuredClient
from unstructured_client.models import operations


with UnstructuredClient() as uc_client:

    res = uc_client.sources.get_connection_check_sources(security=operations.GetConnectionCheckSourcesSecurity(
        http_bearer="<YOUR_BEARER_TOKEN_HERE>",
    ), request={
        "source_id": "4df23b66-dae2-44ea-8dd3-329184d5644a",
    })

    assert res.dag_node_connection_check is not None

    # Handle response
    print(res.dag_node_connection_check)

```

### Parameters

| Parameter                                                                                                    | Type                                                                                                         | Required                                                                                                     | Description                                                                                                  |
| ------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------ |
| `request`                                                                                                    | [operations.GetConnectionCheckSourcesRequest](../../models/operations/getconnectionchecksourcesrequest.md)   | :heavy_check_mark:                                                                                           | The request object to use for the request.                                                                   |
| `security`                                                                                                   | [operations.GetConnectionCheckSourcesSecurity](../../models/operations/getconnectionchecksourcessecurity.md) | :heavy_check_mark:                                                                                           | The security requirements to use for the request.                                                            |
| `retries`                                                                                                    | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                                             | :heavy_minus_sign:                                                                                           | Configuration to override the default retry behavior of the client.                                          |

### Response

**[operations.GetConnectionCheckSourcesResponse](../../models/operations/getconnectionchecksourcesresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

## get_source

Retrieve detailed information for a specific source connector by its ID.

### Example Usage

<!-- UsageSnippet language="python" operationID="get_source" method="get" path="/api/v1/sources/{source_id}" -->
```python
from unstructured_client import UnstructuredClient
from unstructured_client.models import operations


with UnstructuredClient() as uc_client:

    res = uc_client.sources.get_source(security=operations.GetSourceSecurity(
        http_bearer="<YOUR_BEARER_TOKEN_HERE>",
    ), request={
        "source_id": "df7d5ab1-bb15-4f1a-8dc0-c92a9a28a585",
    })

    assert res.source_connector_information is not None

    # Handle response
    print(res.source_connector_information)

```

### Parameters

| Parameter                                                                    | Type                                                                         | Required                                                                     | Description                                                                  |
| ---------------------------------------------------------------------------- | ---------------------------------------------------------------------------- | ---------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| `request`                                                                    | [operations.GetSourceRequest](../../models/operations/getsourcerequest.md)   | :heavy_check_mark:                                                           | The request object to use for the request.                                   |
| `security`                                                                   | [operations.GetSourceSecurity](../../models/operations/getsourcesecurity.md) | :heavy_check_mark:                                                           | The security requirements to use for the request.                            |
| `retries`                                                                    | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)             | :heavy_minus_sign:                                                           | Configuration to override the default retry behavior of the client.          |

### Response

**[operations.GetSourceResponse](../../models/operations/getsourceresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

## list_sources

Retrieve a list of available source connectors.

### Example Usage

<!-- UsageSnippet language="python" operationID="list_sources" method="get" path="/api/v1/sources/" -->
```python
from unstructured_client import UnstructuredClient
from unstructured_client.models import operations


with UnstructuredClient() as uc_client:

    res = uc_client.sources.list_sources(security=operations.ListSourcesSecurity(
        http_bearer="<YOUR_BEARER_TOKEN_HERE>",
    ), request={})

    assert res.response_list_sources is not None

    # Handle response
    print(res.response_list_sources)

```

### Parameters

| Parameter                                                                        | Type                                                                             | Required                                                                         | Description                                                                      |
| -------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| `request`                                                                        | [operations.ListSourcesRequest](../../models/operations/listsourcesrequest.md)   | :heavy_check_mark:                                                               | The request object to use for the request.                                       |
| `security`                                                                       | [operations.ListSourcesSecurity](../../models/operations/listsourcessecurity.md) | :heavy_check_mark:                                                               | The security requirements to use for the request.                                |
| `retries`                                                                        | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                 | :heavy_minus_sign:                                                               | Configuration to override the default retry behavior of the client.              |

### Response

**[operations.ListSourcesResponse](../../models/operations/listsourcesresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

## update_source

Update the configuration of an existing source connector.

### Example Usage

<!-- UsageSnippet language="python" operationID="update_source" method="put" path="/api/v1/sources/{source_id}" -->
```python
from unstructured_client import UnstructuredClient
from unstructured_client.models import operations


with UnstructuredClient() as uc_client:

    res = uc_client.sources.update_source(security=operations.UpdateSourceSecurity(
        http_bearer="<YOUR_BEARER_TOKEN_HERE>",
    ), request={
        "update_source_connector": {
            "config": {
                "batch_size": 615322,
                "bucket": "<value>",
                "collection_id": "<id>",
                "connection_string": "<value>",
                "password": "sMt9qfyDYveMwvw",
                "username": "Rene.Glover-Lakin",
            },
        },
        "source_id": "ddfe2014-2c10-4972-9711-fc2801d19038",
    })

    assert res.source_connector_information is not None

    # Handle response
    print(res.source_connector_information)

```

### Parameters

| Parameter                                                                          | Type                                                                               | Required                                                                           | Description                                                                        |
| ---------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `request`                                                                          | [operations.UpdateSourceRequest](../../models/operations/updatesourcerequest.md)   | :heavy_check_mark:                                                                 | The request object to use for the request.                                         |
| `security`                                                                         | [operations.UpdateSourceSecurity](../../models/operations/updatesourcesecurity.md) | :heavy_check_mark:                                                                 | The security requirements to use for the request.                                  |
| `retries`                                                                          | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                   | :heavy_minus_sign:                                                                 | Configuration to override the default retry behavior of the client.                |

### Response

**[operations.UpdateSourceResponse](../../models/operations/updatesourceresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |