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
