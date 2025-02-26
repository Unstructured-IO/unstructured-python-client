# Jobs
(*jobs*)

## Overview

### Available Operations

* [cancel_job](#cancel_job) - Cancel Job
* [get_job](#get_job) - Get Job
* [list_jobs](#list_jobs) - List Jobs

## cancel_job

Cancel the specified job.

### Example Usage

```python
from unstructured_client import UnstructuredClient

with UnstructuredClient(
    server_url="https://api.example.com",
) as uc_client:

    res = uc_client.jobs.cancel_job(request={
        "job_id": "ec29bf67-0f30-4793-b5ee-8fc0da196032",
    })

    assert res.any is not None

    # Handle response
    print(res.any)

```

### Parameters

| Parameter                                                                  | Type                                                                       | Required                                                                   | Description                                                                |
| -------------------------------------------------------------------------- | -------------------------------------------------------------------------- | -------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| `request`                                                                  | [operations.CancelJobRequest](../../models/operations/canceljobrequest.md) | :heavy_check_mark:                                                         | The request object to use for the request.                                 |
| `retries`                                                                  | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)           | :heavy_minus_sign:                                                         | Configuration to override the default retry behavior of the client.        |
| `server_url`                                                               | *Optional[str]*                                                            | :heavy_minus_sign:                                                         | An optional server URL to use.                                             |

### Response

**[operations.CancelJobResponse](../../models/operations/canceljobresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

## get_job

Retrieve detailed information for a specific job by its ID.

### Example Usage

```python
from unstructured_client import UnstructuredClient

with UnstructuredClient(
    server_url="https://api.example.com",
) as uc_client:

    res = uc_client.jobs.get_job(request={
        "job_id": "6bb4cb72-a072-4398-9de3-194e59352a3c",
    })

    assert res.job_information is not None

    # Handle response
    print(res.job_information)

```

### Parameters

| Parameter                                                            | Type                                                                 | Required                                                             | Description                                                          |
| -------------------------------------------------------------------- | -------------------------------------------------------------------- | -------------------------------------------------------------------- | -------------------------------------------------------------------- |
| `request`                                                            | [operations.GetJobRequest](../../models/operations/getjobrequest.md) | :heavy_check_mark:                                                   | The request object to use for the request.                           |
| `retries`                                                            | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)     | :heavy_minus_sign:                                                   | Configuration to override the default retry behavior of the client.  |
| `server_url`                                                         | *Optional[str]*                                                      | :heavy_minus_sign:                                                   | An optional server URL to use.                                       |

### Response

**[operations.GetJobResponse](../../models/operations/getjobresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

## list_jobs

Retrieve a list of jobs with optional filtering by workflow ID or job status.

### Example Usage

```python
from unstructured_client import UnstructuredClient

with UnstructuredClient(
    server_url="https://api.example.com",
) as uc_client:

    res = uc_client.jobs.list_jobs(request={})

    assert res.response_list_jobs is not None

    # Handle response
    print(res.response_list_jobs)

```

### Parameters

| Parameter                                                                | Type                                                                     | Required                                                                 | Description                                                              |
| ------------------------------------------------------------------------ | ------------------------------------------------------------------------ | ------------------------------------------------------------------------ | ------------------------------------------------------------------------ |
| `request`                                                                | [operations.ListJobsRequest](../../models/operations/listjobsrequest.md) | :heavy_check_mark:                                                       | The request object to use for the request.                               |
| `retries`                                                                | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)         | :heavy_minus_sign:                                                       | Configuration to override the default retry behavior of the client.      |
| `server_url`                                                             | *Optional[str]*                                                          | :heavy_minus_sign:                                                       | An optional server URL to use.                                           |

### Response

**[operations.ListJobsResponse](../../models/operations/listjobsresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |