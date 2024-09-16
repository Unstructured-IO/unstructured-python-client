<!-- Start SDK Example Usage [usage] -->
```python
# Synchronous Example
from unstructured_client import UnstructuredClient
from unstructured_client.models import shared

s = UnstructuredClient()

res = s.general.partition(request={
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

if res.elements is not None:
    # handle response
    pass
```

</br>

The same SDK client can also be used to make asychronous requests by importing asyncio.
```python
# Asynchronous Example
import asyncio
from unstructured_client import UnstructuredClient
from unstructured_client.models import shared

async def main():
    s = UnstructuredClient()
    res = await s.general.partition_async(request={
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
    if res.elements is not None:
        # handle response
        pass

asyncio.run(main())
```
<!-- End SDK Example Usage [usage] -->