<!-- Start SDK Example Usage [usage] -->
```python
# Synchronous Example
from unstructured_client import UnstructuredClient
from unstructured_client.models import shared

s = UnstructuredClient(
    api_key_auth="YOUR_API_KEY",
)


res = s.general.partition(request={
    "partition_parameters": {
        "files": {
            "content": open("<file_path>", "rb"),
            "file_name": "your_file_here",
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

The same SDK client can also be used to make asynchronous requests by importing asyncio.
```python
# Asynchronous Example
import asyncio
from unstructured_client import UnstructuredClient
from unstructured_client.models import shared

async def main():
    s = UnstructuredClient(
        api_key_auth="YOUR_API_KEY",
    )
    res = await s.general.partition_async(request={
        "partition_parameters": {
            "files": {
                "content": open("<file_path>", "rb"),
                "file_name": "your_file_here",
            },
            "chunking_strategy": shared.ChunkingStrategy.BASIC,
            "split_pdf_page_range": [
                1,
                10,
            ],
            "strategy": shared.Strategy.AUTO,
        },
    })
    if res.elements is not None:
        # handle response
        pass

asyncio.run(main())
```
<!-- End SDK Example Usage [usage] -->