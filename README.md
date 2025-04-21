<h3 align="center">
  <img
    src="https://raw.githubusercontent.com/Unstructured-IO/unstructured/main/img/unstructured_logo.png"
    height="200"
  >
</h3>

<div align="center">
    <a href="https://speakeasyapi.dev/"><img src="https://custom-icon-badges.demolab.com/badge/-Built%20By%20Speakeasy-212015?style=for-the-badge&logoColor=FBE331&logo=speakeasy&labelColor=545454" /></a>
</div>

<div align="center">

</div>

<h2 align="center">
  <p>Python SDK for the Unstructured API</p>
</h2>

This is a HTTP client for the [Unstructured Platform API](https://docs.unstructured.io/platform-api/overview). You can sign up [here](https://unstructured.io/developers) and process 1000 free pages per day for 14 days.

Please refer to the our documentation for a full guide on integrating the [Workflow Endpoint](https://docs.unstructured.io/platform-api/api/overview) and [Partition Endpoint](https://docs.unstructured.io/platform-api/partition-api/sdk-python) into your Python code.

<!-- Start Summary [summary] -->
## Summary


<!-- End Summary [summary] -->

<!-- Start Table of Contents [toc] -->
## Table of Contents
<!-- $toc-max-depth=2 -->
  * [SDK Installation](#sdk-installation)
  * [Retries](#retries)
  * [Error Handling](#error-handling)
  * [Custom HTTP Client](#custom-http-client)
  * [IDE Support](#ide-support)
  * [SDK Example Usage](#sdk-example-usage)
  * [Configuration](#configuration)
  * [File uploads](#file-uploads)
  * [Resource Management](#resource-management)
  * [Debugging](#debugging)

<!-- End Table of Contents [toc] -->

<!-- Start SDK Installation [installation] -->
## SDK Installation

> [!NOTE]
> **Python version upgrade policy**
>
> Once a Python version reaches its [official end of life date](https://devguide.python.org/versions/), a 3-month grace period is provided for users to upgrade. Following this grace period, the minimum python version supported in the SDK will be updated.

The SDK can be installed with either *pip* or *poetry* package managers.

### PIP

*PIP* is the default package installer for Python, enabling easy installation and management of packages from PyPI via the command line.

```bash
pip install unstructured-client
```

### Poetry

*Poetry* is a modern tool that simplifies dependency management and package publishing by using a single `pyproject.toml` file to handle project metadata and dependencies.

```bash
poetry add unstructured-client
```

### Shell and script usage with `uv`

You can use this SDK in a Python shell with [uv](https://docs.astral.sh/uv/) and the `uvx` command that comes with it like so:

```shell
uvx --from unstructured-client python
```

It's also possible to write a standalone Python script without needing to set up a whole project like so:

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "unstructured-client",
# ]
# ///

from unstructured_client import UnstructuredClient

sdk = UnstructuredClient(
  # SDK arguments
)

# Rest of script here...
```

Once that is saved to a file, you can run it with `uv run script.py` where
`script.py` can be replaced with the actual file name.
<!-- End SDK Installation [installation] -->


<!-- Start Retries [retries] -->
## Retries

Some of the endpoints in this SDK support retries. If you use the SDK without any configuration, it will fall back to the default retry strategy provided by the API. However, the default retry strategy can be overridden on a per-operation basis, or across the entire SDK.

To change the default retry strategy for a single API call, simply provide a `RetryConfig` object to the call:
```python
from unstructured_client import UnstructuredClient
from unstructured_client.utils import BackoffStrategy, RetryConfig


with UnstructuredClient() as uc_client:

    res = uc_client.destinations.create_connection_check_destinations(request={
        "destination_id": "d9795fb7-2135-4e48-a51d-009dd6ca38a1",
    },
        RetryConfig("backoff", BackoffStrategy(1, 50, 1.1, 100), False))

    assert res.dag_node_connection_check is not None

    # Handle response
    print(res.dag_node_connection_check)

```

If you'd like to override the default retry strategy for all operations that support retries, you can use the `retry_config` optional parameter when initializing the SDK:
```python
from unstructured_client import UnstructuredClient
from unstructured_client.utils import BackoffStrategy, RetryConfig


with UnstructuredClient(
    retry_config=RetryConfig("backoff", BackoffStrategy(1, 50, 1.1, 100), False),
) as uc_client:

    res = uc_client.destinations.create_connection_check_destinations(request={
        "destination_id": "d9795fb7-2135-4e48-a51d-009dd6ca38a1",
    })

    assert res.dag_node_connection_check is not None

    # Handle response
    print(res.dag_node_connection_check)

```
<!-- End Retries [retries] -->


<!-- Start Error Handling [errors] -->
## Error Handling

Handling errors in this SDK should largely match your expectations. All operations return a response object or raise an exception.

By default, an API error will raise a errors.SDKError exception, which has the following properties:

| Property        | Type             | Description           |
|-----------------|------------------|-----------------------|
| `.status_code`  | *int*            | The HTTP status code  |
| `.message`      | *str*            | The error message     |
| `.raw_response` | *httpx.Response* | The raw HTTP response |
| `.body`         | *str*            | The response content  |

When custom error responses are specified for an operation, the SDK may also raise their associated exceptions. You can refer to respective *Errors* tables in SDK docs for more details on possible exception types for each operation. For example, the `create_connection_check_destinations_async` method may raise the following exceptions:

| Error Type                 | Status Code | Content Type     |
| -------------------------- | ----------- | ---------------- |
| errors.HTTPValidationError | 422         | application/json |
| errors.SDKError            | 4XX, 5XX    | \*/\*            |

### Example

```python
from unstructured_client import UnstructuredClient
from unstructured_client.models import errors


with UnstructuredClient() as uc_client:
    res = None
    try:

        res = uc_client.destinations.create_connection_check_destinations(request={
            "destination_id": "d9795fb7-2135-4e48-a51d-009dd6ca38a1",
        })

        assert res.dag_node_connection_check is not None

        # Handle response
        print(res.dag_node_connection_check)

    except errors.HTTPValidationError as e:
        # handle e.data: errors.HTTPValidationErrorData
        raise(e)
    except errors.SDKError as e:
        # handle exception
        raise(e)
```
<!-- End Error Handling [errors] -->

<!-- Start Custom HTTP Client [http-client] -->
## Custom HTTP Client

The Python SDK makes API calls using the [httpx](https://www.python-httpx.org/) HTTP library.  In order to provide a convenient way to configure timeouts, cookies, proxies, custom headers, and other low-level configuration, you can initialize the SDK client with your own HTTP client instance.
Depending on whether you are using the sync or async version of the SDK, you can pass an instance of `HttpClient` or `AsyncHttpClient` respectively, which are Protocol's ensuring that the client has the necessary methods to make API calls.
This allows you to wrap the client with your own custom logic, such as adding custom headers, logging, or error handling, or you can just pass an instance of `httpx.Client` or `httpx.AsyncClient` directly.

For example, you could specify a header for every request that this sdk makes as follows:
```python
from unstructured_client import UnstructuredClient
import httpx

http_client = httpx.Client(headers={"x-custom-header": "someValue"})
s = UnstructuredClient(client=http_client)
```

or you could wrap the client with your own custom logic:
```python
from unstructured_client import UnstructuredClient
from unstructured_client.httpclient import AsyncHttpClient
import httpx

class CustomClient(AsyncHttpClient):
    client: AsyncHttpClient

    def __init__(self, client: AsyncHttpClient):
        self.client = client

    async def send(
        self,
        request: httpx.Request,
        *,
        stream: bool = False,
        auth: Union[
            httpx._types.AuthTypes, httpx._client.UseClientDefault, None
        ] = httpx.USE_CLIENT_DEFAULT,
        follow_redirects: Union[
            bool, httpx._client.UseClientDefault
        ] = httpx.USE_CLIENT_DEFAULT,
    ) -> httpx.Response:
        request.headers["Client-Level-Header"] = "added by client"

        return await self.client.send(
            request, stream=stream, auth=auth, follow_redirects=follow_redirects
        )

    def build_request(
        self,
        method: str,
        url: httpx._types.URLTypes,
        *,
        content: Optional[httpx._types.RequestContent] = None,
        data: Optional[httpx._types.RequestData] = None,
        files: Optional[httpx._types.RequestFiles] = None,
        json: Optional[Any] = None,
        params: Optional[httpx._types.QueryParamTypes] = None,
        headers: Optional[httpx._types.HeaderTypes] = None,
        cookies: Optional[httpx._types.CookieTypes] = None,
        timeout: Union[
            httpx._types.TimeoutTypes, httpx._client.UseClientDefault
        ] = httpx.USE_CLIENT_DEFAULT,
        extensions: Optional[httpx._types.RequestExtensions] = None,
    ) -> httpx.Request:
        return self.client.build_request(
            method,
            url,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            timeout=timeout,
            extensions=extensions,
        )

s = UnstructuredClient(async_client=CustomClient(httpx.AsyncClient()))
```
<!-- End Custom HTTP Client [http-client] -->

<!-- Start IDE Support [idesupport] -->
## IDE Support

### PyCharm

Generally, the SDK will work well with most IDEs out of the box. However, when using PyCharm, you can enjoy much better integration with Pydantic by installing an additional plugin.

- [PyCharm Pydantic Plugin](https://docs.pydantic.dev/latest/integrations/pycharm/)
<!-- End IDE Support [idesupport] -->


<!-- Start SDK Example Usage [usage] -->
## SDK Example Usage

### Example

```python
# Synchronous Example
from unstructured_client import UnstructuredClient


with UnstructuredClient() as uc_client:

    res = uc_client.destinations.create_connection_check_destinations(request={
        "destination_id": "d9795fb7-2135-4e48-a51d-009dd6ca38a1",
    })

    assert res.dag_node_connection_check is not None

    # Handle response
    print(res.dag_node_connection_check)
```

</br>

The same SDK client can also be used to make asychronous requests by importing asyncio.
```python
# Asynchronous Example
import asyncio
from unstructured_client import UnstructuredClient

async def main():

    async with UnstructuredClient() as uc_client:

        res = await uc_client.destinations.create_connection_check_destinations_async(request={
            "destination_id": "d9795fb7-2135-4e48-a51d-009dd6ca38a1",
        })

        assert res.dag_node_connection_check is not None

        # Handle response
        print(res.dag_node_connection_check)

asyncio.run(main())
```
<!-- End SDK Example Usage [usage] -->

Refer to the [API parameters page](https://docs.unstructured.io/api-reference/api-services/api-parameters) for all available parameters.


## Configuration

### Splitting PDF by pages

See [page splitting](https://docs.unstructured.io/api-reference/api-services/sdk#page-splitting) for more details.

In order to speed up processing of large PDF files, the client splits up PDFs into smaller files, sends these to the API concurrently, and recombines the results. `split_pdf_page` can be set to `False` to disable this.

The amount of workers utilized for splitting PDFs is dictated by the `split_pdf_concurrency_level` parameter, with a default of 5 and a maximum of 15 to keep resource usage and costs in check. The splitting process leverages `asyncio` to manage concurrency effectively.
The size of each batch of pages (ranging from 2 to 20) is internally determined based on the concurrency level and the total number of pages in the document. Because the splitting process uses `asyncio` the client can encouter event loop issues if it is nested in another async runner, like running in a `gevent` spawned task. Instead, this is safe to run in multiprocessing workers (e.g., using `multiprocessing.Pool` with `fork` context).

Example:
```python
req = operations.PartitionRequest(
    partition_parameters=shared.PartitionParameters(
        files=files,
        strategy="fast",
        languages=["eng"],
        split_pdf_concurrency_level=8
    )
)
```

### Sending specific page ranges

When `split_pdf_page=True` (the default), you can optionally specify a page range to send only a portion of your PDF to be extracted. The parameter takes a list of two integers to specify the range, inclusive. A ValueError is thrown if the page range is invalid.

Example:
```python
req = operations.PartitionRequest(
    partition_parameters=shared.PartitionParameters(
        files=files,
        strategy="fast",
        languages=["eng"],
        split_pdf_page_range=[10,15],
    )
)
```

### Splitting PDF by pages - strict mode

When `split_pdf_allow_failed=False` (the default), any errors encountered during sending parallel request will break the process and raise an exception. 
When `split_pdf_allow_failed=True`, the process will continue even if some requests fail, and the results will be combined at the end (the output from the errored pages will not be included).

Example:
```python
req = operations.PartitionRequest(
    partition_parameters=shared.PartitionParameters(
        files=files,
        strategy="fast",
        languages=["eng"],
        split_pdf_allow_failed=True,
    )
)
```

<!-- Start File uploads [file-upload] -->
## File uploads

Certain SDK methods accept file objects as part of a request body or multi-part request. It is possible and typically recommended to upload files as a stream rather than reading the entire contents into memory. This avoids excessive memory consumption and potentially crashing with out-of-memory errors when working with very large files. The following example demonstrates how to attach a file stream to a request.

> [!TIP]
>
> For endpoints that handle file uploads bytes arrays can also be used. However, using streams is recommended for large files.
>

```python
from unstructured_client import UnstructuredClient
from unstructured_client.models import shared


with UnstructuredClient() as uc_client:

    res = uc_client.general.partition(request={
        "partition_parameters": {
            "files": {
                "content": open("example.file", "rb"),
                "file_name": "example.file",
            },
            "split_pdf_page_range": [
                1,
                10,
            ],
            "vlm_model": shared.VLMModel.GPT_4O,
            "vlm_model_provider": shared.VLMModelProvider.OPENAI,
        },
    })

    assert res.elements is not None

    # Handle response
    print(res.elements)

```
<!-- End File uploads [file-upload] -->

<!-- Start Resource Management [resource-management] -->
## Resource Management

The `UnstructuredClient` class implements the context manager protocol and registers a finalizer function to close the underlying sync and async HTTPX clients it uses under the hood. This will close HTTP connections, release memory and free up other resources held by the SDK. In short-lived Python programs and notebooks that make a few SDK method calls, resource management may not be a concern. However, in longer-lived programs, it is beneficial to create a single SDK instance via a [context manager][context-manager] and reuse it across the application.

[context-manager]: https://docs.python.org/3/reference/datamodel.html#context-managers

```python
from unstructured_client import UnstructuredClient
def main():

    with UnstructuredClient() as uc_client:
        # Rest of application here...


# Or when using async:
async def amain():

    async with UnstructuredClient() as uc_client:
        # Rest of application here...
```
<!-- End Resource Management [resource-management] -->

<!-- Start Debugging [debug] -->
## Debugging

You can setup your SDK to emit debug logs for SDK requests and responses.

You can pass your own logger class directly into your SDK.
```python
from unstructured_client import UnstructuredClient
import logging

logging.basicConfig(level=logging.DEBUG)
s = UnstructuredClient(debug_logger=logging.getLogger("unstructured_client"))
```
<!-- End Debugging [debug] -->

<!-- No SDK Available Operations -->
<!-- No Pagination -->
<!-- No Server Selection -->
<!-- No Authentication -->

<!-- Placeholder for Future Speakeasy SDK Sections -->

### Maturity

This SDK is in beta, and there may be breaking changes between versions without a major version update. Therefore, we recommend pinning usage
to a specific package version. This way, you can install the same version each time without breaking changes unless you are intentionally
looking for the latest version.

### Installation Instructions for Local Development

The following instructions are intended to help you get up and running with `unstructured-python-client` locally if you are planning to contribute to the project.

* Using `pyenv` to manage virtualenv's is recommended but not necessary
   * Mac install instructions. See [here](https://github.com/Unstructured-IO/community#mac--homebrew) for more detailed instructions.
      * `brew install pyenv-virtualenv`
      * `pyenv install 3.10`
   * Linux instructions are available [here](https://github.com/Unstructured-IO/community#linux).

* Create a virtualenv to work in and activate it, e.g. for one named `unstructured-python-client`:

  `pyenv  virtualenv 3.10 unstructured-python-client`
  `pyenv activate unstructured-python-client`

* Run `make install` and `make test`

### Contributions

While we value open-source contributions to this SDK, this library is generated programmatically by Speakeasy. In order to start working with this repo, you need to:
1. Install Speakeasy client locally https://github.com/speakeasy-api/speakeasy#installation
2. Run `speakeasy auth login`
3. Run `make client-generate`. This allows to iterate development with python client.

There are two important files used by `make client-generate`:
1. `openapi.json` which is actually not stored here, [but fetched from unstructured-api](https://api.unstructured.io/general/openapi.json), represents the API that is supported on backend.
2. `overlay_client.yaml` is a handcrafted diff that when applied over above, produces `openapi_client.json` which is used to generate SDK.

Once PR with changes is merged, Github CI will autogenerate the Speakeasy client in a new PR, using
the `openapi.json` and `overlay_client.yaml` You will have to manually bring back the human created lines in it.

Feel free to open a PR or a Github issue as a proof of concept and we'll do our best to include it in a future release!

### SDK Created by [Speakeasy](https://www.speakeasyapi.dev/docs/sdk-design/python/methodology-python)
