# Sources
(*sources*)

## Overview

### Available Operations

* [check_connection_api_v1_sources_source_id_connection_check_post](#check_connection_api_v1_sources_source_id_connection_check_post) - Check Connection
* [create_source](#create_source) - Create source connector
* [delete_source](#delete_source) - Delete source connector
* [get_connection_check_api_v1_sources_source_id_connection_check_get](#get_connection_check_api_v1_sources_source_id_connection_check_get) - Get Connection Check
* [get_source](#get_source) - Get source connector
* [list_sources](#list_sources) - List available source connectors
* [update_source](#update_source) - Update source connector

## check_connection_api_v1_sources_source_id_connection_check_post

Check Connection

Initiates a connection check for the specified source connector.

**Parameters:**
- **source_id**: The UUID of the source connector.
- **db_session**: Database session dependency.
- **user_data**: Information about the authenticated user.

**Returns:**
- The result of the connection check.

### Example Usage

```python
from unstructured_client import UnstructuredClient


with UnstructuredClient() as uc_client:

    res = uc_client.sources.check_connection_api_v1_sources_source_id_connection_check_post(request={
        "source_id": "8cb54f13-5652-423e-889c-1df1f8147126",
    })

    assert res.dag_node_connection_check is not None

    # Handle response
    print(res.dag_node_connection_check)

```

### Parameters

| Parameter                                                                                                                                                            | Type                                                                                                                                                                 | Required                                                                                                                                                             | Description                                                                                                                                                          |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `request`                                                                                                                                                            | [operations.CheckConnectionAPIV1SourcesSourceIDConnectionCheckPostRequest](../../models/operations/checkconnectionapiv1sourcessourceidconnectioncheckpostrequest.md) | :heavy_check_mark:                                                                                                                                                   | The request object to use for the request.                                                                                                                           |
| `retries`                                                                                                                                                            | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                                                                                                     | :heavy_minus_sign:                                                                                                                                                   | Configuration to override the default retry behavior of the client.                                                                                                  |
| `server_url`                                                                                                                                                         | *Optional[str]*                                                                                                                                                      | :heavy_minus_sign:                                                                                                                                                   | An optional server URL to use.                                                                                                                                       |

### Response

**[operations.CheckConnectionAPIV1SourcesSourceIDConnectionCheckPostResponse](../../models/operations/checkconnectionapiv1sourcessourceidconnectioncheckpostresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

## create_source

Create a new source connector using the provided configuration and name.

### Example Usage

```python
from unstructured_client import UnstructuredClient
from unstructured_client.models import shared


with UnstructuredClient() as uc_client:

    res = uc_client.sources.create_source(request={
        "create_source_connector": {
            "config": {
                "authority_url": "https://login.microsoftonline.com",
                "client_cred": "<value>",
                "client_id": "<id>",
                "recursive": False,
                "site": "<value>",
                "tenant": "<value>",
                "user_pname": "<value>",
            },
            "name": "<value>",
            "type": shared.SourceConnectorType.SNOWFLAKE,
        },
    })

    assert res.source_connector_information is not None

    # Handle response
    print(res.source_connector_information)

```

### Parameters

| Parameter                                                                        | Type                                                                             | Required                                                                         | Description                                                                      |
| -------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| `request`                                                                        | [operations.CreateSourceRequest](../../models/operations/createsourcerequest.md) | :heavy_check_mark:                                                               | The request object to use for the request.                                       |
| `retries`                                                                        | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                 | :heavy_minus_sign:                                                               | Configuration to override the default retry behavior of the client.              |
| `server_url`                                                                     | *Optional[str]*                                                                  | :heavy_minus_sign:                                                               | An optional server URL to use.                                                   |

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

```python
from unstructured_client import UnstructuredClient


with UnstructuredClient() as uc_client:

    res = uc_client.sources.delete_source(request={
        "source_id": "8a24d7ae-5524-45e9-83f9-b0adba5303d4",
    })

    assert res.any is not None

    # Handle response
    print(res.any)

```

### Parameters

| Parameter                                                                        | Type                                                                             | Required                                                                         | Description                                                                      |
| -------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| `request`                                                                        | [operations.DeleteSourceRequest](../../models/operations/deletesourcerequest.md) | :heavy_check_mark:                                                               | The request object to use for the request.                                       |
| `retries`                                                                        | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                 | :heavy_minus_sign:                                                               | Configuration to override the default retry behavior of the client.              |
| `server_url`                                                                     | *Optional[str]*                                                                  | :heavy_minus_sign:                                                               | An optional server URL to use.                                                   |

### Response

**[operations.DeleteSourceResponse](../../models/operations/deletesourceresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

## get_connection_check_api_v1_sources_source_id_connection_check_get

Get Connection Checks

Retrieves the most recent connection check for the specified source connector.

**Parameters:**
- **source_id**: The UUID of the source connector.
- **db_session**: Database session dependency.
- **user_data**: Information about the authenticated user.

**Returns:**
- Connection check results.

### Example Usage

```python
from unstructured_client import UnstructuredClient


with UnstructuredClient() as uc_client:

    res = uc_client.sources.get_connection_check_api_v1_sources_source_id_connection_check_get(request={
        "source_id": "d9c3daec-ddf9-4cef-ae8d-3a989813cc7b",
    })

    assert res.dag_node_connection_check is not None

    # Handle response
    print(res.dag_node_connection_check)

```

### Parameters

| Parameter                                                                                                                                                                | Type                                                                                                                                                                     | Required                                                                                                                                                                 | Description                                                                                                                                                              |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `request`                                                                                                                                                                | [operations.GetConnectionCheckAPIV1SourcesSourceIDConnectionCheckGetRequest](../../models/operations/getconnectioncheckapiv1sourcessourceidconnectioncheckgetrequest.md) | :heavy_check_mark:                                                                                                                                                       | The request object to use for the request.                                                                                                                               |
| `retries`                                                                                                                                                                | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                                                                                                         | :heavy_minus_sign:                                                                                                                                                       | Configuration to override the default retry behavior of the client.                                                                                                      |
| `server_url`                                                                                                                                                             | *Optional[str]*                                                                                                                                                          | :heavy_minus_sign:                                                                                                                                                       | An optional server URL to use.                                                                                                                                           |

### Response

**[operations.GetConnectionCheckAPIV1SourcesSourceIDConnectionCheckGetResponse](../../models/operations/getconnectioncheckapiv1sourcessourceidconnectioncheckgetresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

## get_source

Retrieve detailed information for a specific source connector by its ID.

### Example Usage

```python
from unstructured_client import UnstructuredClient


with UnstructuredClient() as uc_client:

    res = uc_client.sources.get_source(request={
        "source_id": "e02d8147-b614-4e4c-9c6d-0cd9c4492ea0",
    })

    assert res.source_connector_information is not None

    # Handle response
    print(res.source_connector_information)

```

### Parameters

| Parameter                                                                  | Type                                                                       | Required                                                                   | Description                                                                |
| -------------------------------------------------------------------------- | -------------------------------------------------------------------------- | -------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| `request`                                                                  | [operations.GetSourceRequest](../../models/operations/getsourcerequest.md) | :heavy_check_mark:                                                         | The request object to use for the request.                                 |
| `retries`                                                                  | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)           | :heavy_minus_sign:                                                         | Configuration to override the default retry behavior of the client.        |
| `server_url`                                                               | *Optional[str]*                                                            | :heavy_minus_sign:                                                         | An optional server URL to use.                                             |

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

```python
from unstructured_client import UnstructuredClient


with UnstructuredClient() as uc_client:

    res = uc_client.sources.list_sources(request={})

    assert res.response_list_sources is not None

    # Handle response
    print(res.response_list_sources)

```

### Parameters

| Parameter                                                                      | Type                                                                           | Required                                                                       | Description                                                                    |
| ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------ |
| `request`                                                                      | [operations.ListSourcesRequest](../../models/operations/listsourcesrequest.md) | :heavy_check_mark:                                                             | The request object to use for the request.                                     |
| `retries`                                                                      | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)               | :heavy_minus_sign:                                                             | Configuration to override the default retry behavior of the client.            |
| `server_url`                                                                   | *Optional[str]*                                                                | :heavy_minus_sign:                                                             | An optional server URL to use.                                                 |

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

```python
from unstructured_client import UnstructuredClient


with UnstructuredClient() as uc_client:

    res = uc_client.sources.update_source(request={
        "update_source_connector": {
            "config": {
                "batch_size": 69608,
                "database": "<value>",
                "host": "pleasing-hammock.org",
                "id_column": "id",
                "password": "Ns3L8K8WEZq1xvB",
                "port": 834056,
                "table_name": "<value>",
                "username": "Justyn.Daugherty",
            },
        },
        "source_id": "edec439e-8ef6-4c69-bc9e-3ba7a8418be7",
    })

    assert res.source_connector_information is not None

    # Handle response
    print(res.source_connector_information)

```

### Parameters

| Parameter                                                                        | Type                                                                             | Required                                                                         | Description                                                                      |
| -------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| `request`                                                                        | [operations.UpdateSourceRequest](../../models/operations/updatesourcerequest.md) | :heavy_check_mark:                                                               | The request object to use for the request.                                       |
| `retries`                                                                        | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                 | :heavy_minus_sign:                                                               | Configuration to override the default retry behavior of the client.              |
| `server_url`                                                                     | *Optional[str]*                                                                  | :heavy_minus_sign:                                                               | An optional server URL to use.                                                   |

### Response

**[operations.UpdateSourceResponse](../../models/operations/updatesourceresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |