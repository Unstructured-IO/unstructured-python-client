# General
(*general*)

## Overview

### Available Operations

* [partition](#partition) - Summary

## partition

Description

### Example Usage

```python
from unstructured_client import UnstructuredClient
from unstructured_client.models import shared

with UnstructuredClient() as unstructured_client:

    res = unstructured_client.general.partition(request={
        "partition_parameters": {
            "files": {
                "content": open("example.file", "rb"),
                "file_name": "example.file",
            },
            "chunking_strategy": shared.ChunkingStrategy.BY_TITLE,
            "split_pdf_page_range": [
                1,
                10,
            ],
            "strategy": shared.Strategy.HI_RES,
        },
    })

    assert res.elements is not None

    # Handle response
    print(res.elements)

```

### Parameters

| Parameter                                                                  | Type                                                                       | Required                                                                   | Description                                                                |
| -------------------------------------------------------------------------- | -------------------------------------------------------------------------- | -------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| `request`                                                                  | [operations.PartitionRequest](../../models/operations/partitionrequest.md) | :heavy_check_mark:                                                         | The request object to use for the request.                                 |
| `retries`                                                                  | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)           | :heavy_minus_sign:                                                         | Configuration to override the default retry behavior of the client.        |

### Response

**[operations.PartitionResponse](../../models/operations/partitionresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.ServerError         | 5XX                        | application/json           |
| errors.SDKError            | 4XX                        | \*/\*                      |