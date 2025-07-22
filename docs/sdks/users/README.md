# Users
(*users*)

## Overview

### Available Operations

* [retrieve](#retrieve) - Retrieve PEM Key
* [store_secret](#store_secret) - Store an encrypted secret

## retrieve

Given a UNSTRUCTURED_API_KEY in the post-payload, retrieve the associated PEM key

### Example Usage

```python
from unstructured_client import UnstructuredClient


with UnstructuredClient() as uc_client:

    res = uc_client.users.retrieve(request={})

    assert res.pem_auth_response is not None

    # Handle response
    print(res.pem_auth_response)

```

### Parameters

| Parameter                                                                | Type                                                                     | Required                                                                 | Description                                                              |
| ------------------------------------------------------------------------ | ------------------------------------------------------------------------ | ------------------------------------------------------------------------ | ------------------------------------------------------------------------ |
| `request`                                                                | [operations.RetrieveRequest](../../models/operations/retrieverequest.md) | :heavy_check_mark:                                                       | The request object to use for the request.                               |
| `retries`                                                                | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)         | :heavy_minus_sign:                                                       | Configuration to override the default retry behavior of the client.      |
| `server_url`                                                             | *Optional[str]*                                                          | :heavy_minus_sign:                                                       | An optional server URL to use.                                           |

### Response

**[operations.RetrieveResponse](../../models/operations/retrieveresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

## store_secret

After encrypting a secret locally, store it and get back a reference id.

### Example Usage

```python
from unstructured_client import UnstructuredClient


with UnstructuredClient() as uc_client:

    res = uc_client.users.store_secret(request={
        "encrypted_secret": {
            "encrypted_value": "<value>",
        },
    })

    assert res.secret_reference is not None

    # Handle response
    print(res.secret_reference)

```

### Parameters

| Parameter                                                                      | Type                                                                           | Required                                                                       | Description                                                                    |
| ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------ |
| `request`                                                                      | [operations.StoreSecretRequest](../../models/operations/storesecretrequest.md) | :heavy_check_mark:                                                             | The request object to use for the request.                                     |
| `retries`                                                                      | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)               | :heavy_minus_sign:                                                             | Configuration to override the default retry behavior of the client.            |
| `server_url`                                                                   | *Optional[str]*                                                                | :heavy_minus_sign:                                                             | An optional server URL to use.                                                 |

### Response

**[operations.StoreSecretResponse](../../models/operations/storesecretresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |