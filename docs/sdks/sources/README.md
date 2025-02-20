# Sources
(*sources*)

## Overview

### Available Operations

* [create_source](#create_source) - Create source connector
* [delete_source](#delete_source) - Delete source connector
* [get_source](#get_source) - Get source connector
* [list_sources](#list_sources) - List available source connectors
* [update_source](#update_source) - Update source connector

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
                "batch_size": 100,
                "bucket": "bucket-name",
                "collection": "collection_name",
                "collection_id": "type",
                "connection_string": "couchbases://cb.abcdefg.cloud.couchbase.com",
                "password": "password",
                "scope": "scope_name",
                "username": "username",
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
                "batch_size": 100,
                "bucket": "bucket-name",
                "collection": "collection_name",
                "collection_id": "type",
                "connection_string": "couchbases://cb.abcdefg.cloud.couchbase.com",
                "password": "password",
                "scope": "scope_name",
                "username": "username",
            },
        },
        "source_id": "196d27d0-3173-4749-b69d-2ee5d8e2396e",
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