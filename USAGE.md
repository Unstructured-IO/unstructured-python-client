<!-- Start SDK Example Usage [usage] -->
```python
# Synchronous Example
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

</br>

The same SDK client can also be used to make asychronous requests by importing asyncio.
```python
# Asynchronous Example
import asyncio
from unstructured_client import UnstructuredClient
from unstructured_client.models import shared

async def main():
    async with UnstructuredClient() as unstructured_client:

        res = await unstructured_client.general.partition_async(request={
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

asyncio.run(main())
```
<!-- End SDK Example Usage [usage] -->