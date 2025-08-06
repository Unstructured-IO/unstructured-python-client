## 0.42.2

### Enhancements

### Features
* Enable arbitrary inputs for `SourceConnectorType` and `DestinationConnectorType`. This lets the client support new connector types without having to upgrade.

### Fixes

## 0.42.1

### Enhancements

### Features

### Fixes
* potential issue referencing models before declaration (commit by @mfbx9da4)

## 0.42.0

### Enhancements

### Features

### Fixes
* Fix some environments failing to split pdfs with `Can't patch loop of type <class 'uvloop.Loop'>`, remove usage of `nest-asyncio`
* Remove some operations under `client.users` that are not fully ready yet

## 0.41.0

### Enhancements

### Features
* Provide a base `UnstructuredClientError` to capture every error raised by the SDK. Note that some exceptions such as `SDKError` now have more information in the `message` field. This will impact any users who rely on string matching in their error handling.

### Fixes

## 0.37.3

### Enhancements
* Improve PDF validation error handling by introducing FileValidationError base class for better error abstraction

### Features

### Fixes
* Replace RequestError with PDFValidationError for invalid PDF files to provide more accurate error context

## 0.37.0

### Enhancements

### Features

### Fixes
* Throws appropriate error message in case the given PDF file is invalid (corrupted or encrypted).

## 0.30.0

### Enhancements

### Features
* Add Unstructured Platform APIs to manage source and destination connectors, workflows, and workflow runs
__WARNING__: This is a breaking change for the use of non-default `server_url` settings in the client usage.
To set the custom URL for the client, use the the `server_url` parameter in a given operation:
```python
elements = client.general.partition(
    request=operations.PartitionRequest(
        partition_parameters=shared.PartitionParameters(
            files=shared.Files(
                content=doc_file,
                file_name="your_document.pdf",
            ),
            strategy=shared.Strategy.FAST,
        )
    ),
    server_url="your_server_url",
)
```

### Fixes

## 0.26.1

### Enhancements

### Features

### Fixes
* Use the configured server_url for our split page "dummy" request

## 0.26.0

### Enhancements
* Switch to a httpx based client instead of requests
* Switch to poetry for dependency management
* Add client side parameter checking via Pydantic or TypedDict interfaces

### Features
* Add `partition_async` for a non blocking alternative to `partition`

### Fixes
* Address some asyncio based errors in pdf splitting logic
