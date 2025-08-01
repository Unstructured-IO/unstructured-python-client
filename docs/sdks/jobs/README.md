# Jobs
(*jobs*)

## Overview

### Available Operations

* [cancel_job](#cancel_job) - Cancel Job
* [download_job_output](#download_job_output) - Download Job output
* [get_job](#get_job) - Get Job
* [get_job_details](#get_job_details) - Get Job processing details
* [get_job_failed_files](#get_job_failed_files) - Get Job Failed Files
* [list_jobs](#list_jobs) - List Jobs

## cancel_job

Cancel the specified job.

### Example Usage

<!-- UsageSnippet language="python" operationID="cancel_job" method="post" path="/api/v1/jobs/{job_id}/cancel" -->
```python
from unstructured_client import UnstructuredClient


with UnstructuredClient() as uc_client:

    res = uc_client.jobs.cancel_job(request={
        "job_id": "2fafd129-04f3-4201-a0e7-fe33e937b367",
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

### Response

**[operations.CancelJobResponse](../../models/operations/canceljobresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

## download_job_output

Download the output of a job from a workflow where the input file was provided at runtime.

### Example Usage

<!-- UsageSnippet language="python" operationID="download_job_output" method="get" path="/api/v1/jobs/{job_id}/download" -->
```python
from unstructured_client import UnstructuredClient


with UnstructuredClient() as uc_client:

    res = uc_client.jobs.download_job_output(request={
        "file_id": "<id>",
        "job_id": "06d1b7b8-8642-4793-b37e-e45d97d53bc3",
        "node_id": "7c8f2aa4-da13-4a04-a98d-0204ea55681e",
    })

    assert res.any is not None

    # Handle response
    print(res.any)

```

### Parameters

| Parameter                                                                                  | Type                                                                                       | Required                                                                                   | Description                                                                                |
| ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ |
| `request`                                                                                  | [operations.DownloadJobOutputRequest](../../models/operations/downloadjoboutputrequest.md) | :heavy_check_mark:                                                                         | The request object to use for the request.                                                 |
| `retries`                                                                                  | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                           | :heavy_minus_sign:                                                                         | Configuration to override the default retry behavior of the client.                        |

### Response

**[operations.DownloadJobOutputResponse](../../models/operations/downloadjoboutputresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

## get_job

Retrieve detailed information for a specific job by its ID.

### Example Usage

<!-- UsageSnippet language="python" operationID="get_job" method="get" path="/api/v1/jobs/{job_id}" -->
```python
from unstructured_client import UnstructuredClient


with UnstructuredClient() as uc_client:

    res = uc_client.jobs.get_job(request={
        "job_id": "d95a05b3-3446-4f3d-806c-904b6a7ba40a",
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

### Response

**[operations.GetJobResponse](../../models/operations/getjobresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

## get_job_details

Retrieve processing details for a specific job by its ID.

### Example Usage

<!-- UsageSnippet language="python" operationID="get_job_details" method="get" path="/api/v1/jobs/{job_id}/details" -->
```python
from unstructured_client import UnstructuredClient


with UnstructuredClient() as uc_client:

    res = uc_client.jobs.get_job_details(request={
        "job_id": "14cc95f9-4174-46b3-81f5-7089b87a4787",
    })

    assert res.job_details is not None

    # Handle response
    print(res.job_details)

```

### Parameters

| Parameter                                                                          | Type                                                                               | Required                                                                           | Description                                                                        |
| ---------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `request`                                                                          | [operations.GetJobDetailsRequest](../../models/operations/getjobdetailsrequest.md) | :heavy_check_mark:                                                                 | The request object to use for the request.                                         |
| `retries`                                                                          | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                   | :heavy_minus_sign:                                                                 | Configuration to override the default retry behavior of the client.                |

### Response

**[operations.GetJobDetailsResponse](../../models/operations/getjobdetailsresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

## get_job_failed_files

Retrieve failed files for a specific job by its ID.

### Example Usage

<!-- UsageSnippet language="python" operationID="get_job_failed_files" method="get" path="/api/v1/jobs/{job_id}/failed-files" -->
```python
from unstructured_client import UnstructuredClient


with UnstructuredClient() as uc_client:

    res = uc_client.jobs.get_job_failed_files(request={
        "job_id": "ad262041-3530-40a9-9f83-b004e947a203",
    })

    assert res.job_failed_files is not None

    # Handle response
    print(res.job_failed_files)

```

### Parameters

| Parameter                                                                                  | Type                                                                                       | Required                                                                                   | Description                                                                                |
| ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ |
| `request`                                                                                  | [operations.GetJobFailedFilesRequest](../../models/operations/getjobfailedfilesrequest.md) | :heavy_check_mark:                                                                         | The request object to use for the request.                                                 |
| `retries`                                                                                  | [Optional[utils.RetryConfig]](../../models/utils/retryconfig.md)                           | :heavy_minus_sign:                                                                         | Configuration to override the default retry behavior of the client.                        |

### Response

**[operations.GetJobFailedFilesResponse](../../models/operations/getjobfailedfilesresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |

## list_jobs

Retrieve a list of jobs with optional filtering by workflow ID or job status.

### Example Usage

<!-- UsageSnippet language="python" operationID="list_jobs" method="get" path="/api/v1/jobs/" -->
```python
from unstructured_client import UnstructuredClient


with UnstructuredClient() as uc_client:

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

### Response

**[operations.ListJobsResponse](../../models/operations/listjobsresponse.md)**

### Errors

| Error Type                 | Status Code                | Content Type               |
| -------------------------- | -------------------------- | -------------------------- |
| errors.HTTPValidationError | 422                        | application/json           |
| errors.SDKError            | 4XX, 5XX                   | \*/\*                      |